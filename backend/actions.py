"""Action handlers for a Monopoly-style game. Pure business logic, no FastAPI imports."""

import asyncio
import random
from datetime import datetime
from typing import Literal

from board import COLOR_GROUPS, Space, SpaceType, build_board
from cards import Card, CardAction, build_chance_deck, build_community_chest_deck
from game_state import AuctionState, GameSession, calculate_rent, start_auction, can_build_on, can_sell_from
from player import Player

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BUYABLE_TYPES: frozenset[SpaceType] = frozenset(
    {SpaceType.PROPERTY, SpaceType.RAILROAD, SpaceType.UTILITY}
)


def _get_current_player(session: GameSession) -> Player:
    """Return the Player whose turn it currently is."""
    players = list(session.players.values())
    return players[session.current_player_index]


def _log(session: GameSession, message: str) -> None:
    session.log.append(message)


def _advance_turn(session: GameSession) -> None:
    """Move current_player_index to the next non-bankrupt player."""
    players = list(session.players.values())
    n = len(players)
    for i in range(1, n + 1):
        idx = (session.current_player_index + i) % n
        if not players[idx].is_bankrupt:
            session.current_player_index = idx
            return


def _check_win(session: GameSession) -> bool:
    """Return True if the game is over; set status and log winner."""
    active = [p for p in session.players.values() if not p.is_bankrupt]
    if len(active) == 1:
        session.status = "game_over"
        session.phase = "game_over"
        _log(session, f"{active[0].nickname} wins the game!")
        return True
    return False


def _nearest_position(current: int, targets: list[int]) -> tuple[int, bool]:
    """Return (nearest_target, passes_go).

    *passes_go* is True when the nearest target is behind the player on the
    board (i.e. the player would cross position 0 to reach it).
    """
    best: int | None = None
    best_steps = 41
    for t in targets:
        steps = (t - current) % 40
        if steps == 0:
            steps = 40
        if steps < best_steps:
            best_steps = steps
            best = t
    assert best is not None
    passes_go = best < current or (best == current)  # wrapped around
    # More precise: passes go if best_steps caused a wrap
    passes_go = (current + best_steps) >= 40
    return best, passes_go


# ---------------------------------------------------------------------------
# Card application
# ---------------------------------------------------------------------------

def _apply_card(session: GameSession, player: Player, card: Card) -> None:
    """Apply a drawn card's effect to the player/session."""
    _log(session, f"{player.nickname} drew: {card.description}")

    match card.action:
        case CardAction.ADVANCE_TO_GO:
            player.cash += 200
            player.position = 0
            _log(session, f"{player.nickname} advanced to Go, collected $200.")

        case CardAction.ADVANCE_TO_POSITION:
            target: int = card.position  # type: ignore[assignment]
            if target < player.position:
                player.cash += 200
                _log(session, f"{player.nickname} passed Go, collected $200.")
            player.position = target
            space = session.board[target]
            _log(session, f"{player.nickname} moved to {space.name}.")
            _apply_space(session, player)

        case CardAction.ADVANCE_TO_NEAREST_UTILITY:
            nearest, passes_go = _nearest_position(player.position, [12, 28])
            if passes_go:
                player.cash += 200
                _log(session, f"{player.nickname} passed Go, collected $200.")
            player.position = nearest
            space = session.board[nearest]
            _log(session, f"{player.nickname} moved to {space.name}.")
            if space.owner_id and space.owner_id != player.id and not space.is_mortgaged:
                owner = session.players.get(space.owner_id)
                if owner and not owner.is_bankrupt:
                    dice_sum = sum(session.dice) if session.dice else 0
                    rent = 10 * dice_sum
                    player.cash -= rent
                    owner.cash += rent
                    _log(
                        session,
                        f"{player.nickname} paid ${rent} rent (10x dice) to {owner.nickname}.",
                    )
            else:
                _apply_space(session, player)

        case CardAction.ADVANCE_TO_NEAREST_RAILROAD:
            nearest, passes_go = _nearest_position(player.position, [5, 15, 25, 35])
            if passes_go:
                player.cash += 200
                _log(session, f"{player.nickname} passed Go, collected $200.")
            player.position = nearest
            space = session.board[nearest]
            _log(session, f"{player.nickname} moved to {space.name}.")
            if space.owner_id and space.owner_id != player.id and not space.is_mortgaged:
                owner = session.players.get(space.owner_id)
                if owner and not owner.is_bankrupt:
                    # 2x normal railroad rent
                    normal_rent = calculate_rent(session, space, 0)
                    rent = normal_rent * 2
                    player.cash -= rent
                    owner.cash += rent
                    _log(
                        session,
                        f"{player.nickname} paid ${rent} rent (2x railroad) to {owner.nickname}.",
                    )
            else:
                _apply_space(session, player)

        case CardAction.BANK_PAYS:
            amount: int = card.amount or 0
            player.cash += amount
            _log(session, f"{player.nickname} received ${amount} from the bank.")

        case CardAction.GET_OUT_OF_JAIL_FREE:
            player.get_out_of_jail_free += 1
            _log(session, f"{player.nickname} received a Get Out of Jail Free card.")

        case CardAction.GO_BACK_3:
            new_pos = (player.position - 3) % 40
            _log(session, f"{player.nickname} went back 3 spaces to position {new_pos}.")
            player.position = new_pos
            _apply_space(session, player)

        case CardAction.GO_TO_JAIL:
            player.position = 10
            player.in_jail = True
            player.jail_turns = 0
            session.doubles_count = 0
            session.phase = "jail"
            _log(session, f"{player.nickname} was sent to Jail!")

        case CardAction.REPAIRS:
            house_cost: int = card.house_cost or 0
            hotel_cost: int = card.hotel_cost or 0
            total_houses = 0
            total_hotels = 0
            for pos_str in player.properties:
                space = session.board[int(pos_str)]
                if space.has_hotel:
                    total_hotels += 1
                else:
                    total_houses += space.houses
            total = total_houses * house_cost + total_hotels * hotel_cost
            player.cash -= total
            _log(
                session,
                f"{player.nickname} paid ${total} for repairs "
                f"({total_houses} houses, {total_hotels} hotels).",
            )

        case CardAction.PAY_BANK:
            amount = card.amount or 0
            player.cash -= amount
            _log(session, f"{player.nickname} paid ${amount} to the bank.")

        case CardAction.COLLECT_FROM_PLAYERS:
            amount = card.amount or 0
            for other in session.players.values():
                if other.id != player.id and not other.is_bankrupt:
                    other.cash -= amount
                    player.cash += amount
            _log(
                session,
                f"{player.nickname} collected ${amount} from each other player.",
            )


# ---------------------------------------------------------------------------
# Space application
# ---------------------------------------------------------------------------

def _apply_space(session: GameSession, player: Player) -> None:
    """Handle the effect of a player landing on a board space."""
    space: Space = session.board[player.position]

    match space.space_type:
        case SpaceType.GO | SpaceType.JAIL | SpaceType.FREE_PARKING:
            pass  # no effect

        case SpaceType.GO_TO_JAIL:
            player.position = 10
            player.in_jail = True
            player.jail_turns = 0
            session.doubles_count = 0
            session.phase = "jail"
            _log(session, f"{player.nickname} was sent to Jail!")

        case SpaceType.TAX:
            amount: int = space.tax_amount or 0
            player.cash -= amount
            _log(session, f"{player.nickname} paid ${amount} tax on {space.name}.")

        case SpaceType.CHANCE:
            if session.chance_deck:
                card = session.chance_deck.pop(0)
                session.chance_deck.append(card)
                _apply_card(session, player, card)

        case SpaceType.COMMUNITY_CHEST:
            if session.community_deck:
                card = session.community_deck.pop(0)
                session.community_deck.append(card)
                _apply_card(session, player, card)

        case SpaceType.PROPERTY | SpaceType.RAILROAD | SpaceType.UTILITY:
            if space.owner_id is None:
                # Player can buy or auction — phase stays "turn_action"
                pass
            elif space.owner_id == player.id:
                _log(session, f"{player.nickname} landed on their own property: {space.name}.")
            else:
                owner = session.players.get(space.owner_id)
                if owner and not owner.is_bankrupt and not space.is_mortgaged:
                    dice_sum = sum(session.dice) if session.dice else 0
                    rent = calculate_rent(session, space, dice_sum)
                    player.cash -= rent
                    owner.cash += rent
                    _log(
                        session,
                        f"{player.nickname} paid ${rent} rent to {owner.nickname} "
                        f"for {space.name}.",
                    )


# ---------------------------------------------------------------------------
# Public action handlers
# ---------------------------------------------------------------------------

def handle_start_game(session: GameSession, player_id: str) -> tuple[bool, str]:
    """Start the game. Only the host may call this; requires ≥ 2 players."""
    if player_id != session.host_id:
        return False, "Only the host can start the game."
    if len(session.players) < 2:
        return False, "Need at least 2 players to start."
    if session.status != "waiting":
        return False, "Game is not in waiting state."

    session.status = "started"
    session.phase = "turn_roll"
    session.board = build_board()
    session.chance_deck = build_chance_deck()
    session.community_deck = build_community_chest_deck()
    session.current_player_index = random.randint(0, len(session.players) - 1)
    _log(session, "Game started!")
    return True, ""


def handle_roll_dice(session: GameSession, player_id: str) -> tuple[bool, str]:
    """Roll the dice for the current player."""
    if session.status != "started":
        return False, "Game is not in progress."
    if session.phase != "turn_roll":
        return False, "Not the dice-rolling phase."
    player = _get_current_player(session)
    if player.id != player_id:
        return False, "It is not your turn."

    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    session.dice = (d1, d2)
    doubles = d1 == d2

    if doubles:
        session.doubles_count += 1

    # Three consecutive doubles → Go to Jail
    if session.doubles_count == 3:
        player.position = 10
        player.in_jail = True
        player.jail_turns = 0
        session.doubles_count = 0
        session.phase = "turn_action"
        _log(
            session,
            f"{player.nickname} rolled doubles three times in a row and was sent to Jail!",
        )
        return True, ""

    # Move player
    old_pos = player.position
    new_pos = (old_pos + d1 + d2) % 40

    # Passing Go: old position is ahead of new position (wrapped) but player was not already on Go
    if old_pos != 0 and new_pos <= old_pos and (old_pos + d1 + d2) >= 40:
        player.cash += 200
        _log(session, f"{player.nickname} passed Go and collected $200.")

    player.position = new_pos
    space: Space = session.board[new_pos]
    _log(
        session,
        f"{player.nickname} rolled {d1}+{d2}={d1 + d2}, moved to {space.name}.",
    )

    session.phase = "turn_action"
    _apply_space(session, player)
    return True, ""


def handle_buy_property(session: GameSession, player_id: str) -> tuple[bool, str]:
    """Current player buys the property they are standing on."""
    if session.phase != "turn_action":
        return False, "Not in the action phase."
    player = _get_current_player(session)
    if player.id != player_id:
        return False, "It is not your turn."

    space: Space = session.board[player.position]
    if space.space_type not in BUYABLE_TYPES:
        return False, f"{space.name} cannot be purchased."
    if space.owner_id is not None:
        return False, f"{space.name} is already owned."
    if space.price is None:
        return False, f"{space.name} has no listed price."
    if player.cash < space.price:
        return False, f"Not enough cash. Need ${space.price}, have ${player.cash}."

    player.cash -= space.price
    space.owner_id = player_id
    player.properties.append(str(player.position))
    _log(session, f"{player.nickname} bought {space.name} for ${space.price}.")
    return True, ""


def handle_end_turn(session: GameSession, player_id: str) -> tuple[bool, str]:
    """End the current player's turn."""
    if session.status != "started":
        return False, "Game is not in progress."
    if session.phase != "turn_action":
        return False, "Not in the action phase."
    player = _get_current_player(session)
    if player.id != player_id:
        return False, "It is not your turn."

    # If the player rolled doubles and is not in jail, they roll again
    if session.doubles_count > 0 and not player.in_jail:
        session.phase = "turn_roll"
        _log(session, f"{player.nickname} rolled doubles and rolls again.")
        return True, ""

    # Advance to next player
    session.doubles_count = 0
    _advance_turn(session)
    session.phase = "turn_roll"

    if _check_win(session):
        return True, ""

    next_player = _get_current_player(session)
    # If next player is in jail, set phase to jail
    if next_player.in_jail:
        session.phase = "jail"

    _log(session, f"It is now {next_player.nickname}'s turn.")
    return True, ""


def handle_jail_action(
    session: GameSession,
    player_id: str,
    action: Literal["pay", "use_card", "roll"],
) -> tuple[bool, str]:
    """Handle a jail-related action for the current player."""
    player = _get_current_player(session)
    if player.id != player_id:
        return False, "It is not your turn."
    if not player.in_jail and session.phase != "jail":
        return False, "You are not in jail."

    match action:
        case "pay":
            if player.cash < 50:
                return False, "Not enough cash to pay the $50 fine."
            player.cash -= 50
            player.in_jail = False
            player.jail_turns = 0
            session.phase = "turn_roll"
            _log(session, f"{player.nickname} paid $50 to get out of Jail.")

        case "use_card":
            if player.get_out_of_jail_free < 1:
                return False, "You have no Get Out of Jail Free cards."
            player.get_out_of_jail_free -= 1
            player.in_jail = False
            player.jail_turns = 0
            session.phase = "turn_roll"
            _log(session, f"{player.nickname} used a Get Out of Jail Free card.")

        case "roll":
            d1 = random.randint(1, 6)
            d2 = random.randint(1, 6)
            session.dice = (d1, d2)
            _log(session, f"{player.nickname} rolled {d1}+{d2}={d1 + d2} in Jail.")

            if d1 == d2:
                # Doubles — break out of jail, move, no extra turn for doubles
                player.in_jail = False
                player.jail_turns = 0
                session.doubles_count = 0
                old_pos = player.position
                new_pos = (old_pos + d1 + d2) % 40
                if old_pos != 0 and new_pos <= old_pos and (old_pos + d1 + d2) >= 40:
                    player.cash += 200
                    _log(session, f"{player.nickname} passed Go and collected $200.")
                player.position = new_pos
                space: Space = session.board[new_pos]
                session.phase = "turn_action"
                _log(session, f"{player.nickname} rolled doubles and moved to {space.name}.")
                _apply_space(session, player)
            else:
                player.jail_turns += 1
                if player.jail_turns >= 3:
                    # Forced to pay fine and move
                    player.cash -= 50
                    player.in_jail = False
                    player.jail_turns = 0
                    old_pos = player.position
                    new_pos = (old_pos + d1 + d2) % 40
                    if old_pos != 0 and new_pos <= old_pos and (old_pos + d1 + d2) >= 40:
                        player.cash += 200
                        _log(session, f"{player.nickname} passed Go and collected $200.")
                    player.position = new_pos
                    space = session.board[new_pos]
                    session.phase = "turn_action"
                    _log(
                        session,
                        f"{player.nickname} paid $50 fine after 3 jail turns and moved to {space.name}.",
                    )
                    _apply_space(session, player)
                else:
                    # No doubles — end turn, next player
                    session.doubles_count = 0
                    _advance_turn(session)
                    session.phase = "turn_roll"
                    if _check_win(session):
                        return True, ""
                    next_player = _get_current_player(session)
                    if next_player.in_jail:
                        session.phase = "jail"
                    _log(
                        session,
                        f"{player.nickname} stays in Jail (turn {player.jail_turns}/3). "
                        f"It is now {next_player.nickname}'s turn.",
                    )

        case _:
            return False, f"Unknown jail action: {action}"

    return True, ""


async def handle_decline_buy(session: GameSession, player_id: str) -> tuple[bool, str]:
    if session.phase != "turn_action":
        return False, "Not in action phase"
    player = _get_current_player(session)
    if player.id != player_id:
        return False, "Not your turn"
    space = session.board[player.position]
    if space.space_type not in BUYABLE_TYPES:
        return False, "Nothing to auction here"
    if space.owner_id is not None:
        return False, "Property already owned"
    start_auction(session, player.position)
    asyncio.create_task(_auction_timer(session.code, player.position, session.auction.ends_at))
    return True, ""


async def _auction_timer(session_code: str, position: int, ends_at: datetime) -> None:
    import session_manager as sm
    from game_state import resolve_auction
    import websocket_handler as wh
    await asyncio.sleep(10)
    live_session = sm.sessions.get(session_code)
    if (
        live_session
        and live_session.auction
        and live_session.auction.property_position == position
        and live_session.auction.ends_at == ends_at
    ):
        resolve_auction(live_session)
        await wh.broadcast(session_code, {"type": "game_state", "data": live_session.model_dump(mode="json")})


def handle_build_house(session: GameSession, player_id: str, position: int) -> tuple[bool, str]:
    if session.status != "started":
        return False, "Game is not in progress."
    error = can_build_on(session, player_id, position)
    if error:
        return False, error
    space = session.board[position]
    player = session.players[player_id]
    cost = space.house_cost
    if cost is None:
        return False, "Property has no build cost"
    if space.houses == 4:
        # Upgrade to hotel
        if player.cash < cost:
            return False, f"Need ${cost} to build a hotel"
        player.cash -= cost
        space.houses = 0
        space.has_hotel = True
        _log(session, f"{player.nickname} built a hotel on {space.name}")
    else:
        if player.cash < cost:
            return False, f"Need ${cost} to build a house"
        player.cash -= cost
        space.houses += 1
        _log(session, f"{player.nickname} built house #{space.houses} on {space.name}")
    return True, ""


def handle_sell_house(session: GameSession, player_id: str, position: int) -> tuple[bool, str]:
    if session.status != "started":
        return False, "Game is not in progress."
    error = can_sell_from(session, player_id, position)
    if error:
        return False, error
    space = session.board[position]
    player = session.players[player_id]
    cost = space.house_cost
    if cost is None:
        return False, "Property has no build cost"
    if space.has_hotel:
        space.has_hotel = False
        space.houses = 4
        player.cash += cost // 2
        _log(session, f"{player.nickname} sold hotel on {space.name} for ${cost // 2}")
    else:
        space.houses -= 1
        player.cash += cost // 2
        _log(session, f"{player.nickname} sold a house on {space.name} for ${cost // 2}")
    return True, ""


def handle_auction_bid(session: GameSession, player_id: str, bid: int) -> tuple[bool, str]:
    if session.phase != "auction" or not session.auction:
        return False, "No active auction"
    player = session.players.get(player_id)
    if not player or player.is_bankrupt:
        return False, "Invalid player"
    if not isinstance(bid, int) or bid <= session.auction.highest_bid:
        return False, f"Bid must be higher than current highest (${session.auction.highest_bid})"
    if player.cash < bid:
        return False, "Insufficient funds"
    session.auction.bids[player_id] = bid
    session.auction.highest_bid = bid
    session.auction.highest_bidder = player_id
    session.log.append(f"{player.nickname} bid ${bid} in auction")
    return True, ""


def handle_mortgage(session: GameSession, player_id: str, position: int) -> tuple[bool, str]:
    if session.status != "started":
        return False, "Game is not in progress."
    space = session.board[position]
    if space.owner_id != player_id:
        return False, "You don't own this property."
    if space.is_mortgaged:
        return False, "Already mortgaged."
    if space.houses > 0 or space.has_hotel:
        return False, "Must sell all buildings before mortgaging."
    if space.mortgage_value is None:
        return False, "Property has no mortgage value."
    space.is_mortgaged = True
    player = session.players[player_id]
    player.cash += space.mortgage_value
    _log(session, f"{player.nickname} mortgaged {space.name} for ${space.mortgage_value}")
    return True, ""


def handle_unmortgage(session: GameSession, player_id: str, position: int) -> tuple[bool, str]:
    if session.status != "started":
        return False, "Game is not in progress."
    space = session.board[position]
    if space.owner_id != player_id:
        return False, "You don't own this property."
    if not space.is_mortgaged:
        return False, "Not mortgaged."
    if space.mortgage_value is None:
        return False, "Property has no mortgage value."
    cost = int(space.mortgage_value * 1.1)
    player = session.players[player_id]
    if player.cash < cost:
        return False, f"Need ${cost} to unmortgage (mortgage value + 10% interest)."
    player.cash -= cost
    space.is_mortgaged = False
    _log(session, f"{player.nickname} unmortgaged {space.name} for ${cost}")
    return True, ""
