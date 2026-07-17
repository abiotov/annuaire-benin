"""Étape 2c : arbitrage LLM de la zone grise du rapprochement flou.

La zone grise (56 896 paires au seuil calibré) contient les vraies
paires que le seuil de fusion a laissées passer (rappel mesuré : 81 %).
Un LLM (Gemini) arbitre chaque paire par lots, en français, avec les
mêmes règles que l'annotation manuelle du jeu de vérité. Le protocole
suit la discipline du projet :

1. ``--gold`` : juger d'abord les paires grises du jeu de vérité et
   mesurer l'accord avec l'annotation humaine ; le juge n'est déployé
   que s'il est précis.
2. Arbitrage borné et reprenable : les verdicts sont persistés dans la
   table ``arbitrations``, une paire déjà jugée n'est jamais rejugée,
   le débit respecte les quotas de l'API.
3. ``--apply`` : les verdicts « même entreprise » deviennent des arêtes
   de fusion supplémentaires, le clustering est rejoué et le nouveau
   compte d'entreprises est rapporté.

La clé API est lue dans GEMINI_API_KEY ou dans ``data/.env`` (jamais
commitée). Aucune donnée individuelle n'est envoyée hors des noms
d'entreprises et communes strictement nécessaires à l'arbitrage.

Usage :
    python -m annuaire_benin.dedupe.arbitrate --gold data/gold_pairs_annotated.csv
    python -m annuaire_benin.dedupe.arbitrate --limit 2000 --min-score 0.72
    python -m annuaire_benin.dedupe.arbitrate --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from annuaire_benin.dedupe import clustering, scoring

DEFAULT_MODEL = "gemini-2.5-flash"
BATCH_SIZE = 25
REQUEST_INTERVAL_S = 7.0  # ~8 requêtes/minute, sous les quotas du palier gratuit
MAX_RETRIES = 4

VERDICT_SAME = "meme"
VERDICT_DIFFERENT = "diff"
VERDICT_UNSURE = "incertain"
VALID_VERDICTS = {VERDICT_SAME, VERDICT_DIFFERENT, VERDICT_UNSURE}

ARBITRATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS arbitrations (
    entity_a INTEGER NOT NULL,
    entity_b INTEGER NOT NULL,
    verdict  TEXT NOT NULL,
    model    TEXT NOT NULL,
    judged_at TEXT NOT NULL,
    PRIMARY KEY (entity_a, entity_b)
);
"""

PROMPT_HEADER = """Tu arbitres la déduplication d'un annuaire d'entreprises béninoises.
Pour chaque paire de fiches, décide si elles désignent LA MÊME entreprise
ou des entreprises DIFFÉRENTES.

Règles (issues de l'annotation manuelle de référence) :
- variantes d'orthographe, fautes de frappe, mots réordonnés, suffixe générique
  ajouté (ETS, SERVICES, PLUS, ET FILS, BENIN...) sur le même nom distinctif :
  MÊME entreprise ;
- mention « (RADIÉ) » puis réinscription du même nom : MÊME ;
- deux entreprises d'un même propriétaire mais aux noms réellement différents :
  DIFFÉRENTES ;
- expression pieuse ou générique partagée (GLOIRE DE DIEU, CHEZ..., BUSINESS...)
  sans nom distinctif commun : DIFFÉRENTES ;
- même nom de famille mais prénoms ou initiales différents : DIFFÉRENTES
  (membres d'une famille) ;
- communes éloignées sans très forte identité de nom : plutôt DIFFÉRENTES ;
- même quartier et même nom distinctif : indice fort de MÊME entreprise ;
  secteurs d'activité incompatibles : indice de DIFFÉRENTES ;
- doute réel : INCERTAIN.

Réponds UNIQUEMENT par un tableau JSON, un objet par paire, sans autre texte :
[{"i": 1, "v": "meme"}, {"i": 2, "v": "diff"}, {"i": 3, "v": "incertain"}]

Paires à juger :
"""


def load_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        env_path = Path("data/.env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit("GEMINI_API_KEY introuvable (environnement ou data/.env)")
    return key


def load_entities(connection: sqlite3.Connection) -> dict[int, dict]:
    from annuaire_benin.classify.taxonomy import SECTORS

    entities = {}
    for entity_id, name, communes, quartiers, sector in connection.execute(
        "SELECT id, name, communes, quartiers, sector FROM entities"
    ):
        entities[entity_id] = {
            "name": name,
            "communes": " / ".join(json.loads(communes)),
            "quartiers": " / ".join(json.loads(quartiers)[:3]),
            "sector": SECTORS.get(sector, "?"),
        }
    return entities


def _side(label: str, entity: dict) -> str:
    place = entity["communes"] or "commune inconnue"
    if entity["quartiers"]:
        place += ", quartier " + entity["quartiers"]
    return f'{label}: "{entity["name"]}" ({place} ; {entity["sector"]})'


def describe_pair(index: int, a: dict, b: dict, channels: str, name_sim: float) -> str:
    shared = []
    if "phone" in channels:
        shared.append("téléphone identique")
    if "email" in channels:
        shared.append("email identique")
    contact = ", ".join(shared) if shared else "aucun contact identique connu"
    return (
        f"{index}. {_side('A', a)} | {_side('B', b)}"
        f" | similarité de nom {name_sim:.2f} | {contact}"
    )


def build_prompt(batch: list[dict], entities: dict[int, dict]) -> str:
    lines = [
        describe_pair(i + 1, entities[p["a"]], entities[p["b"]], p["channels"], p["name_sim"])
        for i, p in enumerate(batch)
    ]
    return PROMPT_HEADER + "\n".join(lines)


def parse_verdicts(text: str, expected: int) -> list[str]:
    """Extrait les verdicts du JSON renvoyé ; INCERTAIN pour tout écart."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    verdicts = [VERDICT_UNSURE] * expected
    if not match:
        return verdicts
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return verdicts
    for item in items:
        try:
            index = int(item["i"]) - 1
            verdict = str(item["v"]).strip().lower()
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= index < expected and verdict in VALID_VERDICTS:
            verdicts[index] = verdict
    return verdicts


def call_gemini(prompt: str, key: str, model: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={key}"
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        # thinkingBudget 0 : le raisonnement long est inutile pour ce
        # classement et ses jetons comptent dans maxOutputTokens (constaté :
        # il tronquait le JSON des lots de 25 paires).
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 8192,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")
    delay = 10.0
    for attempt in range(MAX_RETRIES):
        request = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.load(response)
            parts = body["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except urllib.error.HTTPError as error:
            if error.code == 400 and b"thinkingConfig" in payload:
                # Les générations de modèles ne partagent pas la même
                # configuration de thinking : on retente sans elle.
                config = json.loads(payload)
                config["generationConfig"].pop("thinkingConfig", None)
                payload = json.dumps(config).encode("utf-8")
                continue
            if error.code in (429, 500, 503) and attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except (KeyError, IndexError):
            return ""
    return ""


REFUTE_HEADER = """Un premier examen a conclu que chacune de ces paires de fiches
d'un annuaire béninois désigne LA MÊME entreprise. Ton rôle est adversarial :
cherche activement une raison d'en douter (noms distinctifs réellement
différents, membres d'une même famille, homonymes, enseignes génériques ou
pieuses partagées, communes ou quartiers incompatibles, secteurs sans rapport).

Réponds "refute" si tu trouves une raison sérieuse de douter, "confirme"
seulement si l'identité résiste à ta critique, "incertain" sinon.
Réponds UNIQUEMENT par un tableau JSON, sans autre texte :
[{"i": 1, "v": "confirme"}, {"i": 2, "v": "refute"}]

Paires à contre-examiner :
"""


def _batched_call(pairs: list[dict], entities: dict[int, dict], key: str, model: str,
                  header: str, valid: set[str], fallback: str,
                  on_batch=None, offset_total: int = 0) -> list[str]:
    results: list[str] = []
    for start in range(0, len(pairs), BATCH_SIZE):
        batch = pairs[start:start + BATCH_SIZE]
        lines = [
            describe_pair(i + 1, entities[p["a"]], entities[p["b"]],
                          p["channels"], p["name_sim"])
            for i, p in enumerate(batch)
        ]
        text = call_gemini(header + "\n".join(lines), key, model)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        batch_results = [fallback] * len(batch)
        if match:
            try:
                for item in json.loads(match.group(0)):
                    index = int(item["i"]) - 1
                    verdict = str(item["v"]).strip().lower()
                    if 0 <= index < len(batch) and verdict in valid:
                        batch_results[index] = verdict
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass
        results.extend(batch_results)
        if on_batch:
            on_batch(offset_total + len(results))
        if start + BATCH_SIZE < len(pairs):
            time.sleep(REQUEST_INTERVAL_S)
    return results


def judge_pairs(pairs: list[dict], entities: dict[int, dict], key: str,
                model: str, on_batch=None) -> list[str]:
    """Juge chaque paire, puis contre-examine les « même » (passe adversariale).

    Le juge seul sur-fusionne (précision mesurée 44 % avec un rappel de
    100 % sur le jeu de vérité) : la seconde passe, chargée de réfuter,
    ne laisse passer que les identités qui résistent à la critique.
    """
    progress = (lambda done: on_batch(done, len(pairs))) if on_batch else None
    verdicts = _batched_call(pairs, entities, key, model, PROMPT_HEADER,
                             VALID_VERDICTS, VERDICT_UNSURE, on_batch=progress)

    same_indices = [i for i, v in enumerate(verdicts) if v == VERDICT_SAME]
    if same_indices:
        refutations = _batched_call(
            [pairs[i] for i in same_indices], entities, key, model,
            REFUTE_HEADER, {"confirme", "refute", "incertain"}, "incertain",
        )
        for index, outcome in zip(same_indices, refutations, strict=True):
            if outcome != "confirme":
                verdicts[index] = VERDICT_UNSURE
    return verdicts


def run_gold(connection: sqlite3.Connection, gold_path: Path, key: str, model: str) -> None:
    """Juge les paires grises du jeu de vérité et mesure l'accord humain."""
    with gold_path.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["zone"] == scoring.ZONE_GRAY]
    known = {}
    for a, b, channels, name_sim in connection.execute(
        "SELECT entity_a, entity_b, channels, name_sim FROM candidate_pairs"
    ):
        known[(a, b)] = (channels, name_sim)
    pairs = []
    for row in rows:
        a, b = int(row["entity_a"]), int(row["entity_b"])
        channels, name_sim = known.get((a, b), ("", 0.0))
        pairs.append({"a": a, "b": b, "channels": channels, "name_sim": name_sim,
                      "label": row["same_business"]})
    entities = load_entities(connection)
    print(f"Jugement de {len(pairs)} paires grises du jeu de vérité ({model})...")
    verdicts = judge_pairs(pairs, entities, key, model,
                           on_batch=lambda done, total: print(f"  {done}/{total}"))

    all_verdicts = (VERDICT_SAME, VERDICT_DIFFERENT, VERDICT_UNSURE)
    confusion = {}
    for pair, verdict in zip(pairs, verdicts, strict=True):
        confusion[(pair["label"], verdict)] = confusion.get((pair["label"], verdict), 0) + 1
    print("\nAccord juge LLM × annotation humaine (lignes = humain) :")
    print(f"  {'humain':<12}" + "".join(f"{v:>12}" for v in all_verdicts))
    for label in ("oui", "non", "incertain"):
        counts = [confusion.get((label, v), 0) for v in all_verdicts]
        print(f"  {label:<12}" + "".join(f"{c:>12}" for c in counts))

    tp = confusion.get(("oui", VERDICT_SAME), 0)
    fp = confusion.get(("non", VERDICT_SAME), 0)
    fn = sum(confusion.get(("oui", v), 0) for v in (VERDICT_DIFFERENT, VERDICT_UNSURE))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if precision is not None:
        print(f"\n  verdict « même » : précision {precision:.1%}"
              f" ({tp}/{tp + fp}), rappel {recall:.1%} sur les vraies paires grises")


def run_arbitrate(connection: sqlite3.Connection, key: str, model: str,
                  limit: int, min_score: float) -> None:
    """Arbitre les paires grises les plus prometteuses, de façon reprenable."""
    connection.executescript(ARBITRATIONS_SCHEMA)
    done = {
        (a, b) for a, b in connection.execute(
            "SELECT entity_a, entity_b FROM arbitrations")
    }
    pairs = [
        {"a": a, "b": b, "channels": channels, "name_sim": name_sim}
        for a, b, channels, name_sim, score in connection.execute(
            "SELECT entity_a, entity_b, channels, name_sim, score FROM candidate_pairs"
            " WHERE zone = ? AND score >= ? ORDER BY score DESC",
            (scoring.ZONE_GRAY, min_score),
        )
        if (a, b) not in done
    ][:limit]
    if not pairs:
        print("Rien à arbitrer (tout est déjà jugé pour ces critères).")
        return
    entities = load_entities(connection)
    print(f"Arbitrage de {len(pairs)} paires grises (score ≥ {min_score}, {model})...")

    # Persistance par tranche : un run interrompu ne perd que la tranche en
    # cours, le suivant reprend exactement où il s'est arrêté.
    judged_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    chunk_size = 100
    counts = dict.fromkeys(VALID_VERDICTS, 0)
    for start in range(0, len(pairs), chunk_size):
        chunk = pairs[start:start + chunk_size]
        verdicts = judge_pairs(chunk, entities, key, model)
        connection.executemany(
            "INSERT OR REPLACE INTO arbitrations VALUES (?, ?, ?, ?, ?)",
            [(p["a"], p["b"], v, model, judged_at)
             for p, v in zip(chunk, verdicts, strict=True)],
        )
        connection.commit()
        for verdict in verdicts:
            counts[verdict] += 1
        print(f"  {min(start + chunk_size, len(pairs))}/{len(pairs)} persistées")

    print(f"\nVerdicts : même {counts[VERDICT_SAME]},"
          f" différentes {counts[VERDICT_DIFFERENT]}, incertain {counts[VERDICT_UNSURE]}")


def run_apply(connection: sqlite3.Connection) -> None:
    """Rejoue le clustering avec les fusions arbitrées en plus du baseline."""
    edges = [
        (a, b, score) for a, b, score in connection.execute(
            "SELECT entity_a, entity_b, score FROM candidate_pairs WHERE zone = ?",
            (scoring.ZONE_MERGE,),
        )
    ]
    arbitrated = [
        (a, b, score) for a, b, score in connection.execute(
            "SELECT c.entity_a, c.entity_b, c.score FROM arbitrations ar"
            " JOIN candidate_pairs c ON c.entity_a = ar.entity_a AND c.entity_b = ar.entity_b"
            " WHERE ar.verdict = ?",
            (VERDICT_SAME,),
        )
    ]
    all_ids = [row[0] for row in connection.execute("SELECT id FROM entities")]
    assignment, stats = clustering.cluster(edges + arbitrated, all_ids)
    connection.executemany(
        "UPDATE entities SET cluster_id = ? WHERE id = ?",
        [(cluster_id, entity_id) for entity_id, cluster_id in assignment.items()],
    )
    connection.commit()
    final = len(set(assignment.values()))
    print(f"Fusions : {len(edges)} du baseline + {len(arbitrated)} arbitrées"
          f" (garde-fou : {stats.edges_skipped_by_guard} refusées)")
    print(f"{len(all_ids)} entités -> {final} entreprises finales")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/annuaire.db"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--gold", type=Path, help="évaluer le juge sur le jeu de vérité")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--min-score", type=float, default=0.72)
    parser.add_argument("--apply", action="store_true",
                        help="rejouer le clustering avec les fusions arbitrées")
    args = parser.parse_args(argv)

    connection = sqlite3.connect(args.db)
    if args.gold:
        run_gold(connection, args.gold, load_api_key(), args.model)
    elif args.apply:
        run_apply(connection)
    else:
        run_arbitrate(connection, load_api_key(), args.model, args.limit, args.min_score)
    connection.close()
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
