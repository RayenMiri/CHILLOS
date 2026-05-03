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
        if winner and winner.cash >= auction.highest_bid:
            winner.cash -= auction.highest_bid
            space.owner_id = winner.id
            winner.properties.append(str(auction.property_position))
            session.log.append(
                f"{winner.nickname} won auction for {space.name} with bid ${auction.highest_bid}"
            )
        else:
            session.log.append(f"Auction for {space.name} — winner could not pay, property remains unowned")
    else:
        session.log.append(f"No bids — {space.name} remains unowned")
    session.auction = None
    session.phase = "turn_action"


def owner_has_monopoly(session: "GameSession", group: str) -> bool:
    """Return True if all spaces in `group` have the same non-None owner."""
    positions = COLOR_GROUPS.get(group, [])
    if not positions:
        return False
    owner = session.board[positions[0]].owner_id
    if owner is None:
        return False
    return all(session.board[pos].owner_id == owner for pos in positions)


def can_build_on(session: "GameSession", player_id: str, position: int) -> str | None:
    """Return error string if player cannot build on space at position, else None."""
    space = session.board[position]
    if space.space_type != SpaceType.PROPERTY:
        return "Can only build on color properties"
    if space.owner_id != player_id:
        return "You don't own this property"
    if space.is_mortgaged:
        return "Cannot build on mortgaged property"
    group = space.group
    if not group or not owner_has_monopoly(session, group):
        return "Must own full color group to build"
    group_positions = COLOR_GROUPS[group]
    for pos in group_positions:
        if session.board[pos].is_mortgaged:
            return "Cannot build while any group property is mortgaged"
    if space.has_hotel:
        return "Already has a hotel"
    # Even build rule
    active_houses = [
        s.houses for s in (session.board[pos] for pos in group_positions) if not s.has_hotel
    ]
    if active_houses and space.houses > min(active_houses):
        return "Even build rule: build on property with fewer houses first"
    return None


def can_sell_from(session: "GameSession", player_id: str, position: int) -> str | None:
    """Return error string if player cannot sell a building from space at position, else None."""
    space = session.board[position]
    if space.owner_id != player_id:
        return "You don't own this property"
    if space.houses == 0 and not space.has_hotel:
        return "No buildings to sell"
    group = space.group
    if not group:
        return "Property has no group"
    group_positions = COLOR_GROUPS[group]
    if space.has_hotel:
        return None  # always allowed to sell a hotel
    max_houses = max(session.board[pos].houses for pos in group_positions)
    if space.houses < max_houses:
        return "Even sell rule: sell from property with most houses first"
    return None


def apply_trade(session: "GameSession", trade: "TradeOffer") -> None:
    giver = session.players[trade.from_player]
    receiver = session.players[trade.to_player]

    giver.cash -= trade.give_cash
    receiver.cash += trade.give_cash
    giver.cash += trade.request_cash
    receiver.cash -= trade.request_cash

    for pos in trade.give_properties:
        space = session.board[pos]
        space.owner_id = trade.to_player
        prop_str = str(pos)
        if prop_str in giver.properties:
            giver.properties.remove(prop_str)
        if prop_str not in receiver.properties:
            receiver.properties.append(prop_str)

    for pos in trade.request_properties:
        space = session.board[pos]
        space.owner_id = trade.from_player
        prop_str = str(pos)
        if prop_str in receiver.properties:
            receiver.properties.remove(prop_str)
        if prop_str not in giver.properties:
            giver.properties.append(prop_str)

    giver.get_out_of_jail_free -= trade.give_jail_cards
    receiver.get_out_of_jail_free += trade.give_jail_cards
    giver.get_out_of_jail_free += trade.request_jail_cards
    receiver.get_out_of_jail_free -= trade.request_jail_cards

    session.log.append(
        f"Trade complete: {giver.nickname} ↔ {receiver.nickname}"
    )


def resolve_bankruptcy(session: "GameSession", debtor_id: str, creditor_id: str | None) -> None:
    debtor = session.players[debtor_id]
    debtor.is_bankrupt = True
    for space in session.board:
        if space.owner_id == debtor_id:
            if creditor_id:
                space.owner_id = creditor_id
                creditor = session.players[creditor_id]
                prop_str = str(space.position)
                if prop_str not in creditor.properties:
                    creditor.properties.append(prop_str)
            else:
                space.owner_id = None
                space.houses = 0
                space.has_hotel = False
                space.is_mortgaged = False
    if creditor_id:
        creditor = session.players[creditor_id]
        creditor.cash += max(0, debtor.cash)
    debtor.cash = 0
    debtor.properties.clear()
    session.log.append(f"{debtor.nickname} has gone bankrupt!")


def get_active_players(session: "GameSession") -> list[Player]:
    return [p for p in session.players.values() if not p.is_bankrupt]


def check_win_condition(session: "GameSession") -> str | None:
    active = get_active_players(session)
    if len(active) == 1:
        winner = active[0]
        session.status = "game_over"
        session.log.append(f"{winner.nickname} wins the game!")
        return winner.id
    return None
