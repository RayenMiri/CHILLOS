"""Bankruptcy resolution and win condition tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from actions import handle_start_game
from game_state import GameSession, resolve_bankruptcy, check_win_condition
from session_manager import create_game, join_game, sessions


def make_started_session() -> tuple[GameSession, str, str]:
    """Return (session, player1_id, player2_id) with a started 2-player game."""
    code = create_game()
    _, p1_id, _ = join_game(code, "Alice")
    _, p2_id, _ = join_game(code, "Bob")
    session = sessions[code]
    handle_start_game(session, session.host_id)
    return session, p1_id, p2_id


def test_bankrupt_player_marked_bankrupt():
    session, p1, p2 = make_started_session()
    resolve_bankruptcy(session, p1, p2)
    assert session.players[p1].is_bankrupt is True


def test_property_transfers_to_creditor():
    session, p1, p2 = make_started_session()
    session.board[1].owner_id = p1
    session.players[p1].properties = ["1"]
    resolve_bankruptcy(session, p1, p2)
    assert session.board[1].owner_id == p2
    assert "1" in session.players[p2].properties


def test_property_to_bank_on_no_creditor():
    session, p1, p2 = make_started_session()
    session.board[1].owner_id = p1
    session.board[1].houses = 2
    session.players[p1].properties = ["1"]
    resolve_bankruptcy(session, p1, None)
    assert session.board[1].owner_id is None
    assert session.board[1].houses == 0


def test_mortgaged_property_transfers_as_is():
    session, p1, p2 = make_started_session()
    session.board[1].owner_id = p1
    session.board[1].is_mortgaged = True
    session.players[p1].properties = ["1"]
    resolve_bankruptcy(session, p1, p2)
    assert session.board[1].owner_id == p2
    assert session.board[1].is_mortgaged is True


def test_remaining_cash_goes_to_creditor():
    session, p1, p2 = make_started_session()
    session.players[p1].cash = 100
    session.players[p2].cash = 500
    resolve_bankruptcy(session, p1, p2)
    assert session.players[p2].cash == 600
    assert session.players[p1].cash == 0


def test_win_condition_triggers_on_one_player():
    session, p1, p2 = make_started_session()
    session.players[p1].is_bankrupt = True
    winner_id = check_win_condition(session)
    assert winner_id == p2
    assert session.status == "game_over"


def test_no_win_with_two_active_players():
    session, p1, p2 = make_started_session()
    winner_id = check_win_condition(session)
    assert winner_id is None
    assert session.status != "game_over"
