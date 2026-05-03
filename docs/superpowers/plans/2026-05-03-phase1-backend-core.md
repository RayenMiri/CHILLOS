# Phase 1 — Backend Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend with sessions, board data, dice rolling, movement, property buying, and rent calculation — fully testable via WebSocket.

**Architecture:** Single FastAPI process, in-memory state only. WebSocket per player, full `game_state` broadcast on every mutation. Seven backend modules with clear ownership boundaries.

**Tech Stack:** Python 3.11, FastAPI 0.115, Pydantic v2, uvicorn, pytest, pytest-asyncio 0.23

---

## File Map

| File | Responsibility |
|------|---------------|
| `backend/board.py` | `Space` model + `BOARD_TEMPLATE` (40 spaces) + `build_board()` + `COLOR_GROUPS` |
| `backend/player.py` | `Player` Pydantic model + `PLAYER_COLORS` |
| `backend/cards.py` | `Card` model + `CHANCE_CARDS` + `COMMUNITY_CARDS` + `build_chance_deck()` + `build_community_deck()` |
| `backend/game_state.py` | `GameSession`, `AuctionState`, `TradeOffer` models + `init_session()` + `calculate_rent()` helpers |
| `backend/session_manager.py` | `sessions` dict + `connections` dict + CRUD + `cleanup_loop()` |
| `backend/actions.py` | `handle_action()` router + `handle_roll_dice()` + `handle_buy_property()` + `handle_end_turn()` + `handle_start_game()` |
| `backend/websocket_handler.py` | `broadcast_state()` + `handle_message()` |
| `backend/main.py` | FastAPI app + `POST /api/create_game` + `POST /api/join_game` + `WS /ws/{code}/{pid}` |
| `backend/requirements.txt` | Python dependencies |
| `backend/pytest.ini` | asyncio_mode = auto |
| `backend/Dockerfile` | Backend container |
| `frontend/Dockerfile` | Frontend container placeholder (fleshed out in Phase 3) |
| `frontend/nginx.conf` | Nginx reverse proxy config (used by frontend Dockerfile) |
| `docker-compose.yml` | Production two-container setup |
| `docker-compose.dev.yml` | Dev override with hot reload + volume mounts |
| `backend/tests/__init__.py` | Empty — marks tests as package |
| `backend/tests/conftest.py` | `make_session()` fixture |
| `backend/tests/test_rent.py` | Rent calculation tests |
| `backend/tests/test_doubles.py` | Doubles and jail roll tests |

---

### Task 1: Requirements, Dockerfiles, and Compose

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
pytest==8.2.0
pytest-asyncio==0.23.0
httpx==0.27.0
```

- [ ] **Step 2: Create `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 5: Create `frontend/Dockerfile` (placeholder — Phase 3 fills this out)**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 6: Create `docker-compose.yml`**

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    expose:
      - "8000"
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

- [ ] **Step 7: Create `docker-compose.dev.yml`**

```yaml
version: "3.9"
services:
  backend:
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    expose: []

  frontend:
    image: node:20-alpine
    build: {}
    entrypoint: []
    working_dir: /app
    command: sh -c "npm install && npm run dev -- --host"
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
```

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini backend/Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml docker-compose.dev.yml
git commit -m "chore: add docker setup and requirements"
```

---

### Task 2: Board Data (board.py)

**Files:**
- Create: `backend/board.py`

- [ ] **Step 1: Create `backend/board.py`**

```python
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class Space(BaseModel):
    id: str
    position: int
    name: str
    space_type: str  # "go"|"property"|"railroad"|"utility"|"tax"|"chance"|"community_chest"|"jail"|"free_parking"|"go_to_jail"
    group: Optional[str] = None
    price: int = 0
    rent: list[int] = []
    house_cost: int = 0
    hotel_cost: int = 0
    mortgage_value: int = 0
    tax_amount: int = 0
    owner_id: Optional[str] = None
    houses: int = 0
    has_hotel: bool = False
    is_mortgaged: bool = False


BOARD_TEMPLATE: list[Space] = [
    Space(id="go", position=0, name="Go", space_type="go"),
    Space(id="mediterranean_ave", position=1, name="Mediterranean Avenue", space_type="property",
          group="Brown", price=60, rent=[2, 10, 30, 90, 160, 250], house_cost=50, hotel_cost=50, mortgage_value=30),
    Space(id="community_chest_1", position=2, name="Community Chest", space_type="community_chest"),
    Space(id="baltic_ave", position=3, name="Baltic Avenue", space_type="property",
          group="Brown", price=60, rent=[2, 10, 30, 90, 160, 250], house_cost=50, hotel_cost=50, mortgage_value=30),
    Space(id="income_tax", position=4, name="Income Tax", space_type="tax", tax_amount=200),
    Space(id="reading_railroad", position=5, name="Reading Railroad", space_type="railroad",
          group="Railroad", price=200, rent=[25, 50, 100, 200], mortgage_value=100),
    Space(id="oriental_ave", position=6, name="Oriental Avenue", space_type="property",
          group="Light Blue", price=100, rent=[6, 30, 90, 270, 400, 550], house_cost=50, hotel_cost=50, mortgage_value=50),
    Space(id="chance_1", position=7, name="Chance", space_type="chance"),
    Space(id="vermont_ave", position=8, name="Vermont Avenue", space_type="property",
          group="Light Blue", price=100, rent=[6, 30, 90, 270, 400, 550], house_cost=50, hotel_cost=50, mortgage_value=50),
    Space(id="connecticut_ave", position=9, name="Connecticut Avenue", space_type="property",
          group="Light Blue", price=120, rent=[6, 30, 90, 270, 400, 550], house_cost=50, hotel_cost=50, mortgage_value=60),
    Space(id="jail", position=10, name="Jail / Just Visiting", space_type="jail"),
    Space(id="st_charles_place", position=11, name="St. Charles Place", space_type="property",
          group="Pink", price=140, rent=[10, 50, 150, 450, 625, 750], house_cost=100, hotel_cost=100, mortgage_value=70),
    Space(id="electric_company", position=12, name="Electric Company", space_type="utility",
          group="Utility", price=150, rent=[], mortgage_value=75),
    Space(id="states_ave", position=13, name="States Avenue", space_type="property",
          group="Pink", price=140, rent=[10, 50, 150, 450, 625, 750], house_cost=100, hotel_cost=100, mortgage_value=70),
    Space(id="virginia_ave", position=14, name="Virginia Avenue", space_type="property",
          group="Pink", price=160, rent=[10, 50, 150, 450, 625, 750], house_cost=100, hotel_cost=100, mortgage_value=80),
    Space(id="pennsylvania_railroad", position=15, name="Pennsylvania Railroad", space_type="railroad",
          group="Railroad", price=200, rent=[25, 50, 100, 200], mortgage_value=100),
    Space(id="st_james_place", position=16, name="St. James Place", space_type="property",
          group="Orange", price=180, rent=[14, 70, 200, 550, 750, 950], house_cost=100, hotel_cost=100, mortgage_value=90),
    Space(id="community_chest_2", position=17, name="Community Chest", space_type="community_chest"),
    Space(id="tennessee_ave", position=18, name="Tennessee Avenue", space_type="property",
          group="Orange", price=180, rent=[14, 70, 200, 550, 750, 950], house_cost=100, hotel_cost=100, mortgage_value=90),
    Space(id="new_york_ave", position=19, name="New York Avenue", space_type="property",
          group="Orange", price=200, rent=[14, 70, 200, 550, 750, 950], house_cost=100, hotel_cost=100, mortgage_value=100),
    Space(id="free_parking", position=20, name="Free Parking", space_type="free_parking"),
    Space(id="kentucky_ave", position=21, name="Kentucky Avenue", space_type="property",
          group="Red", price=220, rent=[18, 90, 250, 700, 875, 1050], house_cost=150, hotel_cost=150, mortgage_value=110),
    Space(id="chance_2", position=22, name="Chance", space_type="chance"),
    Space(id="indiana_ave", position=23, name="Indiana Avenue", space_type="property",
          group="Red", price=220, rent=[18, 90, 250, 700, 875, 1050], house_cost=150, hotel_cost=150, mortgage_value=110),
    Space(id="illinois_ave", position=24, name="Illinois Avenue", space_type="property",
          group="Red", price=240, rent=[18, 90, 250, 700, 875, 1050], house_cost=150, hotel_cost=150, mortgage_value=120),
    Space(id="bo_railroad", position=25, name="B&O Railroad", space_type="railroad",
          group="Railroad", price=200, rent=[25, 50, 100, 200], mortgage_value=100),
    Space(id="atlantic_ave", position=26, name="Atlantic Avenue", space_type="property",
          group="Yellow", price=260, rent=[22, 110, 330, 800, 975, 1150], house_cost=150, hotel_cost=150, mortgage_value=130),
    Space(id="ventnor_ave", position=27, name="Ventnor Avenue", space_type="property",
          group="Yellow", price=260, rent=[22, 110, 330, 800, 975, 1150], house_cost=150, hotel_cost=150, mortgage_value=130),
    Space(id="water_works", position=28, name="Water Works", space_type="utility",
          group="Utility", price=150, rent=[], mortgage_value=75),
    Space(id="marvin_gardens", position=29, name="Marvin Gardens", space_type="property",
          group="Yellow", price=280, rent=[22, 110, 330, 800, 975, 1150], house_cost=150, hotel_cost=150, mortgage_value=140),
    Space(id="go_to_jail", position=30, name="Go To Jail", space_type="go_to_jail"),
    Space(id="pacific_ave", position=31, name="Pacific Avenue", space_type="property",
          group="Green", price=300, rent=[26, 130, 390, 900, 1100, 1275], house_cost=200, hotel_cost=200, mortgage_value=150),
    Space(id="north_carolina_ave", position=32, name="North Carolina Avenue", space_type="property",
          group="Green", price=300, rent=[26, 130, 390, 900, 1100, 1275], house_cost=200, hotel_cost=200, mortgage_value=150),
    Space(id="community_chest_3", position=33, name="Community Chest", space_type="community_chest"),
    Space(id="pennsylvania_ave", position=34, name="Pennsylvania Avenue", space_type="property",
          group="Green", price=320, rent=[26, 130, 390, 900, 1100, 1275], house_cost=200, hotel_cost=200, mortgage_value=160),
    Space(id="short_line", position=35, name="Short Line", space_type="railroad",
          group="Railroad", price=200, rent=[25, 50, 100, 200], mortgage_value=100),
    Space(id="chance_3", position=36, name="Chance", space_type="chance"),
    Space(id="park_place", position=37, name="Park Place", space_type="property",
          group="Dark Blue", price=350, rent=[35, 175, 500, 1100, 1300, 1500], house_cost=200, hotel_cost=200, mortgage_value=175),
    Space(id="luxury_tax", position=38, name="Luxury Tax", space_type="tax", tax_amount=100),
    Space(id="boardwalk", position=39, name="Boardwalk", space_type="property",
          group="Dark Blue", price=400, rent=[35, 175, 500, 1100, 1300, 1500], house_cost=200, hotel_cost=200, mortgage_value=200),
]

COLOR_GROUPS: dict[str, list[str]] = {
    "Brown": ["mediterranean_ave", "baltic_ave"],
    "Light Blue": ["oriental_ave", "vermont_ave", "connecticut_ave"],
    "Pink": ["st_charles_place", "states_ave", "virginia_ave"],
    "Orange": ["st_james_place", "tennessee_ave", "new_york_ave"],
    "Red": ["kentucky_ave", "indiana_ave", "illinois_ave"],
    "Yellow": ["atlantic_ave", "ventnor_ave", "marvin_gardens"],
    "Green": ["pacific_ave", "north_carolina_ave", "pennsylvania_ave"],
    "Dark Blue": ["park_place", "boardwalk"],
    "Railroad": ["reading_railroad", "pennsylvania_railroad", "bo_railroad", "short_line"],
    "Utility": ["electric_company", "water_works"],
}


def build_board() -> list[Space]:
    return [s.model_copy(deep=True) for s in BOARD_TEMPLATE]
```

- [ ] **Step 2: Verify 40 spaces**

Run from `backend/`:
```bash
python -c "from board import BOARD_TEMPLATE; assert len(BOARD_TEMPLATE) == 40, len(BOARD_TEMPLATE); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/board.py
git commit -m "feat: add 40-space board data"
```

---

### Task 3: Player Model (player.py)

**Files:**
- Create: `backend/player.py`

- [ ] **Step 1: Create `backend/player.py`**

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime, timezone

PLAYER_COLORS = ["red", "blue", "green", "yellow", "purple", "orange"]


class Player(BaseModel):
    id: str
    nickname: str
    color: str
    cash: int = 1500
    position: int = 0
    properties: list[str] = Field(default_factory=list)
    get_out_of_jail_free: int = 0
    in_jail: bool = False
    jail_turns: int = 0
    is_active: bool = True
    is_bankrupt: bool = False
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Commit**

```bash
git add backend/player.py
git commit -m "feat: add Player model"
```

---

### Task 4: Card Decks (cards.py)

**Files:**
- Create: `backend/cards.py`

- [ ] **Step 1: Create `backend/cards.py`**

```python
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
import random


class Card(BaseModel):
    id: str
    deck: str  # "chance" | "community"
    description: str
    action: str
    amount: int = 0
    destination: Optional[int] = None


CHANCE_CARDS: list[Card] = [
    Card(id="ch_advance_go", deck="chance", description="Advance to Go (Collect $200)", action="advance_to", destination=0),
    Card(id="ch_advance_illinois", deck="chance", description="Advance to Illinois Ave.", action="advance_to", destination=24),
    Card(id="ch_advance_st_charles", deck="chance", description="Advance to St. Charles Place", action="advance_to", destination=11),
    Card(id="ch_advance_nearest_utility", deck="chance", description="Advance to nearest Utility. If unowned, buy or auction. If owned pay 10x dice.", action="advance_nearest_utility"),
    Card(id="ch_advance_nearest_railroad", deck="chance", description="Advance to nearest Railroad. If unowned, buy or auction. If owned pay 2x rent.", action="advance_nearest_railroad"),
    Card(id="ch_bank_pays_50", deck="chance", description="Bank pays you dividend of $50.", action="collect", amount=50),
    Card(id="ch_get_out_of_jail", deck="chance", description="Get Out of Jail Free.", action="get_out_of_jail_free"),
    Card(id="ch_go_back_3", deck="chance", description="Go Back 3 Spaces.", action="go_back_3"),
    Card(id="ch_go_to_jail", deck="chance", description="Go to Jail.", action="go_to_jail"),
    Card(id="ch_repairs", deck="chance", description="Make general repairs: $25/house, $100/hotel.", action="repairs_chance"),
    Card(id="ch_poor_tax", deck="chance", description="Pay poor tax of $15.", action="pay", amount=15),
    Card(id="ch_reading_railroad", deck="chance", description="Take a trip to Reading Railroad.", action="advance_to", destination=5),
    Card(id="ch_advance_boardwalk", deck="chance", description="Advance to Boardwalk.", action="advance_to", destination=39),
    Card(id="ch_chairman", deck="chance", description="You have been elected Chairman of the Board. Pay each player $50.", action="pay_each_player", amount=50),
    Card(id="ch_building_loan", deck="chance", description="Your building loan matures. Collect $150.", action="collect", amount=150),
    Card(id="ch_crossword", deck="chance", description="You won a crossword competition. Collect $100.", action="collect", amount=100),
]

COMMUNITY_CARDS: list[Card] = [
    Card(id="cc_advance_go", deck="community", description="Advance to Go (Collect $200).", action="advance_to", destination=0),
    Card(id="cc_bank_error", deck="community", description="Bank error in your favor. Collect $200.", action="collect", amount=200),
    Card(id="cc_doctors_fee", deck="community", description="Doctor's fee. Pay $50.", action="pay", amount=50),
    Card(id="cc_stock_sale", deck="community", description="From sale of stock you get $50.", action="collect", amount=50),
    Card(id="cc_get_out_of_jail", deck="community", description="Get Out of Jail Free.", action="get_out_of_jail_free"),
    Card(id="cc_go_to_jail", deck="community", description="Go to Jail.", action="go_to_jail"),
    Card(id="cc_holiday_fund", deck="community", description="Holiday fund matures. Receive $100.", action="collect", amount=100),
    Card(id="cc_income_tax_refund", deck="community", description="Income tax refund. Collect $20.", action="collect", amount=20),
    Card(id="cc_birthday", deck="community", description="It is your birthday. Collect $10 from every player.", action="collect_from_each", amount=10),
    Card(id="cc_life_insurance", deck="community", description="Life insurance matures. Collect $100.", action="collect", amount=100),
    Card(id="cc_hospital_fees", deck="community", description="Pay hospital fees of $100.", action="pay", amount=100),
    Card(id="cc_school_fees", deck="community", description="Pay school fees of $150.", action="pay", amount=150),
    Card(id="cc_consultancy", deck="community", description="Receive $25 consultancy fee.", action="collect", amount=25),
    Card(id="cc_street_repairs", deck="community", description="Street repairs: $40/house, $115/hotel.", action="repairs_community"),
    Card(id="cc_beauty_contest", deck="community", description="Second prize in beauty contest. Collect $10.", action="collect", amount=10),
    Card(id="cc_inheritance", deck="community", description="You inherit $100.", action="collect", amount=100),
]


def build_chance_deck() -> list[Card]:
    deck = [c.model_copy() for c in CHANCE_CARDS]
    random.shuffle(deck)
    return deck


def build_community_deck() -> list[Card]:
    deck = [c.model_copy() for c in COMMUNITY_CARDS]
    random.shuffle(deck)
    return deck
```

- [ ] **Step 2: Commit**

```bash
git add backend/cards.py
git commit -m "feat: add card decks"
```

---

### Task 5: Game State Models + Helpers (game_state.py)

**Files:**
- Create: `backend/game_state.py`

- [ ] **Step 1: Create `backend/game_state.py`**

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

from board import Space, build_board, COLOR_GROUPS
from player import Player, PLAYER_COLORS
from cards import Card, build_chance_deck, build_community_deck


class AuctionState(BaseModel):
    property_id: str
    bids: dict[str, int] = Field(default_factory=dict)
    highest_bidder: Optional[str] = None
    highest_bid: int = 0
    ends_at: datetime


class TradeOffer(BaseModel):
    from_player: str
    to_player: str
    give_properties: list[str] = Field(default_factory=list)
    give_cash: int = 0
    give_jail_cards: int = 0
    request_properties: list[str] = Field(default_factory=list)
    request_cash: int = 0
    request_jail_cards: int = 0
    status: str = "pending"


class GameSession(BaseModel):
    code: str
    host_id: str
    players: dict[str, Player] = Field(default_factory=dict)
    max_players: int = 4
    status: str = "waiting"
    phase: str = "turn_roll"
    current_player_index: int = 0
    board: list[Space] = Field(default_factory=list)
    chance_deck: list[Card] = Field(default_factory=list)
    community_deck: list[Card] = Field(default_factory=list)
    dice: Optional[tuple[int, int]] = None
    doubles_count: int = 0
    auction: Optional[AuctionState] = None
    pending_trade: Optional[TradeOffer] = None
    log: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"arbitrary_types_allowed": True}


def init_session(code: str, host_id: str, max_players: int = 4) -> GameSession:
    return GameSession(
        code=code,
        host_id=host_id,
        max_players=max_players,
        board=build_board(),
        chance_deck=build_chance_deck(),
        community_deck=build_community_deck(),
    )


def get_active_players(session: GameSession) -> list[Player]:
    return [p for p in session.players.values() if not p.is_bankrupt]


def get_current_player(session: GameSession) -> Player:
    active = get_active_players(session)
    return active[session.current_player_index % len(active)]


def get_space(session: GameSession, position: int) -> Space:
    return session.board[position]


def get_space_by_id(session: GameSession, space_id: str) -> Optional[Space]:
    return next((s for s in session.board if s.id == space_id), None)


def owner_has_monopoly(session: GameSession, group: str) -> bool:
    group_spaces = [s for s in session.board if s.group == group
                    and s.space_type in ("property", "railroad", "utility")]
    if not group_spaces:
        return False
    owners = {s.owner_id for s in group_spaces}
    return len(owners) == 1 and None not in owners


def count_owned_unmortgaged_in_group(session: GameSession, player_id: str, group: str) -> int:
    return sum(
        1 for s in session.board
        if s.group == group and s.owner_id == player_id and not s.is_mortgaged
    )


def calculate_rent(session: GameSession, space: Space, dice_sum: int) -> int:
    if space.owner_id is None or space.is_mortgaged:
        return 0
    if space.space_type == "railroad":
        count = count_owned_unmortgaged_in_group(session, space.owner_id, "Railroad")
        return 25 * (2 ** (count - 1))
    if space.space_type == "utility":
        count = count_owned_unmortgaged_in_group(session, space.owner_id, "Utility")
        return (10 if count == 2 else 4) * dice_sum
    if space.space_type == "property":
        if space.has_hotel:
            return space.rent[5]
        if space.houses > 0:
            return space.rent[space.houses]
        if owner_has_monopoly(session, space.group):
            return space.rent[0] * 2
        return space.rent[0]
    return 0
```

- [ ] **Step 2: Commit**

```bash
git add backend/game_state.py
git commit -m "feat: add GameSession models and rent helpers"
```

---

### Task 6: Session Manager (session_manager.py)

**Files:**
- Create: `backend/session_manager.py`

- [ ] **Step 1: Create `backend/session_manager.py`**

```python
from __future__ import annotations
import asyncio
import random
import string
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import WebSocket

from game_state import GameSession, init_session
from player import Player, PLAYER_COLORS

sessions: dict[str, GameSession] = {}
connections: dict[str, dict[str, WebSocket]] = {}


def _generate_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def create_session(nickname: str, max_players: int = 4) -> tuple[str, str]:
    code = _generate_code()
    while code in sessions:
        code = _generate_code()
    player_id = str(uuid.uuid4())
    session = init_session(code=code, host_id=player_id, max_players=max_players)
    player = Player(id=player_id, nickname=nickname, color=PLAYER_COLORS[0])
    session.players[player_id] = player
    sessions[code] = session
    connections[code] = {}
    return code, player_id


def join_session(code: str, nickname: str) -> tuple[bool, str | None, str | None]:
    session = sessions.get(code)
    if not session:
        return False, None, "Session not found"
    if session.status != "waiting":
        return False, None, "Game already started"
    if len(session.players) >= session.max_players:
        return False, None, "Session full"
    used_colors = {p.color for p in session.players.values()}
    color = next((c for c in PLAYER_COLORS if c not in used_colors), PLAYER_COLORS[0])
    player_id = str(uuid.uuid4())
    player = Player(id=player_id, nickname=nickname, color=color)
    session.players[player_id] = player
    return True, player_id, None


def connect_player(code: str, player_id: str, ws: WebSocket) -> bool:
    session = sessions.get(code)
    if not session or player_id not in session.players:
        return False
    session.players[player_id].is_active = True
    session.players[player_id].last_seen = datetime.now(timezone.utc)
    connections.setdefault(code, {})[player_id] = ws
    return True


def disconnect_player(code: str, player_id: str) -> None:
    session = sessions.get(code)
    if session and player_id in session.players:
        session.players[player_id].is_active = False
        session.players[player_id].last_seen = datetime.now(timezone.utc)
    connections.get(code, {}).pop(player_id, None)


async def cleanup_loop() -> None:
    while True:
        await asyncio.sleep(30)
        now = datetime.now(timezone.utc)
        to_delete: list[str] = []
        for code, session in sessions.items():
            if session.status == "game_over" and not connections.get(code):
                to_delete.append(code)
                continue
            timeout = timedelta(minutes=2)
            all_gone = all(
                not p.is_active and (now - p.last_seen) > timeout
                for p in session.players.values()
            )
            if all_gone:
                to_delete.append(code)
        for code in to_delete:
            sessions.pop(code, None)
            connections.pop(code, None)
```

- [ ] **Step 2: Commit**

```bash
git add backend/session_manager.py
git commit -m "feat: add session manager with cleanup"
```

---

### Task 7: WebSocket Handler (websocket_handler.py)

**Files:**
- Create: `backend/websocket_handler.py`

- [ ] **Step 1: Create `backend/websocket_handler.py`**

```python
from __future__ import annotations
import session_manager as sm
from actions import handle_action


async def broadcast_state(code: str) -> None:
    session = sm.sessions.get(code)
    if not session:
        return
    conns = sm.connections.get(code, {})
    payload = {"type": "game_state", "data": session.model_dump(mode="json")}
    dead: list[str] = []
    for pid, ws in list(conns.items()):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(pid)
    for pid in dead:
        sm.disconnect_player(code, pid)


async def handle_message(code: str, player_id: str, data: dict) -> None:
    msg_type = data.get("type")
    if not msg_type:
        return
    session = sm.sessions.get(code)
    if not session:
        return
    error = await handle_action(session, player_id, msg_type, data)
    if error:
        ws = sm.connections.get(code, {}).get(player_id)
        if ws:
            try:
                await ws.send_json({"type": "error", "message": error})
            except Exception:
                pass
        return
    await broadcast_state(code)
```

- [ ] **Step 2: Commit**

```bash
git add backend/websocket_handler.py
git commit -m "feat: add WebSocket handler"
```

---

### Task 8: FastAPI App (main.py)

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: Create `backend/main.py`**

```python
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import session_manager as sm
from websocket_handler import handle_message, broadcast_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(sm.cleanup_loop())
    yield


app = FastAPI(lifespan=lifespan)


class CreateGameRequest(BaseModel):
    nickname: str
    max_players: int = 4


class JoinGameRequest(BaseModel):
    session_code: str
    nickname: str


@app.post("/api/create_game")
async def create_game(req: CreateGameRequest):
    if not 2 <= req.max_players <= 6:
        return {"error": "max_players must be between 2 and 6"}
    code, player_id = sm.create_session(req.nickname, req.max_players)
    return {"session_code": code, "player_id": player_id}


@app.post("/api/join_game")
async def join_game(req: JoinGameRequest):
    success, player_id, error = sm.join_session(req.session_code.upper(), req.nickname)
    if not success:
        return {"success": False, "error": error}
    return {"success": True, "player_id": player_id}


@app.websocket("/ws/{session_code}/{player_id}")
async def websocket_endpoint(ws: WebSocket, session_code: str, player_id: str):
    await ws.accept()
    code = session_code.upper()
    if not sm.connect_player(code, player_id, ws):
        await ws.close(code=4001, reason="Invalid session or player")
        return
    await broadcast_state(code)
    try:
        while True:
            data = await ws.receive_json()
            await handle_message(code, player_id, data)
    except WebSocketDisconnect:
        sm.disconnect_player(code, player_id)
        await broadcast_state(code)
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: add FastAPI app with HTTP and WS endpoints"
```

---

### Task 9: Actions — Roll, Buy, End Turn, Start Game (actions.py)

**Files:**
- Create: `backend/actions.py`

- [ ] **Step 1: Create `backend/actions.py`**

```python
from __future__ import annotations
import random

from game_state import (
    GameSession, get_current_player, get_active_players,
    get_space, calculate_rent
)


async def handle_action(session: GameSession, player_id: str, action: str, data: dict) -> str | None:
    handlers = {
        "start_game": handle_start_game,
        "roll_dice": handle_roll_dice,
        "buy_property": handle_buy_property,
        "end_turn": handle_end_turn,
    }
    handler = handlers.get(action)
    if not handler:
        return f"Unknown action: {action}"
    return await handler(session, player_id, data)


async def handle_start_game(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.status != "waiting":
        return "Game already started"
    if player_id != session.host_id:
        return "Only the host can start the game"
    if len(session.players) < 2:
        return "Need at least 2 players to start"
    session.status = "started"
    session.phase = "turn_roll"
    first = get_current_player(session)
    session.log.append(f"Game started! {first.nickname} goes first.")
    return None


async def handle_roll_dice(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.status != "started":
        return "Game has not started"
    if session.phase != "turn_roll":
        return "Not time to roll"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"

    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    session.dice = (d1, d2)
    is_doubles = d1 == d2

    if current.in_jail:
        await _handle_jail_roll(session, current, d1, d2, is_doubles)
        return None

    if is_doubles:
        session.doubles_count += 1
        if session.doubles_count >= 3:
            _send_to_jail(session, current)
            session.doubles_count = 0
            session.phase = "turn_action"
            session.log.append(f"{current.nickname} rolled three doubles — sent to jail!")
            return None
    else:
        session.doubles_count = 0

    new_pos = _move_player(session, current, d1 + d2)
    session.log.append(f"{current.nickname} rolled {d1}+{d2} and moved to {session.board[new_pos].name}")
    await _resolve_landing(session, current, new_pos, d1 + d2)

    if is_doubles and session.phase == "turn_action":
        session.phase = "turn_roll"

    return None


async def _handle_jail_roll(session: GameSession, player, d1: int, d2: int, is_doubles: bool) -> None:
    if is_doubles:
        player.in_jail = False
        player.jail_turns = 0
        new_pos = _move_player(session, player, d1 + d2)
        session.log.append(f"{player.nickname} rolled doubles, got out of jail, moved to {session.board[new_pos].name}")
        await _resolve_landing(session, player, new_pos, d1 + d2)
    else:
        player.jail_turns += 1
        if player.jail_turns >= 3:
            player.cash -= 50
            player.in_jail = False
            player.jail_turns = 0
            new_pos = _move_player(session, player, d1 + d2)
            session.log.append(f"{player.nickname} paid $50 fine, left jail, moved to {session.board[new_pos].name}")
            await _resolve_landing(session, player, new_pos, d1 + d2)
        else:
            session.phase = "turn_action"
            session.log.append(f"{player.nickname} stays in jail (turn {player.jail_turns}/3)")


def _move_player(session: GameSession, player, steps: int) -> int:
    new_pos = (player.position + steps) % 40
    if new_pos < player.position or player.position + steps >= 40:
        player.cash += 200
        session.log.append(f"{player.nickname} passed Go, collected $200")
    player.position = new_pos
    return new_pos


async def _resolve_landing(session: GameSession, player, position: int, dice_sum: int) -> None:
    space = session.board[position]
    session.phase = "turn_action"

    if space.space_type == "go_to_jail":
        _send_to_jail(session, player)
        session.log.append(f"{player.nickname} landed on Go To Jail!")

    elif space.space_type == "tax":
        player.cash -= space.tax_amount
        session.log.append(f"{player.nickname} paid ${space.tax_amount} tax on {space.name}")

    elif space.space_type in ("property", "railroad", "utility"):
        if space.owner_id is None:
            session.log.append(f"{player.nickname} landed on unowned {space.name} (${space.price})")
        elif space.owner_id == player.id:
            session.log.append(f"{player.nickname} landed on their own {space.name}")
        else:
            rent = calculate_rent(session, space, dice_sum)
            if rent > 0:
                owner = session.players[space.owner_id]
                player.cash -= rent
                owner.cash += rent
                session.log.append(f"{player.nickname} paid ${rent} rent to {owner.nickname} for {space.name}")


def _send_to_jail(session: GameSession, player) -> None:
    player.position = 10
    player.in_jail = True
    player.jail_turns = 0
    session.doubles_count = 0


async def handle_buy_property(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.phase != "turn_action":
        return "Not in action phase"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"
    space = session.board[current.position]
    if space.space_type not in ("property", "railroad", "utility"):
        return "Cannot buy this space"
    if space.owner_id is not None:
        return "Property already owned"
    if current.cash < space.price:
        return "Insufficient funds"
    current.cash -= space.price
    space.owner_id = player_id
    current.properties.append(space.id)
    session.log.append(f"{current.nickname} bought {space.name} for ${space.price}")
    return None


async def handle_end_turn(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.phase != "turn_action":
        return "Not in action phase"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"
    active = get_active_players(session)
    session.current_player_index = (session.current_player_index + 1) % len(active)
    session.phase = "turn_roll"
    session.dice = None
    session.doubles_count = 0
    next_player = get_current_player(session)
    session.log.append(f"Turn passed to {next_player.nickname}")
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/actions.py
git commit -m "feat: add roll_dice, buy_property, end_turn, start_game actions"
```

---

### Task 10: Tests — Rent Calculation

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_rent.py`

- [ ] **Step 1: Create `backend/tests/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from game_state import init_session, GameSession
from player import Player


def make_session() -> GameSession:
    session = init_session(code="TEST01", host_id="p1", max_players=4)
    session.players["p1"] = Player(id="p1", nickname="Alice", color="red")
    session.players["p2"] = Player(id="p2", nickname="Bob", color="blue")
    session.status = "started"
    return session
```

- [ ] **Step 3: Create `backend/tests/test_rent.py`**

```python
from conftest import make_session
from game_state import calculate_rent, get_space_by_id


def test_no_rent_unowned():
    session = make_session()
    space = get_space_by_id(session, "mediterranean_ave")
    assert calculate_rent(session, space, 7) == 0


def test_base_rent_no_monopoly():
    session = make_session()
    space = get_space_by_id(session, "mediterranean_ave")
    space.owner_id = "p1"
    assert calculate_rent(session, space, 7) == 2


def test_monopoly_doubles_base_rent():
    session = make_session()
    for sid in ["mediterranean_ave", "baltic_ave"]:
        get_space_by_id(session, sid).owner_id = "p1"
    space = get_space_by_id(session, "mediterranean_ave")
    assert calculate_rent(session, space, 7) == 4


def test_one_house_rent():
    session = make_session()
    for sid in ["mediterranean_ave", "baltic_ave"]:
        get_space_by_id(session, sid).owner_id = "p1"
    space = get_space_by_id(session, "mediterranean_ave")
    space.houses = 1
    assert calculate_rent(session, space, 7) == 10


def test_hotel_rent():
    session = make_session()
    for sid in ["mediterranean_ave", "baltic_ave"]:
        get_space_by_id(session, sid).owner_id = "p1"
    space = get_space_by_id(session, "mediterranean_ave")
    space.has_hotel = True
    assert calculate_rent(session, space, 7) == 250


def test_no_rent_mortgaged():
    session = make_session()
    space = get_space_by_id(session, "mediterranean_ave")
    space.owner_id = "p1"
    space.is_mortgaged = True
    assert calculate_rent(session, space, 7) == 0


def test_railroad_one_owned():
    session = make_session()
    space = get_space_by_id(session, "reading_railroad")
    space.owner_id = "p1"
    assert calculate_rent(session, space, 7) == 25


def test_railroad_two_owned():
    session = make_session()
    for sid in ["reading_railroad", "pennsylvania_railroad"]:
        get_space_by_id(session, sid).owner_id = "p1"
    assert calculate_rent(session, get_space_by_id(session, "reading_railroad"), 7) == 50


def test_railroad_four_owned():
    session = make_session()
    for sid in ["reading_railroad", "pennsylvania_railroad", "bo_railroad", "short_line"]:
        get_space_by_id(session, sid).owner_id = "p1"
    assert calculate_rent(session, get_space_by_id(session, "reading_railroad"), 7) == 200


def test_railroad_mortgaged_excluded_from_count():
    session = make_session()
    for sid in ["reading_railroad", "pennsylvania_railroad"]:
        get_space_by_id(session, sid).owner_id = "p1"
    get_space_by_id(session, "pennsylvania_railroad").is_mortgaged = True
    assert calculate_rent(session, get_space_by_id(session, "reading_railroad"), 7) == 25


def test_utility_one_owned():
    session = make_session()
    get_space_by_id(session, "electric_company").owner_id = "p1"
    assert calculate_rent(session, get_space_by_id(session, "electric_company"), 8) == 32


def test_utility_both_owned():
    session = make_session()
    for sid in ["electric_company", "water_works"]:
        get_space_by_id(session, sid).owner_id = "p1"
    assert calculate_rent(session, get_space_by_id(session, "electric_company"), 8) == 80
```

- [ ] **Step 4: Run tests**

From `backend/` (activate venv first: `venv\Scripts\activate`):
```bash
python -m pytest tests/test_rent.py -v
```
Expected: 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/
git commit -m "test: add rent calculation tests"
```

---

### Task 11: Tests — Doubles and Jail Rolls

**Files:**
- Create: `backend/tests/test_doubles.py`

- [ ] **Step 1: Create `backend/tests/test_doubles.py`**

```python
from unittest.mock import patch
from conftest import make_session
from actions import handle_roll_dice


async def test_doubles_keeps_turn_roll_phase():
    session = make_session()
    session.phase = "turn_roll"
    with patch("actions.random.randint", side_effect=[3, 3]):
        await handle_roll_dice(session, "p1", {})
    assert session.phase == "turn_roll"
    assert session.doubles_count == 1


async def test_non_doubles_enters_action_phase():
    session = make_session()
    session.phase = "turn_roll"
    with patch("actions.random.randint", side_effect=[2, 5]):
        await handle_roll_dice(session, "p1", {})
    assert session.phase == "turn_action"
    assert session.doubles_count == 0


async def test_three_doubles_sends_to_jail():
    session = make_session()
    session.phase = "turn_roll"
    session.doubles_count = 2
    with patch("actions.random.randint", side_effect=[4, 4]):
        await handle_roll_dice(session, "p1", {})
    player = session.players["p1"]
    assert player.in_jail is True
    assert player.position == 10
    assert session.doubles_count == 0
    assert session.phase == "turn_action"


async def test_jail_doubles_release():
    session = make_session()
    session.phase = "turn_roll"
    p = session.players["p1"]
    p.in_jail = True
    p.jail_turns = 1
    p.position = 10
    with patch("actions.random.randint", side_effect=[3, 3]):
        await handle_roll_dice(session, "p1", {})
    assert p.in_jail is False
    assert p.position == 16  # 10 + 6


async def test_jail_third_turn_auto_pays_fine():
    session = make_session()
    session.phase = "turn_roll"
    p = session.players["p1"]
    p.in_jail = True
    p.jail_turns = 2
    p.position = 10
    with patch("actions.random.randint", side_effect=[2, 5]):
        await handle_roll_dice(session, "p1", {})
    assert p.in_jail is False
    assert p.cash == 1450  # 1500 - 50 fine
    assert p.position == 17  # 10 + 7


async def test_wrong_player_cannot_roll():
    session = make_session()
    session.phase = "turn_roll"
    error = await handle_roll_dice(session, "p2", {})
    assert error == "Not your turn"
```

- [ ] **Step 2: Run all backend tests**

```bash
python -m pytest tests/ -v
```
Expected: 18 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_doubles.py
git commit -m "test: add doubles and jail roll tests"
```

---

### Task 12: Smoke Test — Docker Build and Container Tests

- [ ] **Step 1: Build backend image**

```bash
docker build -t chillos-backend ./backend
```
Expected: image builds without error

- [ ] **Step 2: Run tests inside container**

```bash
docker run --rm chillos-backend python -m pytest tests/ -v
```
Expected: 18 tests PASS

- [ ] **Step 3: Start backend manually and verify HTTP endpoint**

```bash
docker run --rm -p 8000:8000 chillos-backend &
curl -s -X POST http://localhost:8000/api/create_game -H "Content-Type: application/json" -d '{"nickname":"Alice"}' | python -m json.tool
```
Expected: JSON with `session_code` and `player_id`

- [ ] **Step 4: Stop container and commit**

```bash
git commit --allow-empty -m "chore: phase 1 backend core complete"
```
