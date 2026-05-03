from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from session_manager import create_game, join_game, start_cleanup_task
from websocket_handler import on_connect, on_disconnect, handle_message

app = FastAPI(title="CHILLOS Monopoly")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateGameRequest(BaseModel):
    max_players: int = Field(default=4, ge=2, le=6)


class JoinGameRequest(BaseModel):
    session_code: str
    nickname: str = Field(min_length=1, max_length=20)


@app.on_event("startup")
async def startup() -> None:
    start_cleanup_task()


@app.post("/api/create_game")
async def api_create_game(body: CreateGameRequest) -> dict:
    session_code: str = create_game(body.max_players)
    return {"session_code": session_code}


@app.post("/api/join_game")
async def api_join_game(body: JoinGameRequest) -> dict:
    success, player_id, error_msg = join_game(body.session_code.upper(), body.nickname.strip())
    if success:
        return {"success": True, "player_id": player_id}
    return {"success": False, "error": error_msg}


@app.websocket("/ws/{session_code}/{player_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_code: str, player_id: str
) -> None:
    await on_connect(session_code, player_id, websocket)
    try:
        while True:
            data: dict = await websocket.receive_json()
            await handle_message(session_code, player_id, data)
    except WebSocketDisconnect:
        await on_disconnect(session_code, player_id)
