# Phase 2 — Backend Advanced Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Phase 1 backend with auctions, card draws (Chance/Community Chest), jail actions, building houses/hotels, mortgage/unmortgage, trading, and bankruptcy with win condition.

**Architecture:** All new logic is added to `actions.py` and `game_state.py`. Auction timer uses `asyncio.create_task`. Bankruptcy is detected immediately after any cash deduction. No new files needed — all additions extend existing modules.

**Tech Stack:** Same as Phase 1. Requires Phase 1 to be complete and all Phase 1 tests passing.

**Prerequisite:** Phase 1 complete. Run `python -m pytest tests/ -v` and confirm 18 PASS before starting.

---

## File Map (modifications only)

| File | What changes |
|------|-------------|
| `backend/actions.py` | Add 10 new action handlers; add `_check_bankruptcy()` call after every cash deduction |
| `backend/game_state.py` | Add `draw_card()`, `process_card()`, `resolve_bankruptcy()`, `check_win_condition()` |
| `backend/websocket_handler.py` | Import `broadcast_state` used by async auction task |
| `backend/tests/test_bankruptcy.py` | New test file |

---

### Task 1: Auction Logic

The auction is started when a player declines to buy a property. A 10-second async task fires `_end_auction`. All players can bid. Highest bidder wins.

**Files:**
- Modify: `backend/actions.py`
- Modify: `backend/game_state.py`

- [ ] **Step 1: Add auction helpers to `game_state.py`**

Add to the bottom of `backend/game_state.py`:

```python
from datetime import timedelta

def start_auction(session: GameSession, property_id: str) -> None:
    session.auction = AuctionState(
        property_id=property_id,
        ends_at=datetime.now(timezone.utc) + timedelta(seconds=10),
    )
    session.phase = "auction"
    space = get_space_by_id(session, property_id)
    session.log.append(f"Auction started for {space.name if space else property_id}!")


def resolve_auction(session: GameSession) -> None:
    auction = session.auction
    if not auction:
        return
    if auction.highest_bidder:
        winner = session.players.get(auction.highest_bidder)
        space = get_space_by_id(session, auction.property_id)
        if winner and space:
            winner.cash -= auction.highest_bid
            space.owner_id = winner.id
            winner.properties.append(space.id)
            session.log.append(f"{winner.nickname} won auction for {space.name} with bid ${auction.highest_bid}")
    else:
        space = get_space_by_id(session, auction.property_id)
        session.log.append(f"No bids — {space.name if space else auction.property_id} remains unowned")
    session.auction = None
    session.phase = "turn_action"
```

- [ ] **Step 2: Add auction action handlers to `actions.py`**

Add to the `handlers` dict in `handle_action` and implement:

```python
import asyncio
# (add to top of file, alongside existing imports)

# Add these keys to the handlers dict:
"decline_buy": handle_decline_buy,
"auction_bid": handle_auction_bid,

# Add functions:

async def handle_decline_buy(session: GameSession, player_id: str, data: dict) -> str | None:
    from game_state import start_auction
    import websocket_handler
    if session.phase != "turn_action":
        return "Not in action phase"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"
    space = session.board[current.position]
    if space.space_type not in ("property", "railroad", "utility"):
        return "Nothing to auction here"
    if space.owner_id is not None:
        return "Property already owned"
    start_auction(session, space.id)
    asyncio.create_task(_auction_timer(session.code, session))
    return None


async def _auction_timer(code: str, session: GameSession) -> None:
    import session_manager as sm
    from game_state import resolve_auction
    import websocket_handler as wh
    await asyncio.sleep(10)
    live_session = sm.sessions.get(code)
    if live_session and live_session.auction:
        resolve_auction(live_session)
        await wh.broadcast_state(code)


async def handle_auction_bid(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.phase != "auction" or not session.auction:
        return "No active auction"
    player = session.players.get(player_id)
    if not player or player.is_bankrupt:
        return "Invalid player"
    bid = data.get("bid", 0)
    if not isinstance(bid, int) or bid <= session.auction.highest_bid:
        return f"Bid must be higher than current highest (${session.auction.highest_bid})"
    if player.cash < bid:
        return "Insufficient funds"
    session.auction.bids[player_id] = bid
    session.auction.highest_bid = bid
    session.auction.highest_bidder = player_id
    session.log.append(f"{player.nickname} bid ${bid} in auction")
    return None
```

- [ ] **Step 3: Add `code` field to `GameSession` (already there from Phase 1 — verify it exists)**

```bash
python -c "from game_state import GameSession; s = GameSession(code='X', host_id='y'); print(s.code)"
```
Expected: `X`

- [ ] **Step 4: Commit**

```bash
git add backend/actions.py backend/game_state.py
git commit -m "feat: add auction logic with async 10s timer"
```

---

### Task 2: Card Drawing and Processing

**Files:**
- Modify: `backend/game_state.py`
- Modify: `backend/actions.py`

- [ ] **Step 1: Add `draw_and_process_card()` to `game_state.py`**

Add to bottom of `backend/game_state.py`:

```python
from cards import Card

def draw_card(session: GameSession, deck_type: str) -> Card:
    deck = session.chance_deck if deck_type == "chance" else session.community_deck
    card = deck.pop(0)
    deck.append(card)  # used card goes to bottom
    return card


def process_card(session: GameSession, player_id: str, card: Card, dice_sum: int) -> None:
    player = session.players[player_id]
    session.log.append(f"{player.nickname} drew: {card.description}")

    if card.action == "collect":
        player.cash += card.amount

    elif card.action == "pay":
        player.cash -= card.amount

    elif card.action == "advance_to":
        dest = card.destination
        if dest < player.position:
            player.cash += 200
            session.log.append(f"{player.nickname} passed Go, collected $200")
        player.position = dest

    elif card.action == "go_back_3":
        player.position = (player.position - 3) % 40

    elif card.action == "go_to_jail":
        _send_to_jail_helper(session, player)

    elif card.action == "get_out_of_jail_free":
        player.get_out_of_jail_free += 1

    elif card.action == "advance_nearest_utility":
        utilities = [12, 28]
        dest = min(utilities, key=lambda x: (x - player.position) % 40)
        if dest < player.position:
            player.cash += 200
        player.position = dest
        space = session.board[dest]
        if space.owner_id and space.owner_id != player_id:
            rent = calculate_rent(session, space, dice_sum)
            owner = session.players[space.owner_id]
            player.cash -= rent
            owner.cash += rent

    elif card.action == "advance_nearest_railroad":
        railroads = [5, 15, 25, 35]
        dest = min(railroads, key=lambda x: (x - player.position) % 40)
        if dest < player.position:
            player.cash += 200
        player.position = dest
        space = session.board[dest]
        if space.owner_id and space.owner_id != player_id:
            base_rent = calculate_rent(session, space, dice_sum)
            rent = base_rent * 2
            owner = session.players[space.owner_id]
            player.cash -= rent
            owner.cash += rent

    elif card.action == "repairs_chance":
        cost = sum(
            (25 * s.houses) + (100 if s.has_hotel else 0)
            for s in session.board if s.owner_id == player_id
        )
        player.cash -= cost

    elif card.action == "repairs_community":
        cost = sum(
            (40 * s.houses) + (115 if s.has_hotel else 0)
            for s in session.board if s.owner_id == player_id
        )
        player.cash -= cost

    elif card.action == "pay_each_player":
        active = get_active_players(session)
        others = [p for p in active if p.id != player_id]
        player.cash -= card.amount * len(others)
        for other in others:
            other.cash += card.amount

    elif card.action == "collect_from_each":
        active = get_active_players(session)
        others = [p for p in active if p.id != player_id]
        player.cash += card.amount * len(others)
        for other in others:
            other.cash -= card.amount


def _send_to_jail_helper(session: GameSession, player) -> None:
    player.position = 10
    player.in_jail = True
    player.jail_turns = 0
    session.doubles_count = 0
```

- [ ] **Step 2: Wire card draw into `_resolve_landing` in `actions.py`**

Replace the `chance` and `community_chest` handling in `_resolve_landing` (add these elif branches):

```python
    elif space.space_type == "chance":
        from game_state import draw_card, process_card
        card = draw_card(session, "chance")
        process_card(session, player.id, card, dice_sum)

    elif space.space_type == "community_chest":
        from game_state import draw_card, process_card
        card = draw_card(session, "community")
        process_card(session, player.id, card, dice_sum)
```

- [ ] **Step 3: Commit**

```bash
git add backend/actions.py backend/game_state.py
git commit -m "feat: add card drawing and all card action processing"
```

---

### Task 3: Jail Actions (pay fine, use card)

**Files:**
- Modify: `backend/actions.py`

- [ ] **Step 1: Add jail action handlers to `actions.py`**

Add to the `handlers` dict in `handle_action` and implement:

```python
"use_jail_card": handle_use_jail_card,
"pay_jail_fine": handle_pay_jail_fine,

async def handle_use_jail_card(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.phase != "turn_roll":
        return "Can only use jail card before rolling"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"
    if not current.in_jail:
        return "Not in jail"
    if current.get_out_of_jail_free < 1:
        return "No Get Out of Jail Free cards"
    current.get_out_of_jail_free -= 1
    current.in_jail = False
    current.jail_turns = 0
    session.log.append(f"{current.nickname} used a Get Out of Jail Free card")
    return None


async def handle_pay_jail_fine(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.phase != "turn_roll":
        return "Can only pay fine before rolling"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"
    if not current.in_jail:
        return "Not in jail"
    if current.cash < 50:
        return "Insufficient funds to pay fine"
    current.cash -= 50
    current.in_jail = False
    current.jail_turns = 0
    session.log.append(f"{current.nickname} paid $50 jail fine and is free")
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/actions.py
git commit -m "feat: add jail card and fine actions"
```

---

### Task 4: Building Houses and Hotels

**Files:**
- Modify: `backend/actions.py`
- Modify: `backend/game_state.py`

- [ ] **Step 1: Add even-build validator to `game_state.py`**

```python
def can_build_on(session: GameSession, player_id: str, space_id: str) -> str | None:
    space = get_space_by_id(session, space_id)
    if not space:
        return "Property not found"
    if space.space_type != "property":
        return "Can only build on color properties"
    if space.owner_id != player_id:
        return "You don't own this property"
    if space.is_mortgaged:
        return "Cannot build on mortgaged property"
    if not owner_has_monopoly(session, space.group):
        return "Must own full color group to build"
    group_spaces = [s for s in session.board if s.group == space.group]
    for s in group_spaces:
        if s.is_mortgaged:
            return "Cannot build while any group property is mortgaged"
    if space.has_hotel:
        return "Already has a hotel"
    current_houses = space.houses
    min_houses = min(s.houses for s in group_spaces if not s.has_hotel)
    if current_houses > min_houses:
        return "Even build rule: build on property with fewer houses first"
    return None


def can_sell_from(session: GameSession, player_id: str, space_id: str) -> str | None:
    space = get_space_by_id(session, space_id)
    if not space:
        return "Property not found"
    if space.owner_id != player_id:
        return "You don't own this property"
    if space.houses == 0 and not space.has_hotel:
        return "No buildings to sell"
    group_spaces = [s for s in session.board if s.group == space.group]
    if space.has_hotel:
        return None
    max_houses = max(s.houses for s in group_spaces)
    if space.houses < max_houses:
        return "Even sell rule: sell from property with most houses first"
    return None
```

- [ ] **Step 2: Add build/sell handlers to `actions.py`**

```python
"build_house": handle_build_house,
"sell_house": handle_sell_house,

async def handle_build_house(session: GameSession, player_id: str, data: dict) -> str | None:
    from game_state import can_build_on
    space_id = data.get("property_id")
    if not space_id:
        return "property_id required"
    error = can_build_on(session, player_id, space_id)
    if error:
        return error
    space = next(s for s in session.board if s.id == space_id)
    player = session.players[player_id]
    if space.houses == 4:
        if player.cash < space.hotel_cost:
            return "Insufficient funds for hotel"
        player.cash -= space.hotel_cost
        space.houses = 0
        space.has_hotel = True
        session.log.append(f"{player.nickname} built a hotel on {space.name}")
    else:
        if player.cash < space.house_cost:
            return "Insufficient funds for house"
        player.cash -= space.house_cost
        space.houses += 1
        session.log.append(f"{player.nickname} built house #{space.houses} on {space.name}")
    return None


async def handle_sell_house(session: GameSession, player_id: str, data: dict) -> str | None:
    from game_state import can_sell_from
    space_id = data.get("property_id")
    if not space_id:
        return "property_id required"
    error = can_sell_from(session, player_id, space_id)
    if error:
        return error
    space = next(s for s in session.board if s.id == space_id)
    player = session.players[player_id]
    if space.has_hotel:
        space.has_hotel = False
        space.houses = 4
        player.cash += space.hotel_cost // 2
        session.log.append(f"{player.nickname} sold hotel on {space.name} for ${space.hotel_cost // 2}")
    else:
        space.houses -= 1
        player.cash += space.house_cost // 2
        session.log.append(f"{player.nickname} sold a house on {space.name} for ${space.house_cost // 2}")
    return None
```

- [ ] **Step 3: Commit**

```bash
git add backend/actions.py backend/game_state.py
git commit -m "feat: add build and sell house/hotel actions"
```

---

### Task 5: Mortgage and Unmortgage

**Files:**
- Modify: `backend/actions.py`

- [ ] **Step 1: Add mortgage handlers**

```python
"mortgage": handle_mortgage,
"unmortgage": handle_unmortgage,

async def handle_mortgage(session: GameSession, player_id: str, data: dict) -> str | None:
    space_id = data.get("property_id")
    if not space_id:
        return "property_id required"
    space = next((s for s in session.board if s.id == space_id), None)
    if not space:
        return "Property not found"
    if space.owner_id != player_id:
        return "You don't own this property"
    if space.is_mortgaged:
        return "Already mortgaged"
    if space.houses > 0 or space.has_hotel:
        return "Must sell all buildings before mortgaging"
    space.is_mortgaged = True
    player = session.players[player_id]
    player.cash += space.mortgage_value
    session.log.append(f"{player.nickname} mortgaged {space.name} for ${space.mortgage_value}")
    return None


async def handle_unmortgage(session: GameSession, player_id: str, data: dict) -> str | None:
    space_id = data.get("property_id")
    if not space_id:
        return "property_id required"
    space = next((s for s in session.board if s.id == space_id), None)
    if not space:
        return "Property not found"
    if space.owner_id != player_id:
        return "You don't own this property"
    if not space.is_mortgaged:
        return "Not mortgaged"
    cost = int(space.mortgage_value * 1.1)
    player = session.players[player_id]
    if player.cash < cost:
        return f"Need ${cost} to unmortgage (value + 10% interest)"
    player.cash -= cost
    space.is_mortgaged = False
    session.log.append(f"{player.nickname} unmortgaged {space.name} for ${cost}")
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/actions.py
git commit -m "feat: add mortgage and unmortgage actions"
```

---

### Task 6: Trading

**Files:**
- Modify: `backend/actions.py`
- Modify: `backend/game_state.py`

- [ ] **Step 1: Add trade helpers to `game_state.py`**

```python
def apply_trade(session: GameSession, trade: TradeOffer) -> None:
    giver = session.players[trade.from_player]
    receiver = session.players[trade.to_player]

    giver.cash -= trade.give_cash
    receiver.cash += trade.give_cash
    giver.cash += trade.request_cash
    receiver.cash -= trade.request_cash

    for prop_id in trade.give_properties:
        space = get_space_by_id(session, prop_id)
        if space:
            space.owner_id = trade.to_player
        if prop_id in giver.properties:
            giver.properties.remove(prop_id)
        receiver.properties.append(prop_id)

    for prop_id in trade.request_properties:
        space = get_space_by_id(session, prop_id)
        if space:
            space.owner_id = trade.from_player
        if prop_id in receiver.properties:
            receiver.properties.remove(prop_id)
        giver.properties.append(prop_id)

    giver.get_out_of_jail_free -= trade.give_jail_cards
    receiver.get_out_of_jail_free += trade.give_jail_cards
    giver.get_out_of_jail_free += trade.request_jail_cards
    receiver.get_out_of_jail_free -= trade.request_jail_cards
```

- [ ] **Step 2: Add trade action handlers to `actions.py`**

```python
"propose_trade": handle_propose_trade,
"respond_trade": handle_respond_trade,

async def handle_propose_trade(session: GameSession, player_id: str, data: dict) -> str | None:
    from game_state import TradeOffer, apply_trade
    if session.phase not in ("turn_action", "turn_roll"):
        return "Cannot trade during auction or non-action phase"
    trade_data = data.get("trade", {})
    to_player = trade_data.get("to_player")
    if not to_player or to_player not in session.players:
        return "Invalid trade partner"
    if to_player == player_id:
        return "Cannot trade with yourself"
    giver = session.players[player_id]
    give_cash = trade_data.get("give_cash", 0)
    give_props = trade_data.get("give_properties", [])
    give_jail = trade_data.get("give_jail_cards", 0)
    req_cash = trade_data.get("request_cash", 0)
    req_props = trade_data.get("request_properties", [])
    req_jail = trade_data.get("request_jail_cards", 0)

    if giver.cash < give_cash:
        return "Insufficient cash for trade offer"
    for pid in give_props:
        if pid not in giver.properties:
            return f"You don't own {pid}"
    if giver.get_out_of_jail_free < give_jail:
        return "Not enough jail cards to offer"

    session.pending_trade = TradeOffer(
        from_player=player_id,
        to_player=to_player,
        give_properties=give_props,
        give_cash=give_cash,
        give_jail_cards=give_jail,
        request_properties=req_props,
        request_cash=req_cash,
        request_jail_cards=req_jail,
    )
    session.phase = "trading"
    session.log.append(f"{giver.nickname} proposed a trade to {session.players[to_player].nickname}")
    return None


async def handle_respond_trade(session: GameSession, player_id: str, data: dict) -> str | None:
    from game_state import apply_trade
    if session.phase != "trading" or not session.pending_trade:
        return "No pending trade"
    trade = session.pending_trade
    if player_id != trade.to_player:
        return "Only the trade recipient can respond"
    accept = data.get("accept", False)
    if accept:
        apply_trade(session, trade)
        session.log.append("Trade accepted!")
    else:
        session.log.append("Trade rejected")
    session.pending_trade = None
    session.phase = "turn_action"
    return None
```

- [ ] **Step 3: Commit**

```bash
git add backend/actions.py backend/game_state.py
git commit -m "feat: add trading actions"
```

---

### Task 7: Bankruptcy and Win Condition

**Files:**
- Modify: `backend/game_state.py`
- Modify: `backend/actions.py`

- [ ] **Step 1: Add `resolve_bankruptcy()` and `check_win_condition()` to `game_state.py`**

```python
def resolve_bankruptcy(session: GameSession, debtor_id: str, creditor_id: str | None) -> None:
    debtor = session.players[debtor_id]
    debtor.is_bankrupt = True
    for space in session.board:
        if space.owner_id == debtor_id:
            if creditor_id:
                space.owner_id = creditor_id
                creditor = session.players[creditor_id]
                if space.id not in creditor.properties:
                    creditor.properties.append(space.id)
            else:
                space.owner_id = None
                space.houses = 0
                space.has_hotel = False
                space.is_mortgaged = False
    if debtor_id in session.players:
        if creditor_id:
            creditor = session.players[creditor_id]
            creditor.cash += max(0, debtor.cash)
        debtor.cash = 0
        debtor.properties.clear()
    session.log.append(f"{debtor.nickname} has gone bankrupt!")


def check_win_condition(session: GameSession) -> str | None:
    active = get_active_players(session)
    if len(active) == 1:
        winner = active[0]
        session.status = "game_over"
        session.log.append(f"{winner.nickname} wins the game!")
        return winner.id
    return None
```

- [ ] **Step 2: Add `_check_bankruptcy()` helper to `actions.py` and call it after every cash deduction**

Add this function to `actions.py`:

```python
def _check_bankruptcy(session: GameSession, player_id: str, creditor_id: str | None) -> bool:
    from game_state import resolve_bankruptcy, check_win_condition
    player = session.players.get(player_id)
    if not player or player.cash >= 0:
        return False
    resolve_bankruptcy(session, player_id, creditor_id)
    check_win_condition(session)
    return True
```

Update `_resolve_landing` in `actions.py` — call after rent deduction:

```python
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
                _check_bankruptcy(session, player.id, owner.id)

    elif space.space_type == "tax":
        player.cash -= space.tax_amount
        session.log.append(f"{player.nickname} paid ${space.tax_amount} tax on {space.name}")
        _check_bankruptcy(session, player.id, None)
```

Also update `handle_end_turn` to skip bankrupt players when advancing `current_player_index`:

```python
async def handle_end_turn(session: GameSession, player_id: str, data: dict) -> str | None:
    if session.phase != "turn_action":
        return "Not in action phase"
    current = get_current_player(session)
    if current.id != player_id:
        return "Not your turn"
    if session.status == "game_over":
        return None
    active = get_active_players(session)
    session.current_player_index = (session.current_player_index + 1) % len(active)
    session.phase = "turn_roll"
    session.dice = None
    session.doubles_count = 0
    next_player = get_current_player(session)
    session.log.append(f"Turn passed to {next_player.nickname}")
    return None
```

- [ ] **Step 3: Commit**

```bash
git add backend/actions.py backend/game_state.py
git commit -m "feat: add bankruptcy resolution and win condition"
```

---

### Task 8: Tests — Bankruptcy

**Files:**
- Create: `backend/tests/test_bankruptcy.py`

- [ ] **Step 1: Create `backend/tests/test_bankruptcy.py`**

```python
from conftest import make_session
from game_state import resolve_bankruptcy, check_win_condition, get_space_by_id


def test_bankrupt_player_marked_bankrupt():
    session = make_session()
    resolve_bankruptcy(session, "p1", "p2")
    assert session.players["p1"].is_bankrupt is True


def test_property_transfers_to_creditor():
    session = make_session()
    space = get_space_by_id(session, "mediterranean_ave")
    space.owner_id = "p1"
    session.players["p1"].properties = ["mediterranean_ave"]
    resolve_bankruptcy(session, "p1", "p2")
    assert space.owner_id == "p2"
    assert "mediterranean_ave" in session.players["p2"].properties


def test_property_to_bank_on_no_creditor():
    session = make_session()
    space = get_space_by_id(session, "mediterranean_ave")
    space.owner_id = "p1"
    space.houses = 2
    session.players["p1"].properties = ["mediterranean_ave"]
    resolve_bankruptcy(session, "p1", None)
    assert space.owner_id is None
    assert space.houses == 0


def test_mortgaged_property_transfers_as_is():
    session = make_session()
    space = get_space_by_id(session, "mediterranean_ave")
    space.owner_id = "p1"
    space.is_mortgaged = True
    session.players["p1"].properties = ["mediterranean_ave"]
    resolve_bankruptcy(session, "p1", "p2")
    assert space.owner_id == "p2"
    assert space.is_mortgaged is True


def test_remaining_cash_goes_to_creditor():
    session = make_session()
    session.players["p1"].cash = 100
    session.players["p2"].cash = 500
    resolve_bankruptcy(session, "p1", "p2")
    assert session.players["p2"].cash == 600
    assert session.players["p1"].cash == 0


def test_win_condition_triggers_on_one_player():
    session = make_session()
    session.players["p1"].is_bankrupt = True
    winner_id = check_win_condition(session)
    assert winner_id == "p2"
    assert session.status == "game_over"


def test_no_win_with_two_active_players():
    session = make_session()
    winner_id = check_win_condition(session)
    assert winner_id is None
    assert session.status != "game_over"
```

- [ ] **Step 2: Run all backend tests**

```bash
python -m pytest tests/ -v
```
Expected: 25 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_bankruptcy.py
git commit -m "test: add bankruptcy tests"
```

---

### Task 9: Smoke Test — Full Backend

- [ ] **Step 1: Build and run all tests inside Docker**

```bash
docker build -t chillos-backend ./backend
docker run --rm chillos-backend python -m pytest tests/ -v
```
Expected: 25 tests PASS

- [ ] **Step 2: Commit**

```bash
git commit --allow-empty -m "chore: phase 2 backend advanced complete"
```
