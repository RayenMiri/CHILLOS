"""Core data models for a Monopoly-style game session."""

from datetime import datetime, timezone, timedelta

from pydantic import BaseModel

from board import COLOR_GROUPS, Space, SpaceType
from cards import Card
from player import Player


class AuctionState(BaseModel):
    property_position: int
    bids: dict[str, int] = {}
    highest_bidder: str | None = None
    highest_bid: int = 0
    ends_at: datetime


class TradeOffer(BaseModel):
    from_player: str
    to_player: str
    give_properties: list[int] = []
    give_cash: int = 0
    give_jail_cards: int = 0
    request_properties: list[int] = []
    request_cash: int = 0
    request_jail_cards: int = 0
    status: str = "pending"


class GameSession(BaseModel):
    code: str
    host_id: str
    players: dict[str, Player] = {}
    max_players: int = 4
    status: str = "waiting"
    phase: str = "turn_roll"
    current_player_index: int = 0
    board: list[Space] = []
    chance_deck: list[Card] = []
    community_deck: list[Card] = []
    dice: tuple[int, int] | None = None
    doubles_count: int = 0
    auction: AuctionState | None = None
    pending_trade: TradeOffer | None = None
    log: list[str] = []
    created_at: datetime


def calculate_rent(session: GameSession, space: Space, dice_sum: int) -> int:
    """Return rent owed for landing on a space. Returns 0 if mortgaged or unowned."""
    if space.is_mortgaged:
        return 0
    if space.owner_id is None:
        return 0

    owner_id: str = space.owner_id

    if space.space_type == SpaceType.RAILROAD:
        positions = COLOR_GROUPS["Railroad"]
        count = sum(
            1
            for pos in positions
            if session.board[pos].owner_id == owner_id
            and not session.board[pos].is_mortgaged
        )
        return 25 * (2 ** (count - 1)) if count > 0 else 0

    if space.space_type == SpaceType.UTILITY:
        positions = COLOR_GROUPS["Utility"]
        count = sum(
            1
            for pos in positions
            if session.board[pos].owner_id == owner_id
            and not session.board[pos].is_mortgaged
        )
        if count == 1:
            return 4 * dice_sum
        if count >= 2:
            return 10 * dice_sum
        return 0

    if space.space_type == SpaceType.PROPERTY:
        group = space.group
        if group is None or group not in COLOR_GROUPS:
            return space.rent[0] if space.rent else 0

        group_positions = COLOR_GROUPS[group]
        monopoly = all(
            session.board[pos].owner_id == owner_id for pos in group_positions
        )

        if space.has_hotel:
            return space.rent[5] if len(space.rent) > 5 else 0
        if space.houses > 0:
            idx = space.houses
            return space.rent[idx] if len(space.rent) > idx else 0
        if monopoly:
            return space.rent[0] * 2 if space.rent else 0
        return space.rent[0] if space.rent else 0

    return 0


def start_auction(session: "GameSession", position: int) -> None:
    session.auction = AuctionState(
        property_position=position,
        ends_at=datetime.now(timezone.utc) + timedelta(seconds=10),
    )
    session.phase = "auction"
    space = session.board[position]
    session.log.append(f"Auction started for {space.name}!")


def resolve_auction(session: "GameSession") -> None:
    auction = session.auction
    if not auction:
        return
    space = session.board[auction.property_position]
    if auction.highest_bidder:
        winner = session.players.get(auction.highest_bidder)
        if winner:
            winner.cash -= auction.highest_bid
            space.owner_id = winner.id
            winner.properties.append(str(auction.property_position))
            session.log.append(
                f"{winner.nickname} won auction for {space.name} with bid ${auction.highest_bid}"
            )
    else:
        session.log.append(f"No bids — {space.name} remains unowned")
    session.auction = None
    session.phase = "turn_action"
