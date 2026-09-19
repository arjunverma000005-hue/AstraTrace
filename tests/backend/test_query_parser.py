"""Unit tests for AstraTrace Natural Language Geospatial Query Parser.

SIH 2026 | Problem ID: SIH26227
"""
from apps.backend.app.services.retrieval.query_parser import SemanticQueryParser


def test_parse_structure_near_roads():
    query = "newly built structures near roads between January 2023 and January 2025"
    parsed = SemanticQueryParser.parse(query)
    d = parsed.to_dict()

    assert d["target"] == "structures"
    assert d["change"] == "new construction"
    assert d["context"] == "near roads"
    assert "2023" in d["time"] and "2025" in d["time"]


def test_parse_vehicle_concentration():
    query = "large vehicle concentrations on open ground"
    parsed = SemanticQueryParser.parse(query)
    d = parsed.to_dict()

    assert d["target"] == "vehicle concentrations"
    assert d["change"] == "concentration / assembly"
    assert d["context"] == "on open ground"


def test_parse_water_expansion():
    query = "waterbody expansion in Rajasthan near rivers"
    parsed = SemanticQueryParser.parse(query)
    d = parsed.to_dict()

    assert d["target"] == "waterbody"
    assert d["change"] == "expansion"
    assert d["location"] == "Rajasthan / Thar Sector"


def test_parse_vegetation_clearance():
    query = "vegetation clearance in 2024"
    parsed = SemanticQueryParser.parse(query)
    d = parsed.to_dict()

    assert d["target"] == "vegetation"
    assert d["change"] == "land clearance"
    assert "2024" in d["time"]
