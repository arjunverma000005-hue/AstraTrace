"""AstraTrace Controlled Vocabulary & EuroSAT Taxonomy Parser.

SIH 2026 | Problem ID: SIH26227
Maps natural language concepts, operational queries, and geospatial terms to
canonical EuroSAT land-cover classes for deterministic baseline retrieval.
"""
import re
from typing import Dict, List, Set, Tuple

# The 10 canonical EuroSAT land-cover classes
EUROSAT_CLASSES: List[str] = [
    "AnnualCrop",
    "Forest",
    "HerbaceousVegetation",
    "Highway",
    "Industrial",
    "Pasture",
    "PermanentCrop",
    "Residential",
    "River",
    "SeaLake",
]

# Comprehensive controlled synset dictionary for remote-sensing concepts
SYNSET_MAP: Dict[str, Dict[str, float]] = {
    # Industrial structures & infrastructure
    "industrial": {"Industrial": 1.0},
    "industry": {"Industrial": 1.0},
    "factory": {"Industrial": 1.0},
    "factories": {"Industrial": 1.0},
    "warehouse": {"Industrial": 1.0},
    "warehouses": {"Industrial": 1.0},
    "depot": {"Industrial": 1.0},
    "depots": {"Industrial": 1.0},
    "storage": {"Industrial": 0.8, "Residential": 0.2},
    "manufacturing": {"Industrial": 1.0},
    "facility": {"Industrial": 0.7, "Residential": 0.3},
    "facilities": {"Industrial": 0.7, "Residential": 0.3},
    "tank": {"Industrial": 0.9},
    "tanks": {"Industrial": 0.9},
    "refinery": {"Industrial": 1.0},
    "hangar": {"Industrial": 0.8, "Highway": 0.2},

    # Residential & general urban structures
    "residential": {"Residential": 1.0},
    "urban": {"Residential": 0.65, "Industrial": 0.35},
    "housing": {"Residential": 1.0},
    "houses": {"Residential": 1.0},
    "house": {"Residential": 1.0},
    "home": {"Residential": 1.0},
    "homes": {"Residential": 1.0},
    "apartment": {"Residential": 1.0},
    "apartments": {"Residential": 1.0},
    "settlement": {"Residential": 0.8, "Industrial": 0.2},
    "settlements": {"Residential": 0.8, "Industrial": 0.2},
    "city": {"Residential": 0.6, "Industrial": 0.3, "Highway": 0.1},
    "town": {"Residential": 0.7, "Highway": 0.2, "Industrial": 0.1},
    "suburb": {"Residential": 0.9, "Highway": 0.1},
    "suburbs": {"Residential": 0.9, "Highway": 0.1},
    "building": {"Residential": 0.6, "Industrial": 0.4},
    "buildings": {"Residential": 0.6, "Industrial": 0.4},
    "structure": {"Residential": 0.5, "Industrial": 0.5},
    "structures": {"Residential": 0.5, "Industrial": 0.5},
    "construction": {"Industrial": 0.5, "Residential": 0.5},

    # Highway & transportation corridors
    "highway": {"Highway": 1.0},
    "highways": {"Highway": 1.0},
    "road": {"Highway": 1.0},
    "roads": {"Highway": 1.0},
    "corridor": {"Highway": 0.8, "River": 0.2},
    "corridors": {"Highway": 0.8, "River": 0.2},
    "motorway": {"Highway": 1.0},
    "expressway": {"Highway": 1.0},
    "freeway": {"Highway": 1.0},
    "runway": {"Highway": 0.85, "Industrial": 0.15},
    "runways": {"Highway": 0.85, "Industrial": 0.15},
    "airstrip": {"Highway": 0.85, "Industrial": 0.15},
    "asphalt": {"Highway": 0.7, "Industrial": 0.3},
    "transit": {"Highway": 1.0},
    "street": {"Highway": 0.7, "Residential": 0.3},
    "streets": {"Highway": 0.7, "Residential": 0.3},
    "tarmac": {"Highway": 0.8, "Industrial": 0.2},
    "route": {"Highway": 0.9},

    # Forest & dense woodland
    "forest": {"Forest": 1.0},
    "forests": {"Forest": 1.0},
    "wood": {"Forest": 0.8, "HerbaceousVegetation": 0.2},
    "woods": {"Forest": 0.9, "HerbaceousVegetation": 0.1},
    "woodland": {"Forest": 1.0},
    "tree": {"Forest": 0.9, "HerbaceousVegetation": 0.1},
    "trees": {"Forest": 0.9, "HerbaceousVegetation": 0.1},
    "jungle": {"Forest": 1.0},
    "canopy": {"Forest": 0.9, "HerbaceousVegetation": 0.1},
    "timberland": {"Forest": 1.0},

    # Herbaceous vegetation & grasslands
    "vegetation": {"HerbaceousVegetation": 0.5, "Forest": 0.5},
    "grass": {"HerbaceousVegetation": 0.7, "Pasture": 0.3},
    "grassland": {"HerbaceousVegetation": 0.7, "Pasture": 0.3},
    "greenery": {"HerbaceousVegetation": 0.6, "Forest": 0.4},
    "meadow": {"HerbaceousVegetation": 0.6, "Pasture": 0.4},
    "meadows": {"HerbaceousVegetation": 0.6, "Pasture": 0.4},
    "shrub": {"HerbaceousVegetation": 0.8, "Forest": 0.2},
    "shrubs": {"HerbaceousVegetation": 0.8, "Forest": 0.2},
    "scrub": {"HerbaceousVegetation": 0.9},
    "scrubland": {"HerbaceousVegetation": 0.9},
    "bush": {"HerbaceousVegetation": 0.8, "Forest": 0.2},
    "bushes": {"HerbaceousVegetation": 0.8, "Forest": 0.2},

    # Pasture & rangeland
    "pasture": {"Pasture": 1.0},
    "pastures": {"Pasture": 1.0},
    "grazing": {"Pasture": 1.0},
    "rangeland": {"Pasture": 0.8, "HerbaceousVegetation": 0.2},

    # Crops & agriculture
    "crop": {"AnnualCrop": 0.8, "PermanentCrop": 0.2},
    "crops": {"AnnualCrop": 0.8, "PermanentCrop": 0.2},
    "farmland": {"AnnualCrop": 0.8, "Pasture": 0.2},
    "farm": {"AnnualCrop": 0.7, "Pasture": 0.2, "Residential": 0.1},
    "farms": {"AnnualCrop": 0.7, "Pasture": 0.2, "Residential": 0.1},
    "field": {"AnnualCrop": 0.6, "Pasture": 0.3, "HerbaceousVegetation": 0.1},
    "fields": {"AnnualCrop": 0.6, "Pasture": 0.3, "HerbaceousVegetation": 0.1},
    "cultivated": {"AnnualCrop": 0.85, "PermanentCrop": 0.15},
    "agriculture": {"AnnualCrop": 0.7, "PermanentCrop": 0.2, "Pasture": 0.1},
    "agricultural": {"AnnualCrop": 0.7, "PermanentCrop": 0.2, "Pasture": 0.1},
    "harvest": {"AnnualCrop": 1.0},
    "paddy": {"AnnualCrop": 1.0},

    # Permanent crops / orchards
    "orchard": {"PermanentCrop": 1.0},
    "orchards": {"PermanentCrop": 1.0},
    "vineyard": {"PermanentCrop": 1.0},
    "vineyards": {"PermanentCrop": 1.0},
    "grove": {"PermanentCrop": 0.8, "Forest": 0.2},
    "groves": {"PermanentCrop": 0.8, "Forest": 0.2},
    "plantation": {"PermanentCrop": 0.7, "AnnualCrop": 0.3},
    "plantations": {"PermanentCrop": 0.7, "AnnualCrop": 0.3},

    # River & running waterways
    "river": {"River": 1.0},
    "rivers": {"River": 1.0},
    "stream": {"River": 1.0},
    "streams": {"River": 1.0},
    "canal": {"River": 0.9, "Highway": 0.1},
    "canals": {"River": 0.9, "Highway": 0.1},
    "waterway": {"River": 0.9, "SeaLake": 0.1},
    "waterways": {"River": 0.9, "SeaLake": 0.1},
    "creek": {"River": 1.0},
    "creeks": {"River": 1.0},
    "tributary": {"River": 1.0},

    # Sea, lakes & open water bodies
    "water": {"SeaLake": 0.6, "River": 0.4},
    "waterbody": {"SeaLake": 0.7, "River": 0.3},
    "waterbodies": {"SeaLake": 0.7, "River": 0.3},
    "lake": {"SeaLake": 1.0},
    "lakes": {"SeaLake": 1.0},
    "sea": {"SeaLake": 1.0},
    "seas": {"SeaLake": 1.0},
    "ocean": {"SeaLake": 1.0},
    "oceans": {"SeaLake": 1.0},
    "reservoir": {"SeaLake": 0.9, "River": 0.1},
    "reservoirs": {"SeaLake": 0.9, "River": 0.1},
    "pond": {"SeaLake": 1.0},
    "ponds": {"SeaLake": 1.0},
    "coast": {"SeaLake": 0.8, "Residential": 0.2},
    "coastal": {"SeaLake": 0.8, "Residential": 0.2},
}


class ControlledVocabulary:
    """Parser that maps natural language search terms to EuroSAT class weight distributions."""

    @staticmethod
    def parse_query(query: str) -> Tuple[Dict[str, float], bool]:
        """Parses a query string into a normalized EuroSAT class weight distribution.

        Returns:
            Tuple of (class_weights: Dict[str, float], is_oov: bool)
            - class_weights: Mapping from EuroSAT class name to confidence weight (sums to 1.0).
            - is_oov: True if no vocabulary keywords matched (fallback to uniform distribution).
        """
        if not query or not query.strip():
            # Uniform fallback for empty query
            uniform = {c: 1.0 / len(EUROSAT_CLASSES) for c in EUROSAT_CLASSES}
            return uniform, True

        # Tokenize and normalize: lowercase, retain alphanumeric characters
        tokens = re.findall(r"\b[a-z0-9_-]+\b", query.lower())

        accumulated_weights: Dict[str, float] = {c: 0.0 for c in EUROSAT_CLASSES}
        matched_any = False

        # 1. Check multi-token bigrams first (e.g., "water body", "industrial warehouse")
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            if bigram in SYNSET_MAP:
                matched_any = True
                for cls_name, weight in SYNSET_MAP[bigram].items():
                    accumulated_weights[cls_name] += weight * 1.5  # Boost bigram matches

        # 2. Check individual tokens
        for token in tokens:
            # Direct class name match
            for cls in EUROSAT_CLASSES:
                if token == cls.lower():
                    accumulated_weights[cls] += 2.0
                    matched_any = True
                    break

            # Synset dictionary match
            if token in SYNSET_MAP:
                matched_any = True
                for cls_name, weight in SYNSET_MAP[token].items():
                    accumulated_weights[cls_name] += weight

        if not matched_any:
            # Fallback: uniform distribution across all 10 classes
            uniform = {c: 1.0 / len(EUROSAT_CLASSES) for c in EUROSAT_CLASSES}
            return uniform, True

        # Normalize weights so they sum to 1.0
        total_sum = sum(accumulated_weights.values())
        if total_sum > 0:
            normalized = {c: round(w / total_sum, 4) for c, w in accumulated_weights.items()}
            # Clean up near-zero noise
            filtered = {c: w for c, w in normalized.items() if w > 0.0}
            return filtered, False
        else:
            uniform = {c: 1.0 / len(EUROSAT_CLASSES) for c in EUROSAT_CLASSES}
            return uniform, True
