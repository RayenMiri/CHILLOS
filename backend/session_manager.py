"""Session manager for in-memory Monopoly-style game sessions."""

import asyncio
import random
import string
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import WebSocket

from game_state import GameSession
from player import Player

PLAYER_COLORS: list[str] = ["red", "blue", "green", "yellow", "purple", "orange"]

sessions: dict[str, GameSession] = {}
connections: dict[str, dict[str, WebSocket]] = {}


def generate_code() -> str:
    """Return a unique 6-char uppercase alphanumeric session code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=6))
        if code not in sessions:
            return code


def create_game(max_players: int = 4) -> str:
    """Create a new empty session and return its code."""
    code = generate_code()
    session = GameSession(
        code=code,
        host_id="",
        players={},
        max_players=max_players,
        status="waiting",
        created_at=datetime.utcnow(),
    )
    sessions[code] = session
    connections[code] = {}
    return code


def join_game(session_code: str, nickname: str) -> tuple[bool, str, str]:
    """Add a player to an existing session.

    Returns:
        (True, player_id, "") on success.
        (False, "", error_message) on failure.
    """
    session = sessions.get(session_code)
    if session is None:
        return False, "", "Session not found."
    if session.status != "waiting":
        return False, "", "Game already started."
    if len(session.players) >= session.max_players:
        return False, "", "Session is full."
    if any(p.nickname == nickname for p in session.players.values()):
        return False, "", "Nickname already taken."

    color_index = len(session.players) % len(PLAYER_COLORS)
    color = PLAYER_COLORS[color_index]

    player_id = str(uuid4())
    player = Player(
        id=player_id,
        nickname=nickname,
        color=color,
        last_seen=datetime.utcnow(),
    )

    session.players[player_id] = player

    if session.host_id == "":
        session.host_id = player_id

    return True, player_id, ""


def get_session(session_code: str) -> GameSession | None:
    """Return the session for the given code, or None."""
    return sessions.get(session_code)


def get_player(session_code: str, player_id: str) -> Player | None:
    """Return the player within a session, or None."""
    session = sessions.get(session_code)
    if session is None:
        return None
    return session.players.get(player_id)


def remove_player(session_code: str, player_id: str) -> None:
    """Mark a player inactive; delete session if all players are inactive."""
    session = sessions.get(session_code)
    if session is None:
        return
    player = session.players.get(player_id)
    if player is None:
        return

    player.is_active = False
    player.last_seen = datetime.utcnow()

    if all(not p.is_active for p in session.players.values()):
        del sessions[session_code]
        connections.pop(session_code, None)


def start_cleanup_task() -> None:
    """Schedule the background cleanup loop as an asyncio task."""
    asyncio.create_task(_cleanup_loop())


async def _cleanup_loop() -> None:
    """Run cleanup indefinitely every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        await _do_cleanup()


async def _do_cleanup() -> None:
    """Delete stale or finished sessions."""
    now = datetime.utcnow()
    cutoff = timedelta(minutes=2)
    to_delete: list[str] = []

    for code, session in sessions.items():
        active_conns = connections.get(code, {})

        # All players inactive and last_seen > 2 minutes ago
        if session.players and all(not p.is_active for p in session.players.values()):
            oldest_seen = max(p.last_seen for p in session.players.values())
            if now - oldest_seen > cutoff:
                to_delete.append(code)
                continue

        # Game over with no active connections
        if session.status == "game_over" and not active_conns:
            to_delete.append(code)

    for code in to_delete:
        sessions.pop(code, None)
        connections.pop(code, None)
