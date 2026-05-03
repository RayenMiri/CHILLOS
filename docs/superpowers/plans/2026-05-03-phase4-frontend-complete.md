# Phase 4 — Frontend Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the frontend with PlayerPanel (property management, build/mortgage controls), AuctionModal (server-synced countdown), TradeModal, ChatLog, GameOver screen, and reconnection overlay polish.

**Architecture:** All new components follow the same pattern: read state from `useGameStore()`, send actions via `sendAction` prop. AuctionModal derives its countdown from the server `ends_at` timestamp to avoid client clock drift.

**Tech Stack:** Same as Phase 3. Requires Phase 3 complete and both containers running.

**Prerequisite:** Phase 3 complete. `docker-compose up --build` serves a working game at http://localhost:80.

---

## File Map

| File | Responsibility |
|------|---------------|
| `frontend/src/components/PlayerPanel.tsx` | Player list, own property list with build/sell/mortgage/unmortgage buttons |
| `frontend/src/components/AuctionModal.tsx` | 10s countdown synced to `ends_at`, bid input, current high bid display |
| `frontend/src/components/TradeModal.tsx` | Select partner, check properties to give/request, cash inputs, propose |
| `frontend/src/components/ChatLog.tsx` | Chat messages + free text input |
| `frontend/src/components/GameOver.tsx` | Winner announcement overlay |
| `frontend/src/App.tsx` | Modified to include all new components |

---

### Task 1: Player Panel

Displays all players' cash and turn indicator. For the local player, shows owned properties with contextual action buttons (build house/hotel, sell, mortgage, unmortgage).

**Files:**
- Create: `frontend/src/components/PlayerPanel.tsx`

- [ ] **Step 1: Create `frontend/src/components/PlayerPanel.tsx`**

```tsx
import { useGameStore } from '../store/gameStore'
import type { ClientAction, Space } from '../types/game'

const COLOR_DOT: Record<string, string> = {
  red: '#ef4444', blue: '#3b82f6', green: '#22c55e',
  yellow: '#eab308', purple: '#a855f7', orange: '#f97316',
}

interface PlayerPanelProps {
  sendAction: (action: ClientAction) => void
  onOpenTrade: () => void
}

export function PlayerPanel({ sendAction, onOpenTrade }: PlayerPanelProps) {
  const { session, myPlayerId } = useGameStore()
  if (!session || !myPlayerId) return null
  const me = session.players[myPlayerId]
  const activePlayers = Object.values(session.players).filter((p) => !p.is_bankrupt)
  const currentPlayer = activePlayers[session.current_player_index % activePlayers.length]
  const isMyTurn = currentPlayer?.id === myPlayerId
  const inActionPhase = session.phase === 'turn_action' && isMyTurn

  function getSpaceById(id: string): Space | undefined {
    return session.board.find((s) => s.id === id)
  }

  function canBuildHouse(space: Space): boolean {
    if (space.space_type !== 'property') return false
    if (space.has_hotel || space.is_mortgaged) return false
    const groupSpaces = session.board.filter((s) => s.group === space.group)
    const allOwned = groupSpaces.every((s) => s.owner_id === myPlayerId)
    if (!allOwned) return false
    const minHouses = Math.min(...groupSpaces.map((s) => s.houses))
    return inActionPhase && space.houses === minHouses
  }

  function canSellBuilding(space: Space): boolean {
    if (space.houses === 0 && !space.has_hotel) return false
    const groupSpaces = session.board.filter((s) => s.group === space.group)
    if (space.has_hotel) return true
    const maxHouses = Math.max(...groupSpaces.map((s) => s.houses))
    return space.houses >= maxHouses
  }

  return (
    <div className="bg-white rounded-xl shadow overflow-hidden">
      <div className="p-3 bg-gray-50 border-b">
        <h3 className="font-semibold text-gray-700 text-sm">Players</h3>
      </div>
      <div className="divide-y">
        {Object.values(session.players).map((player) => {
          const isCurrent = currentPlayer?.id === player.id
          return (
            <div
              key={player.id}
              className={`px-3 py-2 flex items-center justify-between ${isCurrent ? 'bg-yellow-50' : ''} ${player.is_bankrupt ? 'opacity-40' : ''}`}
            >
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full border border-white shadow"
                  style={{ backgroundColor: COLOR_DOT[player.color] ?? player.color }} />
                <span className="text-sm font-medium">{player.nickname}</span>
                {isCurrent && <span className="text-xs text-yellow-600">▶</span>}
                {player.is_bankrupt && <span className="text-xs text-red-500">BANKRUPT</span>}
              </div>
              <span className="text-sm font-semibold text-green-700">${player.cash.toLocaleString()}</span>
            </div>
          )
        })}
      </div>

      {me && !me.is_bankrupt && (
        <div className="p-3 border-t">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-700 text-sm">My Properties</h3>
            {inActionPhase && (
              <button
                onClick={onOpenTrade}
                className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-200"
              >Trade</button>
            )}
          </div>
          {me.properties.length === 0 && (
            <p className="text-xs text-gray-400">No properties yet</p>
          )}
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {me.properties.map((pid) => {
              const space = getSpaceById(pid)
              if (!space) return null
              return (
                <div key={pid} className="text-xs border rounded p-1.5">
                  <div className="flex justify-between items-center mb-1">
                    <span className={`font-medium ${space.is_mortgaged ? 'line-through text-gray-400' : ''}`}>
                      {space.name}
                    </span>
                    <span className="text-gray-500">${space.price}</span>
                  </div>
                  {inActionPhase && (
                    <div className="flex gap-1 flex-wrap">
                      {canBuildHouse(space) && (
                        <button
                          onClick={() => sendAction({ type: 'build_house', property_id: pid })}
                          className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded hover:bg-green-200"
                        >{space.houses === 4 ? 'Build Hotel' : 'Build House'}</button>
                      )}
                      {canSellBuilding(space) && (
                        <button
                          onClick={() => sendAction({ type: 'sell_house', property_id: pid })}
                          className="bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded hover:bg-orange-200"
                        >Sell</button>
                      )}
                      {!space.is_mortgaged && space.houses === 0 && !space.has_hotel && (
                        <button
                          onClick={() => sendAction({ type: 'mortgage', property_id: pid })}
                          className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded hover:bg-red-200"
                        >Mortgage</button>
                      )}
                      {space.is_mortgaged && (
                        <button
                          onClick={() => sendAction({ type: 'unmortgage', property_id: pid })}
                          className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-200"
                        >Unmortgage (${Math.ceil(space.mortgage_value * 1.1)})</button>
                      )}
                    </div>
                  )}
                  {(space.houses > 0 || space.has_hotel) && (
                    <div className="flex gap-0.5 mt-1">
                      {space.has_hotel
                        ? <span className="text-red-500 font-bold">🏨</span>
                        : Array.from({ length: space.houses }).map((_, i) => (
                            <span key={i} className="text-green-600">🏠</span>
                          ))
                      }
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PlayerPanel.tsx
git commit -m "feat: add PlayerPanel with property management"
```

---

### Task 2: Auction Modal

The countdown is derived from the server's `ends_at` ISO timestamp so all clients see the same remaining time regardless of local clock offset.

**Files:**
- Create: `frontend/src/components/AuctionModal.tsx`

- [ ] **Step 1: Create `frontend/src/components/AuctionModal.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { useGameStore } from '../store/gameStore'
import type { ClientAction } from '../types/game'

interface AuctionModalProps {
  sendAction: (action: ClientAction) => void
}

export function AuctionModal({ sendAction }: AuctionModalProps) {
  const { session, myPlayerId } = useGameStore()
  const [bidInput, setBidInput] = useState('')
  const [secondsLeft, setSecondsLeft] = useState(10)

  const auction = session?.auction
  const me = myPlayerId ? session?.players[myPlayerId] : null

  useEffect(() => {
    if (!auction) return
    const tick = () => {
      const remaining = (new Date(auction.ends_at).getTime() - Date.now()) / 1000
      setSecondsLeft(Math.max(0, Math.ceil(remaining)))
    }
    tick()
    const id = setInterval(tick, 250)
    return () => clearInterval(id)
  }, [auction])

  if (!session || session.phase !== 'auction' || !auction) return null

  const space = session.board.find((s) => s.id === auction.property_id)
  const winner = auction.highest_bidder ? session.players[auction.highest_bidder] : null
  const myBid = auction.bids[myPlayerId ?? ''] ?? 0

  function handleBid() {
    const amount = parseInt(bidInput, 10)
    if (!isNaN(amount)) {
      sendAction({ type: 'auction_bid', bid: amount })
      setBidInput('')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm">
        <h2 className="text-xl font-bold mb-1">Auction</h2>
        <p className="text-lg font-semibold text-green-700 mb-4">{space?.name ?? auction.property_id}</p>

        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Time remaining</span>
            <span className={secondsLeft <= 3 ? 'text-red-600 font-bold' : ''}>{secondsLeft}s</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{ width: `${(secondsLeft / 10) * 100}%` }}
            />
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <p className="text-sm text-gray-600">
            Highest bid:{' '}
            <strong>${auction.highest_bid}</strong>
            {winner && <span> by {winner.nickname}</span>}
          </p>
          {myBid > 0 && <p className="text-sm text-blue-600 mt-1">Your bid: ${myBid}</p>}
        </div>

        {me && !me.is_bankrupt && secondsLeft > 0 && (
          <div className="flex gap-2">
            <input
              type="number"
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
              placeholder={`Min $${auction.highest_bid + 1}`}
              value={bidInput}
              onChange={(e) => setBidInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleBid()}
              min={auction.highest_bid + 1}
              max={me.cash}
            />
            <button
              onClick={handleBid}
              className="bg-green-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-green-700 text-sm"
            >Bid</button>
          </div>
        )}
        {secondsLeft === 0 && (
          <p className="text-center text-gray-500 text-sm">Auction ended</p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AuctionModal.tsx
git commit -m "feat: add AuctionModal with server-synced countdown"
```

---

### Task 3: Trade Modal

**Files:**
- Create: `frontend/src/components/TradeModal.tsx`

- [ ] **Step 1: Create `frontend/src/components/TradeModal.tsx`**

```tsx
import { useState } from 'react'
import { useGameStore } from '../store/gameStore'
import type { ClientAction } from '../types/game'

interface TradeModalProps {
  onClose: () => void
  sendAction: (action: ClientAction) => void
}

export function TradeModal({ onClose, sendAction }: TradeModalProps) {
  const { session, myPlayerId } = useGameStore()
  const [toPlayer, setToPlayer] = useState('')
  const [giveProps, setGiveProps] = useState<string[]>([])
  const [requestProps, setRequestProps] = useState<string[]>([])
  const [giveCash, setGiveCash] = useState(0)
  const [requestCash, setRequestCash] = useState(0)
  const [giveJail, setGiveJail] = useState(0)
  const [requestJail, setRequestJail] = useState(0)

  if (!session || !myPlayerId) return null

  const me = session.players[myPlayerId]
  const pendingTrade = session.pending_trade

  if (pendingTrade?.to_player === myPlayerId && pendingTrade.status === 'pending') {
    const from = session.players[pendingTrade.from_player]
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
        <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm">
          <h2 className="text-xl font-bold mb-4">Trade Offer from {from?.nickname}</h2>
          <div className="space-y-2 text-sm mb-4">
            <p><strong>They offer:</strong></p>
            {pendingTrade.give_properties.map((id) => {
              const s = session.board.find((b) => b.id === id)
              return <p key={id} className="ml-2">• {s?.name ?? id}</p>
            })}
            {pendingTrade.give_cash > 0 && <p className="ml-2">• ${pendingTrade.give_cash} cash</p>}
            {pendingTrade.give_jail_cards > 0 && <p className="ml-2">• {pendingTrade.give_jail_cards} jail card(s)</p>}
            <p className="mt-2"><strong>They want:</strong></p>
            {pendingTrade.request_properties.map((id) => {
              const s = session.board.find((b) => b.id === id)
              return <p key={id} className="ml-2">• {s?.name ?? id}</p>
            })}
            {pendingTrade.request_cash > 0 && <p className="ml-2">• ${pendingTrade.request_cash} cash</p>}
            {pendingTrade.request_jail_cards > 0 && <p className="ml-2">• {pendingTrade.request_jail_cards} jail card(s)</p>}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => { sendAction({ type: 'respond_trade', accept: true }); onClose() }}
              className="flex-1 bg-green-600 text-white py-2 rounded-lg font-semibold hover:bg-green-700"
            >Accept</button>
            <button
              onClick={() => { sendAction({ type: 'respond_trade', accept: false }); onClose() }}
              className="flex-1 bg-red-500 text-white py-2 rounded-lg font-semibold hover:bg-red-600"
            >Reject</button>
          </div>
        </div>
      </div>
    )
  }

  const partners = Object.values(session.players).filter(
    (p) => p.id !== myPlayerId && !p.is_bankrupt
  )
  const partnerProps = toPlayer
    ? session.board.filter((s) => s.owner_id === toPlayer)
    : []

  function toggleProp(id: string, list: string[], setter: (v: string[]) => void) {
    setter(list.includes(id) ? list.filter((x) => x !== id) : [...list, id])
  }

  function handlePropose() {
    if (!toPlayer) return
    sendAction({
      type: 'propose_trade',
      trade: {
        from_player: myPlayerId!,
        to_player: toPlayer,
        give_properties: giveProps,
        give_cash: giveCash,
        give_jail_cards: giveJail,
        request_properties: requestProps,
        request_cash: requestCash,
        request_jail_cards: requestJail,
      },
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-lg max-h-screen overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Propose Trade</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Trade with:</label>
          <select
            className="w-full border rounded-lg px-3 py-2"
            value={toPlayer}
            onChange={(e) => { setToPlayer(e.target.value); setRequestProps([]) }}
          >
            <option value="">Select player…</option>
            {partners.map((p) => <option key={p.id} value={p.id}>{p.nickname}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm font-medium mb-2">You offer:</p>
            {me.properties.map((pid) => {
              const s = session.board.find((b) => b.id === pid)
              if (!s) return null
              return (
                <label key={pid} className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
                  <input type="checkbox" checked={giveProps.includes(pid)}
                    onChange={() => toggleProp(pid, giveProps, setGiveProps)} />
                  {s.name}
                </label>
              )
            })}
            <div className="mt-2">
              <label className="text-xs font-medium block mb-0.5">Cash ($)</label>
              <input type="number" min={0} max={me.cash} value={giveCash}
                onChange={(e) => setGiveCash(Math.max(0, parseInt(e.target.value) || 0))}
                className="w-full border rounded px-2 py-1 text-xs" />
            </div>
            {me.get_out_of_jail_free > 0 && (
              <div className="mt-2">
                <label className="text-xs font-medium block mb-0.5">Jail cards (have {me.get_out_of_jail_free})</label>
                <input type="number" min={0} max={me.get_out_of_jail_free} value={giveJail}
                  onChange={(e) => setGiveJail(Math.max(0, Math.min(me.get_out_of_jail_free, parseInt(e.target.value) || 0)))}
                  className="w-full border rounded px-2 py-1 text-xs" />
              </div>
            )}
          </div>
          <div>
            <p className="text-sm font-medium mb-2">You request:</p>
            {partnerProps.map((s) => (
              <label key={s.id} className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
                <input type="checkbox" checked={requestProps.includes(s.id)}
                  onChange={() => toggleProp(s.id, requestProps, setRequestProps)} />
                {s.name}
              </label>
            ))}
            <div className="mt-2">
              <label className="text-xs font-medium block mb-0.5">Cash ($)</label>
              <input type="number" min={0} value={requestCash}
                onChange={(e) => setRequestCash(Math.max(0, parseInt(e.target.value) || 0))}
                className="w-full border rounded px-2 py-1 text-xs" />
            </div>
          </div>
        </div>
        <button
          onClick={handlePropose}
          disabled={!toPlayer}
          className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
        >Propose Trade</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TradeModal.tsx
git commit -m "feat: add TradeModal"
```

---

### Task 4: Chat Log

**Files:**
- Create: `frontend/src/components/ChatLog.tsx`

- [ ] **Step 1: Create `frontend/src/components/ChatLog.tsx`**

```tsx
import { useState, useRef, useEffect } from 'react'
import { useGameStore } from '../store/gameStore'
import type { ClientAction } from '../types/game'

interface ChatLogProps {
  sendAction: (action: ClientAction) => void
}

export function ChatLog({ sendAction }: ChatLogProps) {
  const { session, chatMessages } = useGameStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, session?.log])

  function handleSend() {
    if (!input.trim()) return
    sendAction({ type: 'chat', message: input.trim() })
    setInput('')
  }

  return (
    <div className="bg-white rounded-xl shadow flex flex-col" style={{ height: 200 }}>
      <div className="px-3 py-2 border-b bg-gray-50 rounded-t-xl">
        <h3 className="text-sm font-semibold text-gray-600">Chat & Log</h3>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5 text-xs text-gray-700">
        {session?.log.slice(-30).map((entry, i) => (
          <p key={`log-${i}`} className="text-gray-500">{entry}</p>
        ))}
        {chatMessages.map((msg, i) => (
          <p key={`chat-${i}`}><strong>{msg.nickname}:</strong> {msg.message}</p>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="px-2 py-1.5 border-t flex gap-1">
        <input
          className="flex-1 border rounded px-2 py-1 text-xs"
          placeholder="Message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button
          onClick={handleSend}
          className="bg-blue-500 text-white px-2 py-1 rounded text-xs hover:bg-blue-600"
        >Send</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire chat in the backend** — add `handle_chat` to `backend/actions.py`:

```python
"chat": handle_chat,

async def handle_chat(session: GameSession, player_id: str, data: dict) -> str | None:
    return None
```

Chat messages are sent as a separate WS message type in `websocket_handler.py`. Update `handle_message` to broadcast chat separately:

```python
async def handle_message(code: str, player_id: str, data: dict) -> None:
    msg_type = data.get("type")
    if not msg_type:
        return
    session = sm.sessions.get(code)
    if not session:
        return
    if msg_type == "chat":
        player = session.players.get(player_id)
        if player:
            conns = sm.connections.get(code, {})
            payload = {"type": "chat", "nickname": player.nickname, "message": data.get("message", "")}
            for ws in list(conns.values()):
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass
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

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChatLog.tsx backend/actions.py backend/websocket_handler.py
git commit -m "feat: add ChatLog and backend chat handler"
```

---

### Task 5: Game Over Screen

**Files:**
- Create: `frontend/src/components/GameOver.tsx`

- [ ] **Step 1: Create `frontend/src/components/GameOver.tsx`**

```tsx
import { useGameStore } from '../store/gameStore'

export function GameOver() {
  const { session, reset } = useGameStore()
  if (!session || session.status !== 'game_over') return null

  const activePlayers = Object.values(session.players).filter((p) => !p.is_bankrupt)
  const winner = activePlayers[0]

  function handlePlayAgain() {
    localStorage.removeItem('playerId')
    localStorage.removeItem('sessionCode')
    reset()
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 text-center w-full max-w-sm">
        <div className="text-5xl mb-4">🏆</div>
        <h2 className="text-2xl font-bold mb-2">Game Over!</h2>
        {winner && (
          <p className="text-xl text-green-700 font-semibold mb-4">{winner.nickname} wins!</p>
        )}
        <div className="text-sm text-gray-600 mb-6 text-left space-y-1">
          {Object.values(session.players)
            .sort((a, b) => (b.is_bankrupt ? -1 : 1) - (a.is_bankrupt ? -1 : 1))
            .map((p) => (
              <div key={p.id} className="flex justify-between">
                <span className={p.is_bankrupt ? 'line-through text-gray-400' : ''}>{p.nickname}</span>
                <span>${p.cash.toLocaleString()}</span>
              </div>
            ))}
        </div>
        <button
          onClick={handlePlayAgain}
          className="w-full bg-green-600 text-white py-3 rounded-xl font-semibold hover:bg-green-700"
        >Play Again</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GameOver.tsx
git commit -m "feat: add GameOver screen"
```

---

### Task 6: Wire All Components into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace `frontend/src/App.tsx` with the complete version**

```tsx
import { useEffect, useState } from 'react'
import { useGameStore } from './store/gameStore'
import { useGameWebSocket } from './hooks/useGameWebSocket'
import { Lobby } from './components/Lobby'
import { Board } from './components/Board'
import { TurnControls } from './components/TurnControls'
import { PlayerPanel } from './components/PlayerPanel'
import { AuctionModal } from './components/AuctionModal'
import { TradeModal } from './components/TradeModal'
import { ChatLog } from './components/ChatLog'
import { GameOver } from './components/GameOver'

function Game() {
  const { session, isReconnecting } = useGameStore()
  const { sendAction } = useGameWebSocket()
  const [tradeOpen, setTradeOpen] = useState(false)

  if (!session) return <div className="text-white text-center mt-20 text-lg">Connecting…</div>

  return (
    <div className="min-h-screen bg-green-900 p-2 flex gap-2">
      {isReconnecting && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8 text-center shadow-xl">
            <div className="text-2xl mb-2">⟳</div>
            <p className="text-lg font-semibold">Reconnecting…</p>
            <p className="text-sm text-gray-500 mt-1">Please wait</p>
          </div>
        </div>
      )}

      <GameOver />

      {session.phase === 'auction' && session.auction && (
        <AuctionModal sendAction={sendAction} />
      )}

      {tradeOpen && (
        <TradeModal sendAction={sendAction} onClose={() => setTradeOpen(false)} />
      )}

      <div className="flex-1 min-w-0">
        <Board session={session} />
      </div>

      <div className="w-72 flex flex-col gap-2 flex-shrink-0">
        <TurnControls sendAction={sendAction} />
        <PlayerPanel sendAction={sendAction} onOpenTrade={() => setTradeOpen(true)} />
        <ChatLog sendAction={sendAction} />
      </div>
    </div>
  )
}

export default function App() {
  const { myPlayerId, sessionCode, setMyPlayerId, setSessionCode } = useGameStore()

  useEffect(() => {
    const pid = localStorage.getItem('playerId')
    const code = localStorage.getItem('sessionCode')
    if (pid && code) {
      setMyPlayerId(pid)
      setSessionCode(code)
    }
  }, [setMyPlayerId, setSessionCode])

  if (!myPlayerId || !sessionCode) return <Lobby />
  return <Game />
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire all components into App.tsx"
```

---

### Task 7: End-to-End Smoke Test

- [ ] **Step 1: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```
Expected: 0 errors

- [ ] **Step 2: Build production frontend**

```bash
npm run build
```
Expected: `dist/` generated with no errors

- [ ] **Step 3: Full stack Docker test**

```bash
docker-compose up --build
```
Open http://localhost:80. Run the full golden path:
1. Open two browser tabs
2. Tab 1: Create game, note session code
3. Tab 2: Join game with same session code
4. Tab 1: Start game
5. Roll dice in both turns
6. Buy a property
7. End turns until someone lands on it — verify rent is paid
8. Open trade modal, propose a trade
9. Accept trade in other tab
10. Check chat works

- [ ] **Step 4: Final commit**

```bash
git commit --allow-empty -m "chore: phase 4 frontend complete — full game playable"
```
