from datetime import datetime
from fastapi import WebSocket
from session_manager import sessions, connections, get_session, get_player, remove_player
from actions import (
    handle_start_game,
    handle_roll_dice,
    handle_buy_property,
    handle_end_turn,
    handle_jail_action,
    handle_decline_buy,
    handle_auction_bid,
)


async def broadcast(session_code: str, message: dict) -> None:
    if session_code not in connections:
        return
    snapshot = list(connections[session_code].items())
    for player_id, ws in snapshot:
        try:
            await ws.send_json(message)
        except Exception:
            remove_player(session_code, player_id)
            connections[session_code].pop(player_id, None)


async def send_error(session_code: str, player_id: str, message: str) -> None:
    if session_code not in connections:
        return
    ws: WebSocket | None = connections[session_code].get(player_id)
    if ws is None:
        return
    try:
        await ws.send_json({"type": "error", "message": message})
    except Exception:
        pass


async def handle_message(session_code: str, player_id: str, data: dict) -> None:
    session = get_session(session_code)
    if session is None:
        await send_error(session_code, player_id, "Session not found.")
        return

    msg_type: str = data.get("type", "")

    try:
        if msg_type == "start_game":
            ok, err = handle_start_game(session, player_id)
        elif msg_type == "roll_dice":
            ok, err = handle_roll_dice(session, player_id)
        elif msg_type == "buy_property":
            ok, err = handle_buy_property(session, player_id)
        elif msg_type == "end_turn":
            ok, err = handle_end_turn(session, player_id)
        elif msg_type == "use_jail_card":
            ok, err = handle_jail_action(session, player_id, "use_card")
        elif msg_type == "pay_jail_fine":
            ok, err = handle_jail_action(session, player_id, "pay")
        elif msg_type == "jail_roll":
            ok, err = handle_jail_action(session, player_id, "roll")
        elif msg_type == "decline_buy":
            ok, err = handle_decline_buy(session, player_id)
        elif msg_type == "auction_bid":
            bid = data.get("bid", 0)
            ok, err = handle_auction_bid(session, player_id, bid)
        elif msg_type == "chat":
            player = get_player(session_code, player_id)
            if player is None:
                await send_error(session_code, player_id, "Player not found.")
                return
            await broadcast(
                session_code,
                {
                    "type": "chat",
                    "nickname": player.nickname,
                    "message": data.get("message", ""),
                },
            )
            return
        else:
            await send_error(session_code, player_id, f"Unknown message type: {msg_type!r}")
            return

    except Exception as exc:
        await send_error(session_code, player_id, f"Internal error: {exc}")
        return

    if not ok:
        await send_error(session_code, player_id, err)
        return

    await broadcast(session_code, {"type": "game_state", "data": session.model_dump()})


async def on_connect(session_code: str, player_id: str, websocket: WebSocket) -> None:
    await websocket.accept()

    if session_code not in connections:
        connections[session_code] = {}
    connections[session_code][player_id] = websocket

    player = get_player(session_code, player_id)
    if player is not None:
        player.is_active = True
        player.last_seen = datetime.utcnow()

    nickname: str = player.nickname if player is not None else player_id
    await broadcast(session_code, {"type": "player_joined", "nickname": nickname})

    session = get_session(session_code)
    if session is not None:
        try:
            await websocket.send_json({"type": "game_state", "data": session.model_dump()})
        except Exception:
            pass


async def on_disconnect(session_code: str, player_id: str) -> None:
    player = get_player(session_code, player_id)
    nickname: str = player.nickname if player is not None else player_id

    if session_code in connections:
        connections[session_code].pop(player_id, None)

    remove_player(session_code, player_id)

    await broadcast(session_code, {"type": "player_left", "nickname": nickname})
