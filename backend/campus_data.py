"""
SIUE Campus Graph Data

This module contains the actual campus layout based on the official SIUE campus map.
Buildings are nodes, walkways/paths are edges with distance weights.

Building numbering from the official map:
1 - Rendleman Hall
2 - Founders Hall
3 - Alumni Hall
4 - Peck Hall
5 - Lovejoy Library
6 - Dunham Hall
7 - Science Buildings East and West
8 - Morris University Center (MUC)
9 - Art and Design & Art and Design West
10 - Center for Spirituality and Sustainability
11 - Metcalf Student Experimental Theater
12 - Student Fitness Center
13 - First Community Arena at the Vadalabene Center
17 - Woodland Residence Hall
18 - Prairie Residence Hall
19 - Engineering Building
20 - B. Barnard Birger Hall
21 - Bluff Residence Hall
23 - 200 University Park
24 - 100 North Research Dr.
25 - 95 North Research Drive
26 - Chamber of Commerce
27 - School of Pharmacy Lab
31 - Technology and Management Center
32 - Stratton Quadrangle
33 - Evergreen Residence Hall
34 - 47 North Research Dr.
35 - 110 N Research Dr.
37 - Dental Clinic
39 - Swimming Pool
41 - Outdoor Recreational Sports Complex
44 - Student Success Center
45 - Physics Observatory
48 - The Gardens
49 - The "e" Sculpture

Parking Lots: P1-P12, A-G, BH, PH, WH, EH
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import math


@dataclass
class Building:
    """Represents a campus building/location."""
    id: str
    name: str
    short_name: str
    x: float  # Relative x coordinate (for visualization)
    y: float  # Relative y coordinate (for visualization)
    building_type: str  # academic, residential, athletic, parking, other


@dataclass
class Edge:
    """Represents a path between two buildings."""
    source: str
    target: str
    weight: float  # Distance in meters (estimated)
    path_type: str  # walkway, road, covered


# Campus Buildings with coordinates matching official SIUE map
# Coordinates are normalized (0-100 scale) based on the official campus core map
# X increases left to right, Y increases top to bottom to match map orientation
BUILDINGS: Dict[str, Building] = {
    # Academic Buildings (Red markers on map) - Positioned to match official map
    "1": Building("1", "Rendleman Hall", "RH", 68, 12, "academic"),  # Northeast
    "2": Building("2", "Founders Hall", "FH", 35, 42, "academic"),  # West-central
    "3": Building("3", "Alumni Hall", "AH", 50, 35, "academic"),  # Central
    "4": Building("4", "Peck Hall", "PH", 42, 28, "academic"),  # Central-north
    "5": Building("5", "Lovejoy Library", "LIB", 35, 32, "academic"),  # West-central
    "6": Building("6", "Dunham Hall", "DH", 52, 22, "academic"),  # Central-north
    "7": Building("7", "Science Buildings", "SCI", 30, 38, "academic"),  # West
    "8": Building("8", "Morris University Center", "MUC", 44, 36, "academic"),  # Center
    "9": Building("9", "Art and Design", "AD", 25, 32, "academic"),  # West
    "10": Building("10", "Center for Spirituality", "CS", 57, 30, "academic"),  # East-central
    "11": Building("11", "Metcalf Theater", "MT", 28, 45, "academic"),  # Southwest
    "19": Building("19", "Engineering Building", "EB", 32, 62, "academic"),  # South
    "20": Building("20", "Birger Hall", "BH", 75, 10, "academic"),  # Far northeast
    "27": Building("27", "School of Pharmacy", "PHAR", 85, 58, "academic"),  # Far east
    "31": Building("31", "Tech Management Center", "TMC", 88, 75, "academic"),  # Far southeast
    "37": Building("37", "Dental Clinic", "DC", 90, 65, "academic"),  # Far east
    "44": Building("44", "Student Success Center", "SSC", 52, 60, "academic"),  # South-central

    # Athletic/Recreation facilities
    "12": Building("12", "Student Fitness Center", "SFC", 20, 40, "athletic"),  # West
    "13": Building("13", "Vadalabene Center", "VC", 32, 48, "athletic"),  # Southwest
    "39": Building("39", "Swimming Pool", "POOL", 18, 58, "athletic"),  # Far west
    "41": Building("41", "Sports Complex", "SC", 8, 52, "athletic"),  # Far west

    # Residential Buildings
    "17": Building("17", "Woodland Hall", "WH", 48, 62, "residential"),  # South
    "18": Building("18", "Prairie Hall", "PRH", 58, 50, "residential"),  # Southeast
    "21": Building("21", "Bluff Hall", "BLF", 78, 18, "residential"),  # Northeast
    "33": Building("33", "Evergreen Hall", "EH", 15, 78, "residential"),  # Far southwest

    # Research & Other Buildings
    "23": Building("23", "200 University Park", "UP200", 72, 45, "other"),  # East
    "24": Building("24", "100 North Research Dr", "NRD100", 78, 28, "other"),  # Northeast
    "25": Building("25", "95 North Research Dr", "NRD95", 82, 35, "other"),  # East
    "26": Building("26", "Chamber of Commerce", "COC", 82, 48, "other"),  # East
    "34": Building("34", "47 North Research Dr", "NRD47", 85, 52, "other"),  # Far east
    "35": Building("35", "110 N Research Dr", "NRD110", 88, 55, "other"),  # Far east
    "32": Building("32", "Stratton Quadrangle", "SQ", 48, 20, "other"),  # North-central
    "45": Building("45", "Physics Observatory", "OBS", 22, 85, "other"),  # Far south
    "48": Building("48", "The Gardens", "GARD", 62, 8, "other"),  # Far north
    "49": Building("49", "The 'e' Sculpture", "ESCP", 92, 78, "other"),  # Far southeast

    # Parking Lots positioned to match map
    "P1": Building("P1", "Parking Lot P1", "P1", 52, 52, "parking"),  # Central-south
    "P2": Building("P2", "Parking Lot P2", "P2", 64, 48, "parking"),  # East
    "P3": Building("P3", "Parking Lot P3", "P3", 54, 42, "parking"),  # Central
    "P4": Building("P4", "Parking Lot P4", "P4", 55, 58, "parking"),  # South
    "P5": Building("P5", "Parking Lot P5", "P5", 70, 45, "parking"),  # East
    "P6": Building("P6", "Parking Lot P6", "P6", 60, 40, "parking"),  # East-central
    "P7": Building("P7", "Parking Lot P7", "P7", 68, 35, "parking"),  # East
    "P8": Building("P8", "Parking Lot P8", "P8", 72, 38, "parking"),  # East
    "P9": Building("P9", "Parking Lot P9", "P9", 65, 25, "parking"),  # Northeast
    "P10": Building("P10", "Parking Lot P10", "P10", 58, 22, "parking"),  # North
    "P11": Building("P11", "Parking Lot P11", "P11", 15, 38, "parking"),  # Far west
    "P12": Building("P12", "Parking Lot P12", "P12", 20, 52, "parking"),  # West
    "A": Building("A", "Parking Lot A", "PA", 38, 35, "parking"),  # Central
    "B": Building("B", "Parking Lot B", "PB", 36, 58, "parking"),  # South
    "C": Building("C", "Parking Lot C", "PC", 42, 54, "parking"),  # South
    "D": Building("D", "Parking Lot D", "PD", 25, 62, "parking"),  # Southwest
    "E": Building("E", "Parking Lot E", "PE", 26, 46, "parking"),  # West
    "F": Building("F", "Parking Lot F", "PF", 22, 36, "parking"),  # West
    "G": Building("G", "Parking Lot G", "PG", 38, 24, "parking"),  # North
}


def calculate_distance(b1: Building, b2: Building) -> float:
    """Calculate Euclidean distance between two buildings (scaled to approximate meters)."""
    # Scale factor: 1 unit ≈ 20 meters (campus is roughly 2km x 1.5km)
    dx = b1.x - b2.x
    dy = b1.y - b2.y
    return round(math.sqrt(dx*dx + dy*dy) * 20, 1)


# Define edges (connections between buildings/locations)
# These represent actual walkways and paths on campus
EDGE_DEFINITIONS: List[Tuple[str, str, str]] = [
    # Core Academic Quad connections
    ("8", "5", "walkway"),    # MUC to Library
    ("8", "2", "walkway"),    # MUC to Founders
    ("8", "3", "walkway"),    # MUC to Alumni
    ("8", "A", "walkway"),    # MUC to Lot A
    ("5", "7", "walkway"),    # Library to Science
    ("5", "4", "walkway"),    # Library to Peck
    ("5", "2", "walkway"),    # Library to Founders
    ("4", "6", "walkway"),    # Peck to Dunham
    ("4", "32", "walkway"),   # Peck to Stratton Quad
    ("6", "10", "walkway"),   # Dunham to Spirituality Center
    ("6", "P10", "walkway"),  # Dunham to P10
    ("3", "P3", "walkway"),   # Alumni to P3
    ("2", "7", "walkway"),    # Founders to Science
    ("2", "11", "walkway"),   # Founders to Metcalf
    ("7", "E", "walkway"),    # Science to Lot E
    ("7", "13", "walkway"),   # Science to Vadalabene

    # Art and Fitness area
    ("9", "F", "walkway"),    # Art to Lot F
    ("9", "12", "walkway"),   # Art to Fitness
    ("9", "5", "walkway"),    # Art to Library
    ("12", "F", "walkway"),   # Fitness to Lot F
    ("12", "P11", "walkway"), # Fitness to P11
    ("12", "41", "walkway"),  # Fitness to Sports Complex
    ("13", "A", "walkway"),   # Vadalabene to Lot A
    ("13", "8", "walkway"),   # Vadalabene to MUC

    # Metcalf and surrounding
    ("11", "E", "walkway"),   # Metcalf to Lot E
    ("11", "F", "walkway"),   # Metcalf to Lot F

    # North campus (Rendleman, Birger, Gardens)
    ("1", "20", "walkway"),   # Rendleman to Birger
    ("1", "21", "walkway"),   # Rendleman to Bluff
    ("1", "48", "walkway"),   # Rendleman to Gardens
    ("20", "48", "walkway"),  # Birger to Gardens
    ("21", "24", "walkway"),  # Bluff to 100 NRD
    ("48", "P9", "road"),     # Gardens to P9

    # Research Drive corridor
    ("10", "P9", "walkway"),  # Spirituality to P9
    ("P9", "P7", "road"),     # P9 to P7
    ("P7", "P8", "road"),     # P7 to P8
    ("P8", "24", "road"),     # P8 to 100 NRD
    ("24", "25", "road"),     # 100 NRD to 95 NRD
    ("P8", "P5", "road"),     # P8 to P5
    ("P5", "23", "road"),     # P5 to 200 UP
    ("23", "26", "road"),     # 200 UP to Chamber
    ("26", "34", "road"),     # Chamber to 47 NRD
    ("34", "35", "road"),     # 47 NRD to 110 NRD
    ("35", "27", "road"),     # 110 NRD to Pharmacy
    ("27", "37", "road"),     # Pharmacy to Dental

    # Central parking connections
    ("P3", "P6", "road"),     # P3 to P6
    ("P6", "P7", "road"),     # P6 to P7
    ("P6", "18", "walkway"),  # P6 to Prairie
    ("P1", "P2", "road"),     # P1 to P2
    ("P2", "P5", "road"),     # P2 to P5
    ("P1", "C", "road"),      # P1 to Lot C
    ("P4", "17", "walkway"),  # P4 to Woodland
    ("P4", "P1", "road"),     # P4 to P1

    # South campus (Engineering, Housing)
    ("19", "B", "walkway"),   # Engineering to Lot B
    ("19", "D", "walkway"),   # Engineering to Lot D
    ("19", "44", "walkway"),  # Engineering to Student Success
    ("B", "C", "road"),       # Lot B to Lot C
    ("C", "44", "walkway"),   # Lot C to Student Success
    ("17", "19", "walkway"),  # Woodland to Engineering
    ("17", "18", "walkway"),  # Woodland to Prairie

    # Far south
    ("D", "33", "road"),      # Lot D to Evergreen
    ("33", "45", "road"),     # Evergreen to Observatory

    # Tech/Management area
    ("31", "37", "road"),     # TMC to Dental
    ("31", "49", "road"),     # TMC to e Sculpture
    ("27", "31", "road"),     # Pharmacy to TMC

    # Additional cross-campus connections
    ("A", "5", "walkway"),    # Lot A to Library
    ("G", "32", "walkway"),   # Lot G to Stratton
    ("G", "P12", "road"),     # Lot G to P12
    ("P12", "39", "road"),    # P12 to Pool
    ("39", "41", "road"),     # Pool to Sports Complex
    ("32", "6", "walkway"),   # Stratton to Dunham
    ("18", "23", "walkway"),  # Prairie to 200 UP
    ("3", "10", "walkway"),   # Alumni to Spirituality
]


def build_edges() -> List[Edge]:
    """Build edge list with calculated distances."""
    edges = []
    for source, target, path_type in EDGE_DEFINITIONS:
        if source in BUILDINGS and target in BUILDINGS:
            b1 = BUILDINGS[source]
            b2 = BUILDINGS[target]
            distance = calculate_distance(b1, b2)

            # Adjust weight based on path type
            if path_type == "road":
                distance *= 1.1  # Roads are slightly longer (less direct)
            elif path_type == "covered":
                distance *= 0.95  # Covered paths feel shorter

            edges.append(Edge(source, target, distance, path_type))
    return edges


EDGES: List[Edge] = build_edges()


def get_graph_data() -> Dict[str, Any]:
    """Return graph data in a format suitable for the frontend."""
    nodes = []
    for bid, building in BUILDINGS.items():
        nodes.append({
            "id": bid,
            "name": building.name,
            "shortName": building.short_name,
            "x": building.x,
            "y": building.y,
            "type": building.building_type,
        })

    edges = []
    for edge in EDGES:
        edges.append({
            "source": edge.source,
            "target": edge.target,
            "weight": edge.weight,
            "pathType": edge.path_type,
        })

    return {
        "nodes": nodes,
        "edges": edges,
    }


def get_adjacency_list() -> Dict[str, List[Tuple[str, float]]]:
    """Build adjacency list for pathfinding algorithms."""
    adj: Dict[str, List[Tuple[str, float]]] = {bid: [] for bid in BUILDINGS}

    for edge in EDGES:
        # Bidirectional edges
        adj[edge.source].append((edge.target, edge.weight))
        adj[edge.target].append((edge.source, edge.weight))

    return adj


# Building categories for filtering
BUILDING_CATEGORIES = {
    "academic": [b.id for b in BUILDINGS.values() if b.building_type == "academic"],
    "residential": [b.id for b in BUILDINGS.values() if b.building_type == "residential"],
    "athletic": [b.id for b in BUILDINGS.values() if b.building_type == "athletic"],
    "parking": [b.id for b in BUILDINGS.values() if b.building_type == "parking"],
    "other": [b.id for b in BUILDINGS.values() if b.building_type == "other"],
}
