"""Tests for dice-doubles mechanics and jail interactions."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from actions import (
    _get_current_player,
    handle_end_turn,
    handle_jail_action,
    handle_roll_dice,
    handle_start_game,
)
from game_state import GameSession
from session_manager import create_game, join_game, sessions


def make_started_session() -> tuple[GameSession, str, str]:
    """Return (session, alice_id, bob_id) with a started 2-player game."""
    code = create_game()
    ok1, alice_id, _ = join_game(code, "Alice")
    ok2, bob_id, _ = join_game(code, "Bob")
    assert ok1 and ok2

    session = sessions[code]
    # Alice is host (first to join)
    ok, _ = handle_start_game(session, alice_id)
    assert ok

    # Force Alice to go first
    session.current_player_index = 0

    return session, alice_id, bob_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_doubles_grants_extra_turn() -> None:
    session, alice_id, _ = make_started_session()

    session.dice = (3, 3)
    session.doubles_count = 1
    session.phase = "turn_action"

    ok, err = handle_end_turn(session, alice_id)
    assert ok, err
    assert session.phase == "turn_roll"
    assert session.current_player_index == 0


def test_no_doubles_advances_turn() -> None:
    session, alice_id, _ = make_started_session()

    session.doubles_count = 0
    session.phase = "turn_action"

    ok, err = handle_end_turn(session, alice_id)
    assert ok, err
    assert session.current_player_index == 1
    assert session.phase == "turn_roll"


def test_three_doubles_sends_to_jail() -> None:
    session, alice_id, _ = make_started_session()

    session.phase = "turn_roll"
    session.doubles_count = 2

    with patch("actions.random.randint", return_value=3):
        ok, err = handle_roll_dice(session, alice_id)

    assert ok, err
    alice = _get_current_player(session)
    assert alice.position == 10
    assert alice.in_jail is True
    assert session.doubles_count == 0


def test_jail_doubles_escape() -> None:
    session, alice_id, _ = make_started_session()

    alice = _get_current_player(session)
    alice.in_jail = True
    alice.position = 10
    alice.jail_turns = 0
    session.phase = "jail"

    with patch("actions.random.randint", return_value=4):
        ok, err = handle_jail_action(session, alice_id, "roll")

    assert ok, err
    assert alice.in_jail is False
    assert alice.position != 10
    assert alice.jail_turns == 0


def test_jail_no_doubles_increments_turns() -> None:
    session, alice_id, _ = make_started_session()

    alice = _get_current_player(session)
    alice.in_jail = True
    alice.position = 10
    alice.jail_turns = 0
    session.phase = "jail"

    with patch("actions.random.randint", side_effect=[1, 2, 1, 2]):
        ok, err = handle_jail_action(session, alice_id, "roll")

    assert ok, err
    assert alice.jail_turns == 1
    assert alice.in_jail is True


def test_jail_third_turn_forced_exit() -> None:
    session, alice_id, _ = make_started_session()

    alice = _get_current_player(session)
    alice.in_jail = True
    alice.position = 10
    alice.jail_turns = 2
    session.phase = "jail"

    initial_cash = alice.cash

    with patch("actions.random.randint", side_effect=[1, 2, 1, 2]):
        ok, err = handle_jail_action(session, alice_id, "roll")

    assert ok, err
    assert alice.in_jail is False
    assert alice.cash == initial_cash - 50
    assert alice.position != 10
