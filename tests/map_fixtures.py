"""Coherent two-result and full-page map XML test data."""

import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import TypedDict


class MapBounds(TypedDict):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


BOUNDS: MapBounds = {"min_lat": 34.36, "max_lat": 35.15, "min_lon": 135.85, "max_lon": 137.25}
XML = (Path(__file__).parent / "fixtures/map_yakitori.xml").read_text()
PAGINATION_OUTPUT_CASES = [
    (1, 271, "", 20, True, True, 20),
    (2, 271, "", 20, True, True, 20),
    (14, 271, ' nextpg="stale" prevpg="stale"', 20, False, False, 11),
    (1, 2, ' nextpg="stale" prevpg="stale"', 20, False, False, 2),
    (1, 2, ' nextpg="stale" prevpg="stale"', 1, False, True, 1),
]


def map_page_xml(page: int, total: int, labels: str = "") -> str:
    """Fill each upstream page before any parser skipping or local truncation."""
    templates = ET.fromstring(XML).findall("marker")
    root = ET.Element("markers")
    root.append(ET.fromstring(f'<srchinfo cnt="{total}"{labels}/>'))
    count = min(20, max(0, total - (page - 1) * 20))
    for index in range(count):
        marker = deepcopy(templates[min(index, 1)])
        if index >= 2 or page > 1:
            original_id = marker.attrib["id"]
            identity = f"{original_id[:2]}{900000 + (page - 1) * 20 + index:06d}"
            marker.set("id", identity)
            marker.set("rsturl", marker.attrib["rsturl"].replace(original_id, identity))
            marker.set("rstname", f"Fixture restaurant {page}-{index}")
        root.append(marker)
    return ET.tostring(root, encoding="unicode")
