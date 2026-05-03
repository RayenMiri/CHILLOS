"""Rent calculation tests for a Monopoly-style game."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from actions import handle_start_game
from game_state import GameSession, calculate_rent
from session_manager import create_game, join_game, sessions


def make_started_session() -> tuple[GameSession, str, str]:
    """Return (session, player1_id, player2_id) with a started 2-player game."""
    code = create_game()
    _, p1_id, _ = join_game(code, "Alice")
    _, p2_id, _ = join_game(code, "Bob")
    session = sessions[code]
    handle_start_game(session, session.host_id)
    return session, p1_id, p2_id


# ---------------------------------------------------------------------------
# 1. Base rent — no monopoly
# ---------------------------------------------------------------------------

def test_base_rent_no_monopoly():
    session, p1_id, p2_id = make_started_session()
    # Bob owns Mediterranean (pos 1); Alice does NOT own Baltic (pos 3).
    session.board[1].owner_id = p2_id
    rent = calculate_rent(session, session.board[1], dice_sum=7)
    assert rent == 2


# ---------------------------------------------------------------------------
# 2. Monopoly doubles base rent (no houses)
# ---------------------------------------------------------------------------

def test_monopoly_doubles_base_rent():
    session, p1_id, p2_id = make_started_session()
    # Alice owns both Brown properties.
    session.board[1].owner_id = p1_id
    session.board[3].owner_id = p1_id
    # Bob lands on pos 1.
    rent = calculate_rent(session, session.board[1], dice_sum=7)
    assert rent == 4  # 2 * base rent[0] = 2 * 2


# ---------------------------------------------------------------------------
# 3. One house rent
# ---------------------------------------------------------------------------

def test_one_house_rent():
    session, p1_id, p2_id = make_started_session()
    session.board[1].owner_id = p1_id
    session.board[3].owner_id = p1_id
    session.board[1].houses = 1
    rent = calculate_rent(session, session.board[1], dice_sum=7)
    assert rent == 10  # rent[1]


# ---------------------------------------------------------------------------
# 4. Four houses rent
# ---------------------------------------------------------------------------

def test_four_houses_rent():
    session, p1_id, p2_id = make_started_session()
    session.board[1].owner_id = p1_id
    session.board[3].owner_id = p1_id
    session.board[1].houses = 4
    rent = calculate_rent(session, session.board[1], dice_sum=7)
    assert rent == 160  # rent[4]


# ---------------------------------------------------------------------------
# 5. Hotel rent
# ---------------------------------------------------------------------------

def test_hotel_rent():
    session, p1_id, p2_id = make_started_session()
    session.board[1].owner_id = p1_id
    session.board[3].owner_id = p1_id
    session.board[1].has_hotel = True
    rent = calculate_rent(session, session.board[1], dice_sum=7)
    assert rent == 250  # rent[5]


# ---------------------------------------------------------------------------
# 6. Railroad — single owned
# ---------------------------------------------------------------------------

def test_railroad_single():
    session, p1_id, p2_id = make_started_session()
    session.board[5].owner_id = p1_id  # Reading Railroad only
    rent = calculate_rent(session, session.board[5], dice_sum=7)
    assert rent == 25


# ---------------------------------------------------------------------------
# 7. Railroad — two owned
# ---------------------------------------------------------------------------

def test_railroad_two():
    session, p1_id, p2_id = make_started_session()
    session.board[5].owner_id = p1_id   # Reading Railroad
    session.board[15].owner_id = p1_id  # Pennsylvania Railroad
    rent = calculate_rent(session, session.board[5], dice_sum=7)
    assert rent == 50


# ---------------------------------------------------------------------------
# 8. Railroad — all four owned
# ---------------------------------------------------------------------------

def test_railroad_four():
    session, p1_id, p2_id = make_started_session()
    for pos in (5, 15, 25, 35):
        session.board[pos].owner_id = p1_id
    rent = calculate_rent(session, session.board[5], dice_sum=7)
    assert rent == 200


# ---------------------------------------------------------------------------
# 9. Railroad — mortgaged
# ---------------------------------------------------------------------------

def test_railroad_mortgaged():
    session, p1_id, p2_id = make_started_session()
    session.board[5].owner_id = p1_id
    session.board[5].is_mortgaged = True
    rent = calculate_rent(session, session.board[5], dice_sum=7)
    assert rent == 0


# ---------------------------------------------------------------------------
# 10. Utility — single owned
# ---------------------------------------------------------------------------

def test_utility_single():
    session, p1_id, p2_id = make_started_session()
    session.board[12].owner_id = p1_id  # Electric Company only
    rent = calculate_rent(session, session.board[12], dice_sum=7)
    assert rent == 28  # 4 * 7


# ---------------------------------------------------------------------------
# 11. Utility — both owned
# ---------------------------------------------------------------------------

def test_utility_both():
    session, p1_id, p2_id = make_started_session()
    session.board[12].owner_id = p1_id  # Electric Company
    session.board[28].owner_id = p1_id  # Water Works
    rent = calculate_rent(session, session.board[12], dice_sum=7)
    assert rent == 70  # 10 * 7


# ---------------------------------------------------------------------------
# 12. Mortgaged property — no rent
# ---------------------------------------------------------------------------

def test_mortgaged_property_no_rent():
    session, p1_id, p2_id = make_started_session()
    session.board[1].owner_id = p1_id
    session.board[1].is_mortgaged = True
    rent = calculate_rent(session, session.board[1], dice_sum=7)
    assert rent == 0
