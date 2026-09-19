"""AstraTrace Natural Language Geospatial Query Parser.

SIH 2026 | Problem ID: SIH26227
Parses unstructured natural language intelligence queries into structured semantic slots:
TARGET, CHANGE, CONTEXT, TIME, LOCATION, SENSOR, QUALITY.
"""
import re
from typing import Any, Dict, List, Optional, Tuple


class ParsedQuerySlot:
    """Represents the decomposed slots of an analyst's natural language query."""

    def __init__(
        self,
        target: str = "general surface",
        change: str = "detected difference",
        context: str = "unrestricted terrain",
        time_range: str = "all available observations",
        location: str = "current archive extent",
        sensor: str = "optical / SAR fused",
        quality: str = "cloud < 20%",
        raw_query: str = "",
    ):
        self.target = target
        self.change = change
        self.context = context
        self.time_range = time_range
        self.location = location
        self.sensor = sensor
        self.quality = quality
        self.raw_query = raw_query

    def to_dict(self) -> Dict[str, str]:
        return {
            "target": self.target,
            "change": self.change,
            "context": self.context,
            "time": self.time_range,
            "location": self.location,
            "sensor": self.sensor,
            "quality": self.quality,
            "raw_query": self.raw_query,
        }


class SemanticQueryParser:
    """Rule-based and semantic slot extractor for Earth observation intelligence queries."""

    # Target keywords
    TARGET_PATTERNS = [
        (r"\b(structures?|buildings?|barracks?|compounds?|facilities|installations?|hangars?)\b", "structures"),
        (r"\b(vehicles?|convoys?|trucks?|tanks?|aircraft|helipads?)\b", "vehicle concentrations"),
        (r"\b(roads?|highways?|runways?|tracks?|paved surface)\b", "road / paved surface"),
        (r"\b(waterbod(y|ies)|lakes?|reservoirs?|rivers?|canals?|flood)\b", "waterbody"),
        (r"\b(vegetation|forest|tree cover|greenery|crops?)\b", "vegetation"),
        (r"\b(industrial|factories|warehouses?|depots?)\b", "industrial facilities"),
        (r"\b(earthworks?|trenches?|excavation|fortifications?)\b", "earthworks / fortifications"),
    ]

    # Change keywords
    CHANGE_PATTERNS = [
        (r"\b(newly built|new construction|constructed|built|development|erected)\b", "new construction"),
        (r"\b(expansion|expanded|growth|widening|enlargement)\b", "expansion"),
        (r"\b(clearance|cleared|deforestation|removal|excavated)\b", "land clearance"),
        (r"\b(concentrations?|accumulations?|clusterings?|groupings?)\b", "concentration / assembly"),
        (r"\b(contraction|reduction|shrinkage|drainage|drying)\b", "contraction"),
        (r"\b(disappearance|demolished|destroyed|removed)\b", "demolition / disappearance"),
        (r"\b(change|difference|modification|shift)\b", "land-use modification"),
    ]

    # Context keywords
    CONTEXT_PATTERNS = [
        (r"\b(near|along|adjacent to|beside)\s+(roads?|highways?|tracks?)\b", "near roads"),
        (r"\b(near|along|adjacent to|beside)\s+(rivers?|waterbod\w+|lakes?)\b", "near waterbody"),
        (r"\b(on|across|in)\s+(open ground|clearing|desert|plains?)\b", "on open ground"),
        (r"\b(near|along)\s+(the\s+)?(border|frontier|perimeter|line of control|loc)\b", "near border / perimeter"),
        (r"\b(within|inside)\s+(urban|military|industrial)\s+(areas?|zones?)\b", "in specialized zone"),
    ]

    # Sensor keywords
    SENSOR_PATTERNS = [
        (r"\b(sentinel[- ]?2|s2|optical|multispectral)\b", "Sentinel-2 (Optical)"),
        (r"\b(sentinel[- ]?1|s1|sar|radar)\b", "Sentinel-1 (SAR)"),
        (r"\b(landsat[- ]?[89]?)\b", "Landsat-8/9"),
    ]

    # Location keywords
    LOCATION_PATTERNS = [
        (r"\b(rajasthan|thar|pokhran|jaisalmer|bikaner|barmer)\b", "Rajasthan / Thar Sector"),
        (r"\b(ladakh|leh|kashmir|siachen)\b", "Northern Sector (High Altitude)"),
        (r"\b(punjab|wagah|ambala)\b", "Western Plains Sector"),
        (r"\b(arunachal|tawang|eastern border)\b", "Eastern Mountain Sector"),
    ]

    # Time keywords
    TIME_PATTERNS = [
        (r"\b(between\s+([a-zA-Z]+\s+\d{4})\s+and\s+([a-zA-Z]+\s+\d{4}))\b", lambda m: f"{m.group(2)} – {m.group(3)}"),
        (r"\b(from\s+(\d{4})\s+to\s+(\d{4}))\b", lambda m: f"{m.group(2)} – {m.group(3)}"),
        (r"\b(in\s+(\d{4}))\b", lambda m: f"Year {m.group(2)}"),
        (r"\b(recent|recently|past\s+months?|past\s+years?)\b", lambda m: "Recent (Past 12 Months)"),
    ]

    @classmethod
    def parse(cls, query: str) -> ParsedQuerySlot:
        """Parses a query string into a ParsedQuerySlot instance."""
        q_lower = query.lower().strip()

        # Extract Target
        target = "general surface"
        for pattern, label in cls.TARGET_PATTERNS:
            if re.search(pattern, q_lower):
                target = label
                break

        # Extract Change
        change = "detected difference"
        for pattern, label in cls.CHANGE_PATTERNS:
            if re.search(pattern, q_lower):
                change = label
                break

        # Extract Context
        context = "unrestricted terrain"
        for pattern, label in cls.CONTEXT_PATTERNS:
            m = re.search(pattern, q_lower)
            if m:
                context = label
                break

        # Extract Sensor
        sensor = "optical / SAR fused"
        for pattern, label in cls.SENSOR_PATTERNS:
            if re.search(pattern, q_lower):
                sensor = label
                break

        # Extract Location
        location = "current archive extent"
        for pattern, label in cls.LOCATION_PATTERNS:
            if re.search(pattern, q_lower):
                location = label
                break

        # Extract Time
        time_range = "all available observations"
        for pattern, formatter in cls.TIME_PATTERNS:
            m = re.search(pattern, q_lower)
            if m:
                time_range = formatter(m)
                break

        # Quality default
        quality = "usable observations only (cloud < 20%)"
        if "cloud" in q_lower:
            m_cloud = re.search(r"cloud\s*<\s*(\d+)%?", q_lower)
            if m_cloud:
                quality = f"cloud < {m_cloud.group(1)}%"

        return ParsedQuerySlot(
            target=target,
            change=change,
            context=context,
            time_range=time_range,
            location=location,
            sensor=sensor,
            quality=quality,
            raw_query=query,
        )
