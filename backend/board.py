from enum import Enum
from typing import Optional
from pydantic import BaseModel


class SpaceType(str, Enum):
    PROPERTY = "PROPERTY"
    RAILROAD = "RAILROAD"
    UTILITY = "UTILITY"
    TAX = "TAX"
    CHANCE = "CHANCE"
    COMMUNITY_CHEST = "COMMUNITY_CHEST"
    GO = "GO"
    JAIL = "JAIL"
    FREE_PARKING = "FREE_PARKING"
    GO_TO_JAIL = "GO_TO_JAIL"


class Space(BaseModel):
    position: int
    name: str
    space_type: SpaceType
    group: Optional[str] = None
    price: Optional[int] = None
    rent: list[int] = []
    house_cost: Optional[int] = None
    mortgage_value: Optional[int] = None
    tax_amount: Optional[int] = None
    owner_id: Optional[str] = None
    houses: int = 0
    has_hotel: bool = False
    is_mortgaged: bool = False


COLOR_GROUPS: dict[str, list[int]] = {
    "Brown": [1, 3],
    "Light Blue": [6, 8, 9],
    "Pink": [11, 13, 14],
    "Orange": [16, 18, 19],
    "Red": [21, 23, 24],
    "Yellow": [26, 27, 29],
    "Green": [31, 32, 34],
    "Dark Blue": [37, 39],
    "Railroad": [5, 15, 25, 35],
    "Utility": [12, 28],
}

BOARD_TEMPLATE: list[dict] = [
    # 0: Go
    {
        "position": 0,
        "name": "Go",
        "space_type": SpaceType.GO,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 1: Mediterranean Avenue
    {
        "position": 1,
        "name": "Mediterranean Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Brown",
        "price": 60,
        "rent": [2, 10, 30, 90, 160, 250],
        "house_cost": 50,
        "mortgage_value": 30,
        "tax_amount": None,
    },
    # 2: Community Chest
    {
        "position": 2,
        "name": "Community Chest",
        "space_type": SpaceType.COMMUNITY_CHEST,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 3: Baltic Avenue
    {
        "position": 3,
        "name": "Baltic Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Brown",
        "price": 60,
        "rent": [4, 20, 60, 180, 320, 450],
        "house_cost": 50,
        "mortgage_value": 30,
        "tax_amount": None,
    },
    # 4: Income Tax
    {
        "position": 4,
        "name": "Income Tax",
        "space_type": SpaceType.TAX,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": 200,
    },
    # 5: Reading Railroad
    {
        "position": 5,
        "name": "Reading Railroad",
        "space_type": SpaceType.RAILROAD,
        "group": "Railroad",
        "price": 200,
        "rent": [25, 50, 100, 200],
        "house_cost": None,
        "mortgage_value": 100,
        "tax_amount": None,
    },
    # 6: Oriental Avenue
    {
        "position": 6,
        "name": "Oriental Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Light Blue",
        "price": 100,
        "rent": [6, 30, 90, 270, 400, 550],
        "house_cost": 50,
        "mortgage_value": 50,
        "tax_amount": None,
    },
    # 7: Chance
    {
        "position": 7,
        "name": "Chance",
        "space_type": SpaceType.CHANCE,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 8: Vermont Avenue
    {
        "position": 8,
        "name": "Vermont Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Light Blue",
        "price": 100,
        "rent": [6, 30, 90, 270, 400, 550],
        "house_cost": 50,
        "mortgage_value": 50,
        "tax_amount": None,
    },
    # 9: Connecticut Avenue
    {
        "position": 9,
        "name": "Connecticut Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Light Blue",
        "price": 120,
        "rent": [8, 40, 100, 300, 450, 600],
        "house_cost": 50,
        "mortgage_value": 60,
        "tax_amount": None,
    },
    # 10: Jail / Just Visiting
    {
        "position": 10,
        "name": "Jail / Just Visiting",
        "space_type": SpaceType.JAIL,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 11: St. Charles Place
    {
        "position": 11,
        "name": "St. Charles Place",
        "space_type": SpaceType.PROPERTY,
        "group": "Pink",
        "price": 140,
        "rent": [10, 50, 150, 450, 625, 750],
        "house_cost": 100,
        "mortgage_value": 70,
        "tax_amount": None,
    },
    # 12: Electric Company
    {
        "position": 12,
        "name": "Electric Company",
        "space_type": SpaceType.UTILITY,
        "group": "Utility",
        "price": 150,
        "rent": [],
        "house_cost": None,
        "mortgage_value": 75,
        "tax_amount": None,
    },
    # 13: States Avenue
    {
        "position": 13,
        "name": "States Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Pink",
        "price": 140,
        "rent": [10, 50, 150, 450, 625, 750],
        "house_cost": 100,
        "mortgage_value": 70,
        "tax_amount": None,
    },
    # 14: Virginia Avenue
    {
        "position": 14,
        "name": "Virginia Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Pink",
        "price": 160,
        "rent": [12, 60, 180, 500, 700, 900],
        "house_cost": 100,
        "mortgage_value": 80,
        "tax_amount": None,
    },
    # 15: Pennsylvania Railroad
    {
        "position": 15,
        "name": "Pennsylvania Railroad",
        "space_type": SpaceType.RAILROAD,
        "group": "Railroad",
        "price": 200,
        "rent": [25, 50, 100, 200],
        "house_cost": None,
        "mortgage_value": 100,
        "tax_amount": None,
    },
    # 16: St. James Place
    {
        "position": 16,
        "name": "St. James Place",
        "space_type": SpaceType.PROPERTY,
        "group": "Orange",
        "price": 180,
        "rent": [14, 70, 200, 550, 750, 950],
        "house_cost": 100,
        "mortgage_value": 90,
        "tax_amount": None,
    },
    # 17: Community Chest
    {
        "position": 17,
        "name": "Community Chest",
        "space_type": SpaceType.COMMUNITY_CHEST,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 18: Tennessee Avenue
    {
        "position": 18,
        "name": "Tennessee Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Orange",
        "price": 180,
        "rent": [14, 70, 200, 550, 750, 950],
        "house_cost": 100,
        "mortgage_value": 90,
        "tax_amount": None,
    },
    # 19: New York Avenue
    {
        "position": 19,
        "name": "New York Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Orange",
        "price": 200,
        "rent": [16, 80, 220, 600, 800, 1000],
        "house_cost": 100,
        "mortgage_value": 100,
        "tax_amount": None,
    },
    # 20: Free Parking
    {
        "position": 20,
        "name": "Free Parking",
        "space_type": SpaceType.FREE_PARKING,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 21: Kentucky Avenue
    {
        "position": 21,
        "name": "Kentucky Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Red",
        "price": 220,
        "rent": [18, 90, 250, 700, 875, 1050],
        "house_cost": 150,
        "mortgage_value": 110,
        "tax_amount": None,
    },
    # 22: Chance
    {
        "position": 22,
        "name": "Chance",
        "space_type": SpaceType.CHANCE,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 23: Indiana Avenue
    {
        "position": 23,
        "name": "Indiana Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Red",
        "price": 220,
        "rent": [18, 90, 250, 700, 875, 1050],
        "house_cost": 150,
        "mortgage_value": 110,
        "tax_amount": None,
    },
    # 24: Illinois Avenue
    {
        "position": 24,
        "name": "Illinois Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Red",
        "price": 240,
        "rent": [20, 100, 300, 750, 925, 1100],
        "house_cost": 150,
        "mortgage_value": 120,
        "tax_amount": None,
    },
    # 25: B&O Railroad
    {
        "position": 25,
        "name": "B&O Railroad",
        "space_type": SpaceType.RAILROAD,
        "group": "Railroad",
        "price": 200,
        "rent": [25, 50, 100, 200],
        "house_cost": None,
        "mortgage_value": 100,
        "tax_amount": None,
    },
    # 26: Atlantic Avenue
    {
        "position": 26,
        "name": "Atlantic Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Yellow",
        "price": 260,
        "rent": [22, 110, 330, 800, 975, 1150],
        "house_cost": 150,
        "mortgage_value": 130,
        "tax_amount": None,
    },
    # 27: Ventnor Avenue
    {
        "position": 27,
        "name": "Ventnor Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Yellow",
        "price": 260,
        "rent": [22, 110, 330, 800, 975, 1150],
        "house_cost": 150,
        "mortgage_value": 130,
        "tax_amount": None,
    },
    # 28: Water Works
    {
        "position": 28,
        "name": "Water Works",
        "space_type": SpaceType.UTILITY,
        "group": "Utility",
        "price": 150,
        "rent": [],
        "house_cost": None,
        "mortgage_value": 75,
        "tax_amount": None,
    },
    # 29: Marvin Gardens
    {
        "position": 29,
        "name": "Marvin Gardens",
        "space_type": SpaceType.PROPERTY,
        "group": "Yellow",
        "price": 280,
        "rent": [24, 120, 360, 850, 1025, 1200],
        "house_cost": 150,
        "mortgage_value": 140,
        "tax_amount": None,
    },
    # 30: Go To Jail
    {
        "position": 30,
        "name": "Go To Jail",
        "space_type": SpaceType.GO_TO_JAIL,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 31: Pacific Avenue
    {
        "position": 31,
        "name": "Pacific Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Green",
        "price": 300,
        "rent": [26, 130, 390, 900, 1100, 1275],
        "house_cost": 200,
        "mortgage_value": 150,
        "tax_amount": None,
    },
    # 32: North Carolina Avenue
    {
        "position": 32,
        "name": "North Carolina Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Green",
        "price": 300,
        "rent": [26, 130, 390, 900, 1100, 1275],
        "house_cost": 200,
        "mortgage_value": 150,
        "tax_amount": None,
    },
    # 33: Community Chest
    {
        "position": 33,
        "name": "Community Chest",
        "space_type": SpaceType.COMMUNITY_CHEST,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 34: Pennsylvania Avenue
    {
        "position": 34,
        "name": "Pennsylvania Avenue",
        "space_type": SpaceType.PROPERTY,
        "group": "Green",
        "price": 320,
        "rent": [28, 150, 450, 1000, 1200, 1400],
        "house_cost": 200,
        "mortgage_value": 160,
        "tax_amount": None,
    },
    # 35: Short Line
    {
        "position": 35,
        "name": "Short Line",
        "space_type": SpaceType.RAILROAD,
        "group": "Railroad",
        "price": 200,
        "rent": [25, 50, 100, 200],
        "house_cost": None,
        "mortgage_value": 100,
        "tax_amount": None,
    },
    # 36: Chance
    {
        "position": 36,
        "name": "Chance",
        "space_type": SpaceType.CHANCE,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": None,
    },
    # 37: Park Place
    {
        "position": 37,
        "name": "Park Place",
        "space_type": SpaceType.PROPERTY,
        "group": "Dark Blue",
        "price": 350,
        "rent": [35, 175, 500, 1100, 1300, 1500],
        "house_cost": 200,
        "mortgage_value": 175,
        "tax_amount": None,
    },
    # 38: Luxury Tax
    {
        "position": 38,
        "name": "Luxury Tax",
        "space_type": SpaceType.TAX,
        "group": None,
        "price": None,
        "rent": [],
        "house_cost": None,
        "mortgage_value": None,
        "tax_amount": 100,
    },
    # 39: Boardwalk
    {
        "position": 39,
        "name": "Boardwalk",
        "space_type": SpaceType.PROPERTY,
        "group": "Dark Blue",
        "price": 400,
        "rent": [50, 200, 600, 1400, 1700, 2000],
        "house_cost": 200,
        "mortgage_value": 200,
        "tax_amount": None,
    },
]


def build_board() -> list[Space]:
    """Construct and return a fresh list of 40 Space instances from BOARD_TEMPLATE."""
    return [Space(**entry) for entry in BOARD_TEMPLATE]
