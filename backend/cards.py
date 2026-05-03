"""Card definitions for Chance and Community Chest decks."""

import random
from enum import Enum

from pydantic import BaseModel


class CardAction(str, Enum):
    ADVANCE_TO_GO = "ADVANCE_TO_GO"
    ADVANCE_TO_POSITION = "ADVANCE_TO_POSITION"
    ADVANCE_TO_NEAREST_UTILITY = "ADVANCE_TO_NEAREST_UTILITY"
    ADVANCE_TO_NEAREST_RAILROAD = "ADVANCE_TO_NEAREST_RAILROAD"
    BANK_PAYS = "BANK_PAYS"
    GET_OUT_OF_JAIL_FREE = "GET_OUT_OF_JAIL_FREE"
    GO_BACK_3 = "GO_BACK_3"
    GO_TO_JAIL = "GO_TO_JAIL"
    REPAIRS = "REPAIRS"
    PAY_BANK = "PAY_BANK"
    COLLECT_FROM_PLAYERS = "COLLECT_FROM_PLAYERS"


class Card(BaseModel):
    description: str
    action: CardAction
    position: int | None = None
    amount: int | None = None
    house_cost: int | None = None
    hotel_cost: int | None = None


CHANCE_CARDS: list[Card] = [
    Card(description="Advance to Go (collect $200)", action=CardAction.ADVANCE_TO_GO),
    Card(description="Advance to Illinois Ave", action=CardAction.ADVANCE_TO_POSITION, position=24),
    Card(description="Advance to St. Charles Place", action=CardAction.ADVANCE_TO_POSITION, position=11),
    Card(description="Advance to nearest Utility", action=CardAction.ADVANCE_TO_NEAREST_UTILITY),
    Card(description="Advance to nearest Railroad", action=CardAction.ADVANCE_TO_NEAREST_RAILROAD),
    Card(description="Bank pays you $50", action=CardAction.BANK_PAYS, amount=50),
    Card(description="Get Out of Jail Free", action=CardAction.GET_OUT_OF_JAIL_FREE),
    Card(description="Go Back 3 Spaces", action=CardAction.GO_BACK_3),
    Card(description="Go to Jail", action=CardAction.GO_TO_JAIL),
    Card(description="Make general repairs ($25/house, $100/hotel)", action=CardAction.REPAIRS, house_cost=25, hotel_cost=100),
    Card(description="Pay poor tax $15", action=CardAction.PAY_BANK, amount=15),
    Card(description="Take trip to Reading Railroad", action=CardAction.ADVANCE_TO_POSITION, position=5),
    Card(description="Advance to Boardwalk", action=CardAction.ADVANCE_TO_POSITION, position=39),
    Card(description="Elected chairman of the board — pay each player $50", action=CardAction.COLLECT_FROM_PLAYERS, amount=50),
    Card(description="Building loan matures, collect $150", action=CardAction.BANK_PAYS, amount=150),
    Card(description="Won crossword competition, collect $100", action=CardAction.BANK_PAYS, amount=100),
]

COMMUNITY_CHEST_CARDS: list[Card] = [
    Card(description="Advance to Go", action=CardAction.ADVANCE_TO_GO),
    Card(description="Bank error in your favor, collect $200", action=CardAction.BANK_PAYS, amount=200),
    Card(description="Doctor's fee, pay $50", action=CardAction.PAY_BANK, amount=50),
    Card(description="From sale of stock, collect $50", action=CardAction.BANK_PAYS, amount=50),
    Card(description="Get Out of Jail Free", action=CardAction.GET_OUT_OF_JAIL_FREE),
    Card(description="Go to Jail", action=CardAction.GO_TO_JAIL),
    Card(description="Holiday fund matures, collect $100", action=CardAction.BANK_PAYS, amount=100),
    Card(description="Income tax refund, collect $20", action=CardAction.BANK_PAYS, amount=20),
    Card(description="It's your birthday, collect $10 from each player", action=CardAction.COLLECT_FROM_PLAYERS, amount=10),
    Card(description="Life insurance matures, collect $100", action=CardAction.BANK_PAYS, amount=100),
    Card(description="Pay hospital fees $100", action=CardAction.PAY_BANK, amount=100),
    Card(description="Pay school fees $150", action=CardAction.PAY_BANK, amount=150),
    Card(description="Receive $25 consultancy fee", action=CardAction.BANK_PAYS, amount=25),
    Card(description="Street repairs ($40/house, $115/hotel)", action=CardAction.REPAIRS, house_cost=40, hotel_cost=115),
    Card(description="Won second prize in beauty contest, collect $10", action=CardAction.BANK_PAYS, amount=10),
    Card(description="Inherit $100", action=CardAction.BANK_PAYS, amount=100),
]


def build_chance_deck() -> list[Card]:
    """Return a shuffled copy of the Chance deck."""
    return random.sample(CHANCE_CARDS, len(CHANCE_CARDS))


def build_community_chest_deck() -> list[Card]:
    """Return a shuffled copy of the Community Chest deck."""
    return random.sample(COMMUNITY_CHEST_CARDS, len(COMMUNITY_CHEST_CARDS))
