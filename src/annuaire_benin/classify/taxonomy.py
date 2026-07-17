"""Taxonomie des secteurs d'activité.

25 secteurs conçus pour l'atlas économique : assez fins pour être
parlants (la téléphonie n'est pas noyée dans le commerce), assez
larges pour que chaque secteur pèse. Inspirée des nomenclatures
ISIC/NAF mais adaptée à la réalité du registre béninois, où le
commerce de détail domine et mérite d'être détaillé par famille de
produits.
"""

from __future__ import annotations

SECTORS: dict[str, str] = {
    "finance-mobile-money": "Transfert d'argent (mobile money)",
    "commerce-telephonie-electronique": "Commerce : téléphonie et électronique",
    "commerce-alimentaire": "Commerce : alimentation et boissons",
    "commerce-mode-beaute": "Commerce : mode, textile et beauté",
    "commerce-agricole": "Commerce : produits agricoles et forestiers",
    "commerce-construction-quincaillerie": "Commerce : quincaillerie et matériaux",
    "commerce-maison-loisirs": "Commerce : maison, bureau et loisirs",
    "commerce-auto-moto": "Commerce : automobile et moto",
    "commerce-divers": "Commerce : divers",
    "energie-eau": "Énergie et eau",
    "informatique-numerique": "Informatique et numérique",
    "btp-construction": "BTP et construction",
    "industrie-transformation": "Industrie et transformation",
    "agriculture-elevage-peche": "Agriculture, élevage et pêche",
    "transport-logistique": "Transport et logistique",
    "restauration-hotellerie-tourisme": "Restauration, hôtellerie et tourisme",
    "immobilier": "Immobilier",
    "services-professionnels": "Services professionnels (conseil, juridique, comptable)",
    "services-beaute": "Coiffure et esthétique",
    "services-location": "Location de matériel et d'espaces",
    "services-divers": "Services divers (entretien, pressing, réparation)",
    "medias-communication": "Médias, édition et audiovisuel",
    "education-formation": "Éducation et formation",
    "sante-medical": "Santé et médical",
    "assurance-finance": "Assurance",
}
