"""
Nex-Lyon Real Estate Analyzer - Configuration
Settings, Lyon market reference data, and demo fixtures.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ──────────────────────────────────────────────────────────────────
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# ─── Database ──────────────────────────────────────────────────────────────────
DB_NAME = "lyon_real_estate.db"

# ─── Lyon Market Reference Data (2025-2026 estimates) ─────────────────────────
# Source: avg observed prices and rental yields per arrondissement
LYON_MARKET = {
    "Lyon 1er": {"avg_price_m2": 4800, "rental_yield_pct": 3.8},
    "Lyon 2e":  {"avg_price_m2": 5300, "rental_yield_pct": 3.5},
    "Lyon 3e":  {"avg_price_m2": 4300, "rental_yield_pct": 4.5},
    "Lyon 4e":  {"avg_price_m2": 4800, "rental_yield_pct": 4.0},
    "Lyon 5e":  {"avg_price_m2": 4300, "rental_yield_pct": 4.2},
    "Lyon 6e":  {"avg_price_m2": 6000, "rental_yield_pct": 3.3},
    "Lyon 7e":  {"avg_price_m2": 4300, "rental_yield_pct": 4.8},
    "Lyon 8e":  {"avg_price_m2": 3700, "rental_yield_pct": 5.5},
    "Lyon 9e":  {"avg_price_m2": 3400, "rental_yield_pct": 5.8},
}

# ─── DPE Energy Ratings ───────────────────────────────────────────────────────
# value_factor  : multiplier on property value relative to DPE C baseline
# energy_cost_yr: estimated annual energy cost in EUR
# reno_cost_m2  : estimated cost per m2 to renovate to DPE B level
DPE = {
    "A": {"label": "Excellent",  "value_factor": 1.10, "energy_cost_yr": 250,  "reno_cost_m2": 0},
    "B": {"label": "Very Good",  "value_factor": 1.05, "energy_cost_yr": 500,  "reno_cost_m2": 0},
    "C": {"label": "Good",       "value_factor": 1.00, "energy_cost_yr": 750,  "reno_cost_m2": 100},
    "D": {"label": "Average",    "value_factor": 0.95, "energy_cost_yr": 1100, "reno_cost_m2": 250},
    "E": {"label": "Poor",       "value_factor": 0.88, "energy_cost_yr": 1600, "reno_cost_m2": 450},
    "F": {"label": "Very Poor",  "value_factor": 0.80, "energy_cost_yr": 2200, "reno_cost_m2": 650},
    "G": {"label": "Critical",   "value_factor": 0.70, "energy_cost_yr": 3000, "reno_cost_m2": 900},
}

# ─── Demo Data ─────────────────────────────────────────────────────────────────
# Curated realistic listings across all 9 arrondissements.
# Used when no SerpAPI key is configured (fully functional without any API keys).
DEMO_LISTINGS = [
    {
        "title": "T3 Lumineux - Pentes Croix-Rousse",
        "price": 225000, "arrondissement": "Lyon 4e", "size": 68, "dpe": "F", "rooms": 3,
        "description": "Bel appartement T3 traversant, parquet ancien, a renover. Vue degagee sur la ville.",
    },
    {
        "title": "T2 Renove Standing - Bellecour",
        "price": 295000, "arrondissement": "Lyon 2e", "size": 55, "dpe": "C", "rooms": 2,
        "description": "Appartement entierement renove, cuisine equipee, proche place Bellecour.",
    },
    {
        "title": "Studio Charme - Terreaux",
        "price": 165000, "arrondissement": "Lyon 1er", "size": 28, "dpe": "D", "rooms": 1,
        "description": "Studio plein de charme au coeur du 1er, ideal investissement locatif.",
    },
    {
        "title": "T4 Familial - Monplaisir",
        "price": 255000, "arrondissement": "Lyon 8e", "size": 88, "dpe": "E", "rooms": 4,
        "description": "Grand T4 familial, 3 chambres, balcon, cave. Quartier calme et commercant.",
    },
    {
        "title": "T3 Vue Parc Tete d'Or",
        "price": 435000, "arrondissement": "Lyon 6e", "size": 75, "dpe": "B", "rooms": 3,
        "description": "Superbe T3 avec vue sur le Parc de la Tete d'Or. Prestations haut de gamme.",
    },
    {
        "title": "T2 Investisseur - Gerland",
        "price": 178000, "arrondissement": "Lyon 7e", "size": 42, "dpe": "D", "rooms": 2,
        "description": "T2 ideal investissement, proche metro et universites. Rentabilite assuree.",
    },
    {
        "title": "T5 Bourgeois - Brotteaux",
        "price": 620000, "arrondissement": "Lyon 6e", "size": 120, "dpe": "C", "rooms": 5,
        "description": "Magnifique appartement bourgeois, moulures, cheminees, parquet point de Hongrie.",
    },
    {
        "title": "T3 Neuf - Confluence",
        "price": 345000, "arrondissement": "Lyon 2e", "size": 65, "dpe": "A", "rooms": 3,
        "description": "Appartement neuf dans residence recente, terrasse, parking inclus.",
    },
    {
        "title": "T2 Atypique - Vieux Lyon",
        "price": 210000, "arrondissement": "Lyon 5e", "size": 48, "dpe": "E", "rooms": 2,
        "description": "T2 de caractere dans immeuble Renaissance. Poutres apparentes, pierres dorees.",
    },
    {
        "title": "T4 Renove - Part-Dieu",
        "price": 310000, "arrondissement": "Lyon 3e", "size": 82, "dpe": "C", "rooms": 4,
        "description": "T4 entierement renove, double sejour, a 5 min de la gare Part-Dieu.",
    },
    {
        "title": "Studio Etudiant - Guillotiere",
        "price": 98000, "arrondissement": "Lyon 7e", "size": 20, "dpe": "F", "rooms": 1,
        "description": "Studio meuble, loue 450 EUR/mois. Proche universites Lyon 2 et Lyon 3.",
    },
    {
        "title": "T3 Dernier Etage - Sans Souci",
        "price": 275000, "arrondissement": "Lyon 3e", "size": 63, "dpe": "D", "rooms": 3,
        "description": "T3 dernier etage avec terrasse, lumineux, ascenseur, gardien.",
    },
    {
        "title": "T2 Cosy - Croix-Rousse Plateau",
        "price": 245000, "arrondissement": "Lyon 4e", "size": 45, "dpe": "C", "rooms": 2,
        "description": "Charmant T2 sur le plateau, ambiance village. Commerces et marche a pied.",
    },
    {
        "title": "T4 A Renover - Duchere",
        "price": 145000, "arrondissement": "Lyon 9e", "size": 78, "dpe": "G", "rooms": 4,
        "description": "T4 a renover entierement. Prix attractif, fort potentiel de plus-value.",
    },
    {
        "title": "T3 Moderne - Jean Mace",
        "price": 268000, "arrondissement": "Lyon 7e", "size": 60, "dpe": "B", "rooms": 3,
        "description": "T3 recent, lumineux, balcon, parking. Quartier dynamique en pleine evolution.",
    },
    {
        "title": "T2 Meuble - Ainay",
        "price": 275000, "arrondissement": "Lyon 2e", "size": 40, "dpe": "D", "rooms": 2,
        "description": "T2 meuble dans quartier prise. Parfait pied-a-terre ou investissement.",
    },
    {
        "title": "T5 Maison de Ville - Saint-Rambert",
        "price": 380000, "arrondissement": "Lyon 9e", "size": 130, "dpe": "E", "rooms": 5,
        "description": "Maison de ville avec jardin, 4 chambres, garage. Cadre verdoyant et calme.",
    },
    {
        "title": "T3 Balcon Filant - Montchat",
        "price": 285000, "arrondissement": "Lyon 3e", "size": 70, "dpe": "C", "rooms": 3,
        "description": "T3 avec grand balcon filant, sejour lumineux, parquet chene. Quartier recherche.",
    },
    {
        "title": "T2 Neuf BBC - Gerland",
        "price": 215000, "arrondissement": "Lyon 7e", "size": 44, "dpe": "A", "rooms": 2,
        "description": "T2 neuf basse consommation, terrasse, parking. Eco-quartier en developpement.",
    },
    {
        "title": "T3 Haussmannien - Massena",
        "price": 395000, "arrondissement": "Lyon 6e", "size": 72, "dpe": "D", "rooms": 3,
        "description": "Bel Haussmannien, hauteur sous plafond, parquet, cheminee marbre.",
    },
]
