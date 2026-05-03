# Phase 3 — Frontend Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React/TypeScript frontend shell: lobby (create/join), WebSocket connection, full board rendering (11×11 CSS grid), player tokens, and turn controls (roll dice, buy property, end turn).

**Architecture:** Vite + React 18 + TypeScript + Tailwind CSS + Zustand. Single Zustand store updated atomically on every `game_state` WS message. Board renders as an 11×11 CSS grid; player tokens are absolutely positioned over spaces.

**Tech Stack:** Node 20, React 18, TypeScript 5, Vite 5, Tailwind CSS 3, Zustand 4

**Prerequisite:** Phase 1 and Phase 2 backend complete. Backend runs on `localhost:8000` (via `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend`).

---

## File Map

| File | Responsibility |
|------|---------------|
| `frontend/package.json` | Dependencies and scripts |
| `frontend/tsconfig.json` | TypeScript config |
| `frontend/vite.config.ts` | Vite config with `/api` and `/ws` proxy to backend |
| `frontend/tailwind.config.js` | Tailwind config |
| `frontend/postcss.config.js` | PostCSS config |
| `frontend/index.html` | HTML entry point |
| `frontend/src/index.css` | Tailwind base imports |
| `frontend/src/main.tsx` | React root mount |
| `frontend/src/types/game.ts` | All TypeScript interfaces mirroring backend Pydantic models |
| `frontend/src/store/gameStore.ts` | Zustand store: `GameSession` snapshot + `myPlayerId` + `sessionCode` |
| `frontend/src/hooks/useGameWebSocket.ts` | WebSocket lifecycle, reconnect, message dispatch |
| `frontend/src/components/Lobby.tsx` | Create/join forms, sends HTTP + navigates to game |
| `frontend/src/components/Board.tsx` | 11×11 CSS grid container, renders 40 `Space` components |
| `frontend/src/components/Space.tsx` | One board space: name, color bar, price, owner dot, houses |
| `frontend/src/components/PlayerToken.tsx` | Colored circle token, positioned in its space cell |
| `frontend/src/components/TurnControls.tsx` | Roll Dice / Buy / End Turn buttons; sends WS actions |
| `frontend/src/App.tsx` | Root: shows Lobby or game board depending on store state |
| `frontend/Dockerfile` | Production Nginx container (replaces Phase 1 placeholder) |

---

### Task 1: Project Setup — Vite + React + TypeScript + Tailwind

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/index.css`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "chillos-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "zustand": "^4.5.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5",
    "vite": "^5.3.1"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 4: Create `frontend/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

- [ ] **Step 5: Create `frontend/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 6: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CHILLOS</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 8: Create `frontend/src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 9: Install dependencies and verify dev server starts**

```bash
cd frontend && npm install && npm run dev
```
Expected: Vite dev server starts on http://localhost:5173 with no TypeScript errors

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/tailwind.config.js frontend/postcss.config.js frontend/index.html frontend/src/index.css frontend/src/main.tsx frontend/package-lock.json
git commit -m "chore: scaffold frontend with Vite + React + Tailwind + Zustand"
```

---

### Task 2: TypeScript Types (game.ts)

**Files:**
- Create: `frontend/src/types/game.ts`

- [ ] **Step 1: Create `frontend/src/types/game.ts`**

```typescript
export interface Player {
  id: string
  nickname: string
  color: string
  cash: number
  position: number
  properties: string[]
  get_out_of_jail_free: number
  in_jail: boolean
  jail_turns: number
  is_active: boolean
  is_bankrupt: boolean
  last_seen: string
}

export interface Space {
  id: string
  position: number
  name: string
  space_type: 'go' | 'property' | 'railroad' | 'utility' | 'tax' | 'chance' | 'community_chest' | 'jail' | 'free_parking' | 'go_to_jail'
  group: string | null
  price: number
  rent: number[]
  house_cost: number
  hotel_cost: number
  mortgage_value: number
  tax_amount: number
  owner_id: string | null
  houses: number
  has_hotel: boolean
  is_mortgaged: boolean
}

export interface AuctionState {
  property_id: string
  bids: Record<string, number>
  highest_bidder: string | null
  highest_bid: number
  ends_at: string
}

export interface TradeOffer {
  from_player: string
  to_player: string
  give_properties: string[]
  give_cash: number
  give_jail_cards: number
  request_properties: string[]
  request_cash: number
  request_jail_cards: number
  status: 'pending' | 'accepted' | 'rejected'
}

export interface GameSession {
  code: string
  host_id: string
  players: Record<string, Player>
  max_players: number
  status: 'waiting' | 'started' | 'game_over'
  phase: 'turn_roll' | 'turn_action' | 'auction' | 'trading' | 'jail'
  current_player_index: number
  board: Space[]
  dice: [number, number] | null
  doubles_count: number
  auction: AuctionState | null
  pending_trade: TradeOffer | null
  log: string[]
  created_at: string
}

export type ClientAction =
  | { type: 'start_game' }
  | { type: 'roll_dice' }
  | { type: 'end_turn' }
  | { type: 'buy_property' }
  | { type: 'decline_buy' }
  | { type: 'auction_bid'; bid: number }
  | { type: 'build_house'; property_id: string }
  | { type: 'sell_house'; property_id: string }
  | { type: 'mortgage'; property_id: string }
  | { type: 'unmortgage'; property_id: string }
  | { type: 'propose_trade'; trade: Omit<TradeOffer, 'status'> }
  | { type: 'respond_trade'; accept: boolean }
  | { type: 'use_jail_card' }
  | { type: 'pay_jail_fine' }
  | { type: 'chat'; message: string }

export type ServerMessage =
  | { type: 'game_state'; data: GameSession }
  | { type: 'error'; message: string }
  | { type: 'chat'; nickname: string; message: string }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/game.ts
git commit -m "feat: add TypeScript game types"
```

---

### Task 3: Zustand Store (gameStore.ts)

**Files:**
- Create: `frontend/src/store/gameStore.ts`

- [ ] **Step 1: Create `frontend/src/store/gameStore.ts`**

```typescript
import { create } from 'zustand'
import type { GameSession } from '../types/game'

interface GameStore {
  session: GameSession | null
  myPlayerId: string | null
  sessionCode: string | null
  isConnected: boolean
  isReconnecting: boolean
  chatMessages: { nickname: string; message: string }[]
  setSession: (session: GameSession) => void
  setMyPlayerId: (id: string) => void
  setSessionCode: (code: string) => void
  setConnected: (v: boolean) => void
  setReconnecting: (v: boolean) => void
  addChat: (nickname: string, message: string) => void
  reset: () => void
}

export const useGameStore = create<GameStore>((set) => ({
  session: null,
  myPlayerId: null,
  sessionCode: null,
  isConnected: false,
  isReconnecting: false,
  chatMessages: [],
  setSession: (session) => set({ session }),
  setMyPlayerId: (id) => set({ myPlayerId: id }),
  setSessionCode: (code) => set({ sessionCode: code }),
  setConnected: (v) => set({ isConnected: v }),
  setReconnecting: (v) => set({ isReconnecting: v }),
  addChat: (nickname, message) =>
    set((s) => ({ chatMessages: [...s.chatMessages, { nickname, message }] })),
  reset: () =>
    set({
      session: null,
      myPlayerId: null,
      sessionCode: null,
      isConnected: false,
      isReconnecting: false,
      chatMessages: [],
    }),
}))
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/gameStore.ts
git commit -m "feat: add Zustand game store"
```

---

### Task 4: WebSocket Hook (useGameWebSocket.ts)

**Files:**
- Create: `frontend/src/hooks/useGameWebSocket.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useGameWebSocket.ts`**

```typescript
import { useEffect, useRef, useCallback } from 'react'
import { useGameStore } from '../store/gameStore'
import type { ClientAction } from '../types/game'

const MAX_BACKOFF_MS = 5000

export function useGameWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const retryDelay = useRef(1000)
  const retryTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { sessionCode, myPlayerId, setSession, setConnected, setReconnecting, addChat } =
    useGameStore()

  const connect = useCallback(() => {
    if (!sessionCode || !myPlayerId) return
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/${sessionCode}/${myPlayerId}`
    const socket = new WebSocket(wsUrl)
    ws.current = socket

    socket.onopen = () => {
      setConnected(true)
      setReconnecting(false)
      retryDelay.current = 1000
    }

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'game_state') {
        setSession(msg.data)
      } else if (msg.type === 'chat') {
        addChat(msg.nickname, msg.message)
      }
    }

    socket.onclose = () => {
      setConnected(false)
      setReconnecting(true)
      retryTimeout.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, MAX_BACKOFF_MS)
        connect()
      }, retryDelay.current)
    }

    socket.onerror = () => {
      socket.close()
    }
  }, [sessionCode, myPlayerId, setSession, setConnected, setReconnecting, addChat])

  useEffect(() => {
    connect()
    return () => {
      if (retryTimeout.current) clearTimeout(retryTimeout.current)
      ws.current?.close()
    }
  }, [connect])

  const sendAction = useCallback((action: ClientAction) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(action))
    }
  }, [])

  return { sendAction }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useGameWebSocket.ts
git commit -m "feat: add WebSocket hook with exponential backoff"
```

---

### Task 5: Lobby Component

**Files:**
- Create: `frontend/src/components/Lobby.tsx`

- [ ] **Step 1: Create `frontend/src/components/Lobby.tsx`**

```tsx
import { useState } from 'react'
import { useGameStore } from '../store/gameStore'

export function Lobby() {
  const [nickname, setNickname] = useState('')
  const [joinCode, setJoinCode] = useState('')
  const [maxPlayers, setMaxPlayers] = useState(4)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setMyPlayerId, setSessionCode } = useGameStore()

  async function handleCreate() {
    if (!nickname.trim()) return setError('Enter a nickname')
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/create_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: nickname.trim(), max_players: maxPlayers }),
      })
      const data = await res.json()
      if (data.error) return setError(data.error)
      localStorage.setItem('playerId', data.player_id)
      localStorage.setItem('sessionCode', data.session_code)
      setMyPlayerId(data.player_id)
      setSessionCode(data.session_code)
    } catch {
      setError('Failed to create game')
    } finally {
      setLoading(false)
    }
  }

  async function handleJoin() {
    if (!nickname.trim()) return setError('Enter a nickname')
    if (!joinCode.trim()) return setError('Enter a session code')
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/join_game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: nickname.trim(), session_code: joinCode.trim().toUpperCase() }),
      })
      const data = await res.json()
      if (!data.success) return setError(data.error ?? 'Failed to join')
      localStorage.setItem('playerId', data.player_id)
      localStorage.setItem('sessionCode', joinCode.trim().toUpperCase())
      setMyPlayerId(data.player_id)
      setSessionCode(joinCode.trim().toUpperCase())
    } catch {
      setError('Failed to join game')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-green-900 flex items-center justify-center">
      <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <h1 className="text-3xl font-bold text-center mb-6 text-green-800">CHILLOS</h1>
        <input
          className="w-full border rounded-lg px-4 py-2 mb-4 text-lg"
          placeholder="Your nickname"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
        />
        <div className="border rounded-lg p-4 mb-4">
          <h2 className="font-semibold mb-3 text-gray-700">Create Game</h2>
          <div className="flex items-center gap-3 mb-3">
            <label className="text-sm text-gray-600">Max players:</label>
            <select
              className="border rounded px-2 py-1"
              value={maxPlayers}
              onChange={(e) => setMaxPlayers(Number(e.target.value))}
            >
              {[2, 3, 4, 5, 6].map((n) => <option key={n}>{n}</option>)}
            </select>
          </div>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="w-full bg-green-600 text-white rounded-lg py-2 font-semibold hover:bg-green-700 disabled:opacity-50"
          >
            Create Game
          </button>
        </div>
        <div className="border rounded-lg p-4 mb-4">
          <h2 className="font-semibold mb-3 text-gray-700">Join Game</h2>
          <input
            className="w-full border rounded-lg px-4 py-2 mb-3 uppercase tracking-widest"
            placeholder="Session code"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            maxLength={6}
          />
          <button
            onClick={handleJoin}
            disabled={loading}
            className="w-full bg-blue-600 text-white rounded-lg py-2 font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            Join Game
          </button>
        </div>
        {error && <p className="text-red-600 text-center text-sm">{error}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Lobby.tsx
git commit -m "feat: add Lobby component with create/join"
```

---

### Task 6: Board Layout (Board.tsx + Space.tsx)

The board uses an 11×11 CSS grid. Spaces are placed at specific grid positions:
- Bottom row (row 11): spaces 0–10 (right to left: 0=col11, 10=col1)
- Left column (col 1): spaces 11–20 (bottom to top: 11=row10, 20=row1)
- Top row (row 1): spaces 21–30 (left to right: 21=col2, 30=col11)
- Right column (col 11): spaces 31–39 (top to bottom: 31=row2, 39=row10)

**Files:**
- Create: `frontend/src/components/Space.tsx`
- Create: `frontend/src/components/Board.tsx`

- [ ] **Step 1: Create `frontend/src/components/Space.tsx`**

```tsx
import type { Space as SpaceType, GameSession } from '../types/game'

const GROUP_COLORS: Record<string, string> = {
  Brown: 'bg-amber-900',
  'Light Blue': 'bg-sky-300',
  Pink: 'bg-pink-400',
  Orange: 'bg-orange-500',
  Red: 'bg-red-600',
  Yellow: 'bg-yellow-400',
  Green: 'bg-green-600',
  'Dark Blue': 'bg-blue-800',
  Railroad: 'bg-gray-800',
  Utility: 'bg-gray-400',
}

interface SpaceProps {
  space: SpaceType
  session: GameSession
  isCorner?: boolean
}

export function Space({ space, session, isCorner = false }: SpaceProps) {
  const owner = space.owner_id ? session.players[space.owner_id] : null
  const colorBar = space.group ? GROUP_COLORS[space.group] : null

  return (
    <div className={`relative border border-gray-400 bg-white flex flex-col items-center justify-center text-center overflow-hidden ${isCorner ? 'text-xs' : 'text-[9px]'}`}>
      {colorBar && (
        <div className={`absolute top-0 left-0 right-0 h-3 ${colorBar}`} />
      )}
      <span className={`font-semibold leading-tight px-0.5 ${colorBar ? 'mt-3' : ''}`}>
        {space.name}
      </span>
      {space.price > 0 && (
        <span className="text-gray-500">${space.price}</span>
      )}
      {space.tax_amount > 0 && (
        <span className="text-red-600">${space.tax_amount}</span>
      )}
      {space.houses > 0 && (
        <div className="flex gap-0.5 mt-0.5">
          {Array.from({ length: space.houses }).map((_, i) => (
            <div key={i} className="w-2 h-2 bg-green-500 rounded-sm" />
          ))}
        </div>
      )}
      {space.has_hotel && <div className="w-3 h-2 bg-red-500 rounded-sm mt-0.5" />}
      {owner && (
        <div
          className="absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full border border-white"
          style={{ backgroundColor: owner.color }}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/Board.tsx`**

```tsx
import type { GameSession } from '../types/game'
import { Space } from './Space'
import { PlayerToken } from './PlayerToken'

function gridPosition(position: number): { row: number; col: number } {
  if (position <= 10) return { row: 11, col: 11 - position }
  if (position <= 20) return { row: 11 - (position - 10), col: 1 }
  if (position <= 30) return { row: 1, col: position - 19 }
  return { row: position - 29, col: 11 }
}

interface BoardProps {
  session: GameSession
}

export function Board({ session }: BoardProps) {
  const playersByPosition: Record<number, string[]> = {}
  Object.values(session.players).forEach((p) => {
    if (!p.is_bankrupt) {
      if (!playersByPosition[p.position]) playersByPosition[p.position] = []
      playersByPosition[p.position].push(p.id)
    }
  })

  return (
    <div
      className="grid gap-0.5 bg-green-800 p-0.5"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(11, 1fr)',
        gridTemplateRows: 'repeat(11, 1fr)',
        width: '100%',
        aspectRatio: '1',
      }}
    >
      {session.board.map((space) => {
        const { row, col } = gridPosition(space.position)
        const isCorner = [0, 10, 20, 30].includes(space.position)
        const tokens = playersByPosition[space.position] ?? []
        return (
          <div
            key={space.id}
            style={{ gridRow: row, gridColumn: col, position: 'relative' }}
          >
            <Space space={space} session={session} isCorner={isCorner} />
            <div className="absolute bottom-1 left-1 flex gap-0.5 flex-wrap">
              {tokens.map((pid) => (
                <PlayerToken key={pid} player={session.players[pid]} />
              ))}
            </div>
          </div>
        )
      })}
      <div
        style={{ gridRow: '2 / 11', gridColumn: '2 / 11' }}
        className="bg-green-700 flex items-center justify-center"
      >
        <div className="text-white text-center">
          <div className="text-2xl font-bold">CHILLOS</div>
          <div className="text-sm opacity-70">{session.code}</div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Space.tsx frontend/src/components/Board.tsx
git commit -m "feat: add Board 11x11 CSS grid and Space component"
```

---

### Task 7: Player Token Component

**Files:**
- Create: `frontend/src/components/PlayerToken.tsx`

- [ ] **Step 1: Create `frontend/src/components/PlayerToken.tsx`**

```tsx
import type { Player } from '../types/game'

const COLOR_MAP: Record<string, string> = {
  red: '#ef4444',
  blue: '#3b82f6',
  green: '#22c55e',
  yellow: '#eab308',
  purple: '#a855f7',
  orange: '#f97316',
}

interface PlayerTokenProps {
  player: Player
  size?: number
}

export function PlayerToken({ player, size = 14 }: PlayerTokenProps) {
  return (
    <div
      title={player.nickname}
      style={{
        width: size,
        height: size,
        backgroundColor: COLOR_MAP[player.color] ?? player.color,
        borderRadius: '50%',
        border: '2px solid white',
        boxShadow: '0 1px 2px rgba(0,0,0,0.5)',
        flexShrink: 0,
      }}
    />
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PlayerToken.tsx
git commit -m "feat: add PlayerToken component"
```

---

### Task 8: Turn Controls Component

**Files:**
- Create: `frontend/src/components/TurnControls.tsx`

- [ ] **Step 1: Create `frontend/src/components/TurnControls.tsx`**

```tsx
import { useGameStore } from '../store/gameStore'
import type { ClientAction } from '../types/game'

interface TurnControlsProps {
  sendAction: (action: ClientAction) => void
}

export function TurnControls({ sendAction }: TurnControlsProps) {
  const { session, myPlayerId } = useGameStore()
  if (!session || !myPlayerId) return null
  if (session.status === 'waiting') {
    const isHost = session.host_id === myPlayerId
    const playerCount = Object.keys(session.players).length
    return (
      <div className="p-4 bg-white rounded-xl shadow text-center">
        <p className="text-gray-600 mb-3">
          Waiting for players… ({playerCount}/{session.max_players})
        </p>
        <p className="text-sm text-gray-500 mb-3">Session code: <strong className="tracking-widest">{session.code}</strong></p>
        {isHost && playerCount >= 2 && (
          <button
            onClick={() => sendAction({ type: 'start_game' })}
            className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700"
          >
            Start Game
          </button>
        )}
        {isHost && playerCount < 2 && (
          <p className="text-sm text-gray-400">Need at least 2 players to start</p>
        )}
      </div>
    )
  }

  const activePlayers = Object.values(session.players).filter((p) => !p.is_bankrupt)
  const currentPlayer = activePlayers[session.current_player_index % activePlayers.length]
  const isMyTurn = currentPlayer?.id === myPlayerId
  const me = session.players[myPlayerId]
  const currentSpace = session.board[me?.position ?? 0]
  const canBuy = isMyTurn
    && session.phase === 'turn_action'
    && currentSpace
    && currentSpace.owner_id === null
    && ['property', 'railroad', 'utility'].includes(currentSpace.space_type)
    && (me?.cash ?? 0) >= currentSpace.price

  return (
    <div className="p-4 bg-white rounded-xl shadow space-y-3">
      <div className="text-sm text-gray-500">
        {isMyTurn
          ? <span className="text-green-600 font-semibold">Your turn!</span>
          : <span>Waiting for <strong>{currentPlayer?.nickname}</strong></span>}
      </div>
      {session.dice && (
        <div className="flex gap-2 items-center">
          <span className="text-2xl">🎲</span>
          <span className="text-lg font-bold">{session.dice[0]} + {session.dice[1]} = {session.dice[0] + session.dice[1]}</span>
        </div>
      )}
      {isMyTurn && me?.in_jail && session.phase === 'turn_roll' && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-red-600">You are in jail</p>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => sendAction({ type: 'pay_jail_fine' })}
              className="bg-red-500 text-white px-3 py-1.5 rounded text-sm hover:bg-red-600"
            >Pay $50 Fine</button>
            {(me?.get_out_of_jail_free ?? 0) > 0 && (
              <button
                onClick={() => sendAction({ type: 'use_jail_card' })}
                className="bg-yellow-500 text-white px-3 py-1.5 rounded text-sm hover:bg-yellow-600"
              >Use Jail Card</button>
            )}
            <button
              onClick={() => sendAction({ type: 'roll_dice' })}
              className="bg-blue-500 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-600"
            >Roll for Doubles</button>
          </div>
        </div>
      )}
      {isMyTurn && !me?.in_jail && session.phase === 'turn_roll' && (
        <button
          onClick={() => sendAction({ type: 'roll_dice' })}
          className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700"
        >Roll Dice</button>
      )}
      {isMyTurn && session.phase === 'turn_action' && (
        <div className="space-y-2">
          {canBuy && (
            <div className="flex gap-2">
              <button
                onClick={() => sendAction({ type: 'buy_property' })}
                className="flex-1 bg-green-600 text-white py-2 rounded-lg font-semibold hover:bg-green-700 text-sm"
              >Buy {currentSpace.name} (${currentSpace.price})</button>
              <button
                onClick={() => sendAction({ type: 'decline_buy' })}
                className="flex-1 bg-orange-500 text-white py-2 rounded-lg font-semibold hover:bg-orange-600 text-sm"
              >Auction</button>
            </div>
          )}
          <button
            onClick={() => sendAction({ type: 'end_turn' })}
            className="w-full bg-gray-600 text-white py-2 rounded-lg font-semibold hover:bg-gray-700"
          >End Turn</button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TurnControls.tsx
git commit -m "feat: add TurnControls component"
```

---

### Task 9: App.tsx — Wire Everything Together

**Files:**
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/src/App.tsx`**

```tsx
import { useEffect } from 'react'
import { useGameStore } from './store/gameStore'
import { useGameWebSocket } from './hooks/useGameWebSocket'
import { Lobby } from './components/Lobby'
import { Board } from './components/Board'
import { TurnControls } from './components/TurnControls'

function Game() {
  const { session, isReconnecting } = useGameStore()
  const { sendAction } = useGameWebSocket()
  if (!session) return <div className="text-white text-center mt-20">Connecting…</div>
  return (
    <div className="min-h-screen bg-green-900 p-2 flex gap-2">
      {isReconnecting && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 text-center shadow-xl">
            <p className="text-lg font-semibold">Reconnecting…</p>
          </div>
        </div>
      )}
      <div className="flex-1 max-w-2xl">
        <Board session={session} />
      </div>
      <div className="w-72 flex flex-col gap-2">
        <TurnControls sendAction={sendAction} />
        <div className="bg-white rounded-xl p-3 flex-1 overflow-y-auto max-h-64">
          <h3 className="font-semibold text-sm text-gray-600 mb-2">Log</h3>
          {[...session.log].reverse().slice(0, 20).map((entry, i) => (
            <p key={i} className="text-xs text-gray-700 mb-0.5">{entry}</p>
          ))}
        </div>
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

- [ ] **Step 2: Run the dev server and verify full lobby → game flow**

```bash
# Start backend (in one terminal):
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend

# Start frontend dev server (in another terminal):
cd frontend && npm run dev
```

Open http://localhost:5173 in two browser tabs. Create a game in tab 1, join in tab 2, start the game, roll dice — verify board updates in both tabs.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add App.tsx and wire full frontend shell"
```

---

### Task 10: Update Frontend Dockerfile

**Files:**
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: No changes needed** — the placeholder Dockerfile from Phase 1 Task 1 already handles the Vite build correctly. Verify it builds:

```bash
docker build -t chillos-frontend ./frontend
```
Expected: image builds successfully

- [ ] **Step 2: Smoke test production build**

```bash
docker-compose up --build
```
Open http://localhost:80 — lobby should load.

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "chore: phase 3 frontend shell complete"
```
