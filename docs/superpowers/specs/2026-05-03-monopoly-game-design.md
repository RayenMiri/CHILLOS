# Monopoly Web Game — Design Spec
**Date:** 2026-05-03  
**Project:** CHILLOS  
**Status:** Approved

---

## Overview

A fully functional real-time multiplayer Monopoly-style board game as a web application. No database, no auth, no persistence — all state lives in server memory. Sessions are ephemeral and disposable.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.10+), asyncio, WebSockets, Pydantic |
| Frontend | React + TypeScript, Tailwind CSS, Zustand, Vite |
| State | In-memory Python dicts only |
| Containerization | Docker + docker-compose (two containers) |

---

## Architecture

### Container Layout

```
CHILLOS/
├── backend/
│   ├── main.py
│   ├── session_manager.py
│   ├── game_state.py
│   ├── board.py
│   ├── cards.py
│   ├── player.py
│   ├── actions.py
│   ├── websocket_handler.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       ├── test_rent.py
│       ├── test_bankruptcy.py
│       └── test_doubles.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Lobby.tsx
│   │   │   ├── Board.tsx
│   │   │   ├── Space.tsx
│   │   │   ├── PlayerToken.tsx
│   │   │   ├── PlayerPanel.tsx
│   │   │   ├── TurnControls.tsx
│   │   │   ├── TradeModal.tsx
│   │   │   ├── AuctionModal.tsx
│   │   │   ├── ChatLog.tsx
│   │   │   └── GameOver.tsx
│   │   ├── hooks/
│   │   │   └── useGameWebSocket.ts
│   │   ├── store/
│   │   │   └── gameStore.ts
│   │   ├── types/
│   │   │   └── game.ts
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── docker-compose.dev.yml
```

### Two-Container Docker Setup

**Production (`docker-compose.yml`)**
- `backend`: uvicorn on port 8000 (internal only)
- `frontend`: Nginx on port 80, proxies `/api/` and `/ws/` to `backend:8000`
- Frontend is a static Vite build artifact served by Nginx

**Development (`docker-compose.dev.yml` override)**
- `backend`: volume-mounted `./backend`, runs `uvicorn --reload`
- `frontend`: runs `vite dev` on port 5173, proxies via `vite.config.ts`
- Run: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`

---

## Backend Design

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `board.py` | Constant `BOARD` list (40 spaces) + `PROPERTY_DATA` dict. Never mutated. |
| `player.py` | `Player` Pydantic model, bankruptcy logic, jail state |
| `session_manager.py` | Global `dict[str, GameSession]`, create/join/leave, 30s cleanup sweep via `asyncio.create_task` at startup |
| `game_state.py` | State machine with explicit phase field. Transitions are pure functions returning mutated session + log entries. |
| `actions.py` | One handler per client action. All validation here. Returns `(success, error_msg)`. |
| `websocket_handler.py` | Routes messages to `actions.py`, broadcasts full `game_state` to all connections. |
| `cards.py` | Chance + Community Chest decks, shuffled at game start, used cards go to bottom. |
| `main.py` | FastAPI app, HTTP endpoints, WebSocket endpoint, startup task registration. |

### State Machine

```
waiting_for_players
  -> started (host starts, min 2 players)
  -> turn_roll (current player rolls)
  -> turn_action (post-roll, movement resolved)
  -> jail (3 doubles or Go To Jail)
  -> auction (declined buy or no buyer)
  -> trading (trade proposed)
  -> game_over (1 player remains)
```

`GameSession.status` retains its three top-level values: `"waiting" | "started" | "game_over"`. A separate `GameSession.phase` field (`str`) tracks the active turn sub-state: `"turn_roll" | "turn_action" | "auction" | "trading" | "jail"`. Only meaningful when `status == "started"`.

### Session & Reconnection

- Disconnect → `is_active = False`, 2-min timer starts
- Reconnect with same `player_id` + `session_code` within 2 min → restore, mark active
- After 2 min → remove player, assets to bank
- All players gone → delete session immediately
- Cleanup sweep: every 30s via background task

### Auction Timer

`asyncio.create_task(asyncio.sleep(10))` started on auction creation. Task is cancelled if resolved early. On expiry, highest bidder wins; no bids = property stays unowned.

### Key Business Rules

- **Rent with monopoly, no buildings**: double base rent (index 0 of rent array)
- **Railroads**: `$25 * count_owned` (mortgaged ones excluded)
- **Utilities**: 4x dice sum if one owned, 10x if both owned
- **Even building**: no property in group can differ by more than 1 house
- **Bankruptcy to creditor**: properties transfer as-is (mortgaged status preserved)
- **Bankruptcy to bank**: properties become unowned

### API Endpoints

```
POST /api/create_game   body: { max_players?: 2-6 }  → { session_code, player_id }
POST /api/join_game     body: { session_code, nickname } → { success, player_id?, error? }
WS   /ws/{session_code}/{player_id}
```

---

## Frontend Design

### State Management (Zustand)

Single store (`gameStore.ts`) holds the full `GameSession` snapshot received from the server. Updated atomically on every `game_state` WebSocket message. Components subscribe to slices — no prop drilling.

### WebSocket Hook (`useGameWebSocket.ts`)

- Owns WebSocket lifecycle: connect, message dispatch, close handling
- Persists `sessionCode` + `playerId` in `localStorage`
- Exponential backoff reconnect: 1s → 2s → 4s → cap at 5s
- Shows "Reconnecting..." overlay while attempting
- On reconnect, sends to same `/ws/{code}/{id}` — server restores state

### Board Layout

CSS Grid 11×11. Corners at grid corners, spaces fill edges. Player tokens absolutely positioned over spaces using a `position (0-39) → grid cell` mapping function. Each space shows: name, color bar, price, owner dot, house/hotel icons, player tokens.

### Component Responsibilities

| Component | Sends WS messages? | Notes |
|-----------|-------------------|-------|
| `TurnControls` | Yes — all turn actions | Roll, buy, auction choice, end turn, jail options |
| `TradeModal` | Yes — propose/respond | Opens from PlayerPanel |
| `AuctionModal` | Yes — bid | Countdown synced to server `ends_at`, not client clock |
| `PlayerPanel` | No | Build/mortgage/sell via TurnControls |
| `Board`, `Space`, `PlayerToken` | No | Pure display |
| `ChatLog` | Yes — chat messages only | |
| `GameOver` | No | Winner display |

### Auction Modal

Local countdown timer derived from `ends_at` (server timestamp). Prevents client clock drift from affecting bid window. Auto-closes on `auction_end` message.

---

## Implementation Phases

### Phase 1 — Backend Core
Sessions, board data, player model, dice/movement, property buying, rent calculation, basic WebSocket broadcast.

### Phase 2 — Backend Advanced
Auctions (with 10s timer), Chance/Community Chest cards, jail mechanics, houses/hotels/mortgage, trading, bankruptcy, win condition.

### Phase 3 — Frontend Shell
Lobby (create/join), WebSocket hook + store, board rendering with CSS grid, player tokens, turn controls (roll, buy, end turn).

### Phase 4 — Frontend Complete
PlayerPanel with build/mortgage controls, AuctionModal, TradeModal, ChatLog, GameOver screen, reconnection overlay, polish.

---

## Testing

`backend/tests/` — pytest + pytest-asyncio, run inside backend container.

| File | Covers |
|------|--------|
| `test_rent.py` | Base rent, monopoly double, railroad scaling, utility multipliers, mortgaged no-rent |
| `test_bankruptcy.py` | Asset transfer to creditor, asset transfer to bank, player elimination, win condition trigger |
| `test_doubles.py` | Double roll again, three doubles → jail, jail doubles escape |

---

## Dependencies

**Backend (`requirements.txt`)**
```
fastapi
uvicorn[standard]
pydantic
pytest
pytest-asyncio
```

**Frontend (`package.json` key deps)**
```
react, react-dom, typescript, vite, tailwindcss, zustand
```
