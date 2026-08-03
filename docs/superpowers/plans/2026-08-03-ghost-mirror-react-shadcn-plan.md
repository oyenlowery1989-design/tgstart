# Ghost Mirror React (shadcn) Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "Not migrated yet" placeholder at `/app/ghost` with the full React Ghost Mirror section — five pages (Home / Chats / Setup / Events / Users) behind one nav item, with an in-page tab strip — sub-project 8 of 9.

**Architecture:** Additive backend + new frontend. `dashboard/routes/ghost_mirror.py` gains five JSON GET endpoints (`/ghost/api/home|chats|setup|events|users`) that run the exact same `execute_query()` queries as the existing Jinja2 routes; the three existing CSRF-protected POST endpoints and `GET /ghost/api/recent_events_v2` are reused unchanged. Frontend adds one page-scoped API module (`lib/ghost-api.ts`), a shared `<GhostTabs>` strip, five page components, and router wiring. Home keeps the classic 3-second live-polling event feed (prepend, cap 200, brief highlight); Chats gets Switch toggles (monitor + 5 core + 6 advanced in an expandable row); Setup gets a per-row backup-destination Select + Save; Events/Users get paginated tables with type filter / search. All page/filter/search state lives in the URL via `useSearchParams` (first use in this rebuild), so back/forward and shareable links behave like the classic `?page=N` pages.

**Tech Stack:** FastAPI + sqlite3 (unchanged patterns), React 19 + TypeScript, Vite, react-router v7 (basename `/app`), shadcn/ui base-ui variant (`@base-ui/react`, `render={...}` never `asChild`), Tailwind.

## Global Constraints

- READ but do NOT modify: the existing routes/helpers in `dashboard/routes/ghost_mirror.py` (`home`, `chats_list`, `setup_page`, `events_list`, `users_list`, `api_toggle`, `api_monitor`, `api_recent_events_v2`, `api_chat_mapping`, `execute_query`, `get_db_connection`, `bump_config`) — new endpoints are appended only. Also do not modify: `dashboard/csrf.py`, `dashboard/templates/ghost/*`, `frontend/src/lib/nav.ts` (the "Ghost Mirror" item at `/ghost` already exists), `frontend/src/lib/nav-match.ts` (its prefix matching already highlights the sidebar for `/ghost/*` sub-routes), `frontend/src/lib/csrf.ts` (reused as-is), `layout.tsx`, `app-sidebar.tsx`.
- Two new shadcn components are required and NOT yet installed (`frontend/src/components/ui/` has neither `switch.tsx` nor `select.tsx` — the design spec's "Select already installed" note is wrong): add both via `npx shadcn@latest add switch select` in Task 3. No other new dependencies.
- House style: page-scoped `lib/ghost-api.ts`; do NOT import from other `*-api.ts` modules; `lib/csrf.ts` is the one sanctioned cross-cutting import. Every fetch helper checks `resp.ok` explicitly and throws a typed `Error`.
- Pagination is page-number based (`?page=N`, matching the backend LIMIT/OFFSET) — no cursors, no infinite scroll.
- Test gates: this repo has NO Python test suite (documented in CLAUDE.md — do not invent pytest) and no frontend test framework. The per-task gates are `venv/bin/python -m py_compile` for Python and `npm run build` (`tsc -b` + Vite) / `npm run lint` (oxlint) for TypeScript, plus a live-browser Playwright-MCP checklist in Task 10.
- All frontend commands run from `frontend/`; all Python commands from the repo root using `venv/bin/python`.
- Commit after every task with the message given in that task.

---

### Task 1: Backend JSON API — five additive GET endpoints

**Files:**
- Modify: `dashboard/routes/ghost_mirror.py` (append only, after `api_chat_mapping`)

**Interfaces:**
- `GET /ghost/api/home` → `{monitored_count, message_count, event_count, failures, recent_events, config_bump, schema_version}`
- `GET /ghost/api/chats?page=N` → `{chats, page, total_pages, total_chats}`
- `GET /ghost/api/setup?q=...` → `{chats, destinations, query}`
- `GET /ghost/api/events?page=N&type=...` → `{events, page, total_pages, total_events, type_filter}`
- `GET /ghost/api/users?page=N&q=...` → `{users, page, total_pages, total_users, query}`

Each body is a copy of its Jinja route's data-building code (same queries, same page-size, same `total_pages` arithmetic — including `chats`/`users`' quirky `(total // limit) + 1` without the `max(..., 1)` that `events` has; preserve, don't "fix"). Appending at the end is safe: none of these paths collide with existing routes (`/api/toggle/...` and `/api/chats/{id}/monitor` are POST-only; `/api/recent_events_v2` is a distinct literal).

**Steps:**

- [ ] Append to the end of `dashboard/routes/ghost_mirror.py` exactly:

```python


# --- JSON API for the React frontend (additive; Jinja2 routes above unchanged) ---

@router.get("/api/home")
async def api_home():
    monitored = execute_query("SELECT COUNT(*) as c FROM chats WHERE monitored=1", fetchone=True)
    msgs = execute_query("SELECT COUNT(*) as c FROM messages", fetchone=True)
    events = execute_query("SELECT COUNT(*) as c FROM events", fetchone=True)
    failures = execute_query("""
        SELECT * FROM events
        WHERE event_type IN ('mirror_failed_total', 'mirror_fallback_copy')
        ORDER BY ts DESC LIMIT 5
    """, fetchall=True)
    recent_events = execute_query("SELECT * FROM events ORDER BY ts DESC LIMIT 10", fetchall=True)
    bump = execute_query("SELECT value FROM config_meta WHERE key='config_bump'", fetchone=True)
    return {
        "monitored_count": monitored['c'] if monitored else 0,
        "message_count": msgs['c'] if msgs else 0,
        "event_count": events['c'] if events else 0,
        "failures": failures,
        "recent_events": recent_events,
        "config_bump": bump['value'] if bump else "0",
        "schema_version": "3",
    }


@router.get("/api/chats")
async def api_chats(page: int = 1):
    limit = 20
    offset = (page - 1) * limit
    total = execute_query("SELECT COUNT(*) as c FROM chats", fetchone=True)['c']
    query = """
        SELECT c.*,
               cfg.toggle_mirror_new, cfg.toggle_log_new,
               cfg.toggle_edits, cfg.toggle_deletes, cfg.toggle_joins,
               cfg.toggle_admin, cfg.toggle_restrict, cfg.toggle_invites, cfg.toggle_bots, cfg.toggle_bio_worker,
               cfg.toggle_reactions
        FROM chats c
        LEFT JOIN config cfg ON c.chat_id = cfg.chat_id
        ORDER BY c.title ASC
        LIMIT ? OFFSET ?
    """
    chats = execute_query(query, (limit, offset), fetchall=True)
    total_pages = (total // limit) + 1
    return {"chats": chats, "page": page, "total_pages": total_pages, "total_chats": total}


@router.get("/api/setup")
async def api_setup(q: str = ""):
    where = ""
    params = []
    if q:
        where = "WHERE title LIKE ? OR chat_id LIKE ?"
        wild = f"%{q}%"
        params = [wild, wild]
    chats = execute_query(f"SELECT * FROM chats {where} ORDER BY monitored DESC, title ASC", tuple(params), fetchall=True)
    destinations = execute_query(
        "SELECT chat_id, title FROM chats WHERE type IN ('channel', 'supergroup', 'group') ORDER BY title ASC",
        fetchall=True,
    )
    return {"chats": chats, "destinations": destinations, "query": q}


@router.get("/api/events")
async def api_events(page: int = 1, type: str = ""):
    limit = 50
    offset = (page - 1) * limit
    params = []
    where_clause = ""
    if type:
        where_clause = "WHERE event_type = ?"
        params.append(type)
    total = execute_query(f"SELECT COUNT(*) as c FROM events {where_clause}", tuple(params), fetchone=True)['c']
    params.extend([limit, offset])
    events = execute_query(f"SELECT * FROM events {where_clause} ORDER BY ts DESC LIMIT ? OFFSET ?", tuple(params), fetchall=True)
    total_pages = max((total // limit) + 1, 1)
    return {"events": events, "page": page, "total_pages": total_pages, "total_events": total, "type_filter": type}


@router.get("/api/users")
async def api_users(page: int = 1, q: str = ""):
    limit = 50
    offset = (page - 1) * limit
    where = ""
    params = []
    if q:
        where = "WHERE username LIKE ? OR first_name LIKE ? OR user_id = ?"
        wild = f"%{q}%"
        params = [wild, wild, q if q.isdigit() else -1]
    total = execute_query(f"SELECT COUNT(*) as c FROM users {where}", tuple(params), fetchone=True)['c']
    params.extend([limit, offset])
    users = execute_query(f"SELECT * FROM users {where} ORDER BY last_seen DESC LIMIT ? OFFSET ?", tuple(params), fetchall=True)
    total_pages = (total // limit) + 1
    return {"users": users, "page": page, "total_pages": total_pages, "total_users": total, "query": q}
```

- [ ] Test gate: from the repo root, run `venv/bin/python -m py_compile dashboard/routes/ghost_mirror.py` — must exit 0 with no output. (No pytest in this repo per CLAUDE.md; live curl verification happens in Task 10.)
- [ ] Verify no existing code changed: `git diff dashboard/routes/ghost_mirror.py` shows only appended lines after `api_chat_mapping`.
- [ ] Commit with message: `ghost: additive JSON API endpoints for home/chats/setup/events/users`

---

### Task 2: `lib/ghost-api.ts` — typed API module

**Files:**
- Create: `frontend/src/lib/ghost-api.ts`

**Interfaces:**
- Types: `GhostEvent`, `HomeData`, `GhostChat`, `ChatsData`, `SetupChat`, `Destination`, `SetupData`, `EventsData`, `GhostUser`, `UsersData`, `ToggleKey`
- GET helpers: `fetchHome()`, `fetchChats(page)`, `fetchSetup(q)`, `fetchEvents(page, type)`, `fetchUsers(page, q)`, `fetchRecentEvents(afterTs)` — all throw on non-OK (house style)
- POST helpers (CSRF header via `@/lib/csrf`): `toggleConfig(chatId, key, value)`, `toggleMonitor(chatId, value)`, `saveChatMapping(chatId, monitored, backupChatId)` — all throw on non-OK

**Steps:**

- [ ] Create `frontend/src/lib/ghost-api.ts` with exactly this content:

```ts
// Shared helpers for the Ghost Mirror pages. Backend endpoints live under
// /ghost (no /app prefix — that's only the SPA router basename). The five
// GET endpoints are the new JSON API; the three POSTs and recent_events_v2
// are the pre-existing endpoints the classic Jinja2 pages already used.

import { csrfToken } from "@/lib/csrf";

/** Row from the events table; summary_json is stored as TEXT (a JSON string). */
export type GhostEvent = {
  event_id: string;
  ts: string;
  chat_id: number;
  event_type: string;
  actor_user_id: number | null;
  summary_json: string | null;
};

export type HomeData = {
  monitored_count: number;
  message_count: number;
  event_count: number;
  failures: GhostEvent[];
  recent_events: GhostEvent[];
  config_bump: string;
  schema_version: string;
};

/**
 * chats row LEFT JOINed with config: every toggle_* is null when the chat
 * has no config row yet — treated as off, matching the classic template's
 * truthiness checks. Only fields the UI reads are typed (house convention).
 */
export type GhostChat = {
  chat_id: number;
  title: string | null;
  type: string | null;
  monitored: number;
  backup_chat_id: number | null;
  member_count: number | null;
  toggle_log_new: number | null;
  toggle_mirror_new: number | null;
  toggle_edits: number | null;
  toggle_deletes: number | null;
  toggle_joins: number | null;
  toggle_admin: number | null;
  toggle_restrict: number | null;
  toggle_invites: number | null;
  toggle_bots: number | null;
  toggle_bio_worker: number | null;
  toggle_reactions: number | null;
};

export type ChatsData = {
  chats: GhostChat[];
  page: number;
  total_pages: number;
  total_chats: number;
};

/** Narrowed chats row for the Setup page (no config join there). */
export type SetupChat = {
  chat_id: number;
  title: string | null;
  type: string | null;
  monitored: number;
  backup_chat_id: number | null;
};

export type Destination = { chat_id: number; title: string | null };

export type SetupData = {
  chats: SetupChat[];
  destinations: Destination[];
  query: string;
};

export type EventsData = {
  events: GhostEvent[];
  page: number;
  total_pages: number;
  total_events: number;
  type_filter: string;
};

export type GhostUser = {
  user_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  last_seen: string | null;
  is_bot: number;
};

export type UsersData = {
  users: GhostUser[];
  page: number;
  total_pages: number;
  total_users: number;
  query: string;
};

/** Mirrors valid_keys in dashboard/routes/ghost_mirror.py api_toggle. */
export type ToggleKey =
  | "toggle_log_new"
  | "toggle_mirror_new"
  | "toggle_edits"
  | "toggle_deletes"
  | "toggle_joins"
  | "toggle_admin"
  | "toggle_restrict"
  | "toggle_invites"
  | "toggle_bots"
  | "toggle_bio_worker"
  | "toggle_reactions";

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Failed to load ${url} (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<T>;
}

export function fetchHome(): Promise<HomeData> {
  return getJson("/ghost/api/home");
}

export function fetchChats(page: number): Promise<ChatsData> {
  return getJson(`/ghost/api/chats?page=${page}`);
}

export function fetchSetup(q: string): Promise<SetupData> {
  return getJson(`/ghost/api/setup?q=${encodeURIComponent(q)}`);
}

export function fetchEvents(page: number, type: string): Promise<EventsData> {
  return getJson(`/ghost/api/events?page=${page}&type=${encodeURIComponent(type)}`);
}

export function fetchUsers(page: number, q: string): Promise<UsersData> {
  return getJson(`/ghost/api/users?page=${page}&q=${encodeURIComponent(q)}`);
}

/** API returns events ASC (oldest first), strictly after afterTs when given. */
export function fetchRecentEvents(afterTs: string): Promise<{ events: GhostEvent[] }> {
  const qs = afterTs ? `?after_ts=${encodeURIComponent(afterTs)}` : "";
  return getJson(`/ghost/api/recent_events_v2${qs}`);
}

async function postOrThrow(url: string, body?: unknown): Promise<void> {
  const headers: Record<string, string> = { "X-CSRF-Token": csrfToken() };
  const init: RequestInit = { method: "POST", headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`Action failed (HTTP ${resp.status})`);
  }
}

export function toggleConfig(chatId: number, key: ToggleKey, value: boolean): Promise<void> {
  return postOrThrow(`/ghost/api/toggle/${chatId}/${key}?value=${value ? 1 : 0}`);
}

export function toggleMonitor(chatId: number, value: boolean): Promise<void> {
  return postOrThrow(`/ghost/api/chats/${chatId}/monitor?value=${value ? 1 : 0}`);
}

export function saveChatMapping(
  chatId: number,
  monitored: boolean,
  backupChatId: number | null,
): Promise<void> {
  return postOrThrow("/ghost/api/chat_mapping", {
    chat_id: chatId,
    monitored,
    backup_chat_id: backupChatId,
  });
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0 (module not imported yet; this proves it type-checks).
- [ ] Commit with message: `frontend: ghost-api module with typed GET/POST helpers`

---

### Task 3: shadcn Switch + Select, and the shared `<GhostTabs>` strip

**Files:**
- Create (via CLI): `frontend/src/components/ui/switch.tsx`, `frontend/src/components/ui/select.tsx`
- Create: `frontend/src/components/ghost-tabs.tsx`

**Interfaces:**
- `Switch` — base-ui wrapper, controlled via `checked` / `onCheckedChange`
- `Select`, `SelectTrigger`, `SelectValue`, `SelectContent`, `SelectItem` — controlled via `value` / `onValueChange`
- `export function GhostTabs({ active }: { active: GhostTab })`, `export type GhostTab = "Home" | "Chats" | "Setup" | "Events" | "Users"`

**Steps:**

- [ ] From `frontend/`, run `npx shadcn@latest add switch select` (components.json is already configured: style `base-nova`, base-ui variant).
- [ ] Read both generated files. Confirm the expected API: `Switch` accepts `checked` + `onCheckedChange`; `Select` root accepts `value` + `onValueChange` with `SelectTrigger`/`SelectValue`/`SelectContent`/`SelectItem` exports. The generated files are the source of truth — if base-nova generated different export names or prop signatures, adapt the usages written in Tasks 5–7 to match the generated code (do NOT hand-edit the generated components) and note the deviation in that task's commit message.
- [ ] Create `frontend/src/components/ghost-tabs.tsx` with exactly this content:

```tsx
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

// Mirrors the classic ghost/base.html secondary navbar. Rendered at the top
// of all five Ghost Mirror pages; the sidebar keeps highlighting "Ghost
// Mirror" on every sub-route via nav-match.ts prefix matching.
const TABS = [
  { title: "Home", to: "/ghost" },
  { title: "Chats", to: "/ghost/chats" },
  { title: "Setup", to: "/ghost/setup" },
  { title: "Events", to: "/ghost/events" },
  { title: "Users", to: "/ghost/users" },
] as const;

export type GhostTab = (typeof TABS)[number]["title"];

export function GhostTabs({ active }: { active: GhostTab }) {
  return (
    <nav className="flex gap-1 border-b">
      {TABS.map((tab) => (
        <Link
          key={tab.to}
          to={tab.to}
          className={cn(
            "text-muted-foreground hover:text-foreground -mb-px border-b-2 border-transparent px-3 py-2 text-sm",
            tab.title === active && "border-primary text-foreground font-medium",
          )}
        >
          {tab.title}
        </Link>
      ))}
    </nav>
  );
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: add shadcn switch/select, shared GhostTabs strip`

---

### Task 4: Home page — stat tiles, failures, 3s live event feed

**Files:**
- Create: `frontend/src/pages/ghost-home-page.tsx`

**Interfaces:**
- `export function GhostHomePage()` — named export, house convention

**Behavioral contract (ported from `dashboard/templates/ghost/index.html`'s script):**
- Initial load via `fetchHome()`: 3 stat tiles, failures table (5 rows max, destructive badge with summary truncated to 50 chars), event feed seeded with `recent_events` (newest first), `lastTs` primed from the newest row.
- Every 3000 ms, `fetchRecentEvents(lastTs)` (ASC, strictly after `lastTs`); advance `lastTs` to the newest returned ts; prepend reversed batch so newest is on top; cap feed at 200 rows; highlight new rows for 2 s; poll errors are silent (next tick retries) — all exactly as classic.
- Polling starts only after the initial load succeeds (classic primed `lastTs` server-side; without this guard an empty `after_ts` would fetch the *oldest* events).
- Deliberate simplification vs classic: the yellow-fade highlight becomes a `bg-accent` class held for 2 s then dropped (no CSS transition timing fidelity).

**Steps:**

- [ ] Create `frontend/src/pages/ghost-home-page.tsx` with exactly this content:

```tsx
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchHome,
  fetchRecentEvents,
  type GhostEvent,
  type HomeData,
} from "@/lib/ghost-api";

const POLL_INTERVAL_MS = 3000;
const FEED_MAX_ROWS = 200;
const HIGHLIGHT_MS = 2000;

function summaryText(s: string | null, max: number): string {
  const text = s ?? "";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

export function GhostHomePage() {
  const [data, setData] = useState<HomeData | null>(null);
  const [feed, setFeed] = useState<GhostEvent[]>([]);
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const lastTsRef = useRef("");

  useEffect(() => {
    let cancelled = false;
    fetchHome()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setFeed(d.recent_events);
        lastTsRef.current = d.recent_events[0]?.ts ?? "";
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Classic index.html poller, translated: every 3s fetch events strictly
  // after the newest ts we have (API returns ASC / oldest-first), prepend so
  // the newest ends up on top, cap at 200 rows, highlight new rows briefly.
  // Starts only once the initial load has primed lastTs — an empty after_ts
  // would return the OLDEST events.
  const loaded = data !== null;
  useEffect(() => {
    if (!loaded) return;
    const id = setInterval(() => {
      fetchRecentEvents(lastTsRef.current)
        .then(({ events }) => {
          if (events.length === 0) return;
          const newest = events[events.length - 1];
          if (newest.ts > lastTsRef.current) {
            lastTsRef.current = newest.ts;
          }
          const newestFirst = [...events].reverse();
          setFeed((prev) => [...newestFirst, ...prev].slice(0, FEED_MAX_ROWS));
          const ids = events.map((e) => e.event_id);
          setFreshIds((prev) => new Set([...prev, ...ids]));
          setTimeout(() => {
            setFreshIds((prev) => {
              const next = new Set(prev);
              for (const eventId of ids) next.delete(eventId);
              return next;
            });
          }, HIGHLIGHT_MS);
        })
        .catch(() => {
          // Classic behavior: poll errors are ignored; next tick retries.
        });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [loaded]);

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <GhostTabs active="Home" />
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-4">
        <GhostTabs active="Home" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Home" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard Overview</h1>
        <Badge variant="secondary">
          v{data.schema_version} | Bump: {data.config_bump}
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-semibold">{data.monitored_count}</div>
            <div className="text-muted-foreground text-sm">Monitored Chats</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-semibold">{data.message_count}</div>
            <div className="text-muted-foreground text-sm">Messages Logged</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-semibold">{data.event_count}</div>
            <div className="text-muted-foreground text-sm">Total Events</div>
          </CardContent>
        </Card>
      </div>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Recent Critical Issues</h2>
        {data.failures.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time (UTC)</TableHead>
                <TableHead>Chat ID</TableHead>
                <TableHead>Error</TableHead>
                <TableHead>Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.failures.map((f) => (
                <TableRow key={f.event_id}>
                  <TableCell>{f.ts}</TableCell>
                  <TableCell>{f.chat_id}</TableCell>
                  <TableCell>
                    <Badge variant="destructive">
                      {summaryText(f.summary_json, 50)}
                    </Badge>
                  </TableCell>
                  <TableCell>{f.event_type}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-center text-green-600">
            No recent critical failures.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Latest Events</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Chat</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Summary</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {feed.map((e) => (
              <TableRow
                key={e.event_id}
                className={
                  freshIds.has(e.event_id)
                    ? "bg-accent transition-colors"
                    : "transition-colors"
                }
              >
                <TableCell>{e.ts}</TableCell>
                <TableCell>{e.chat_id}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{e.event_type}</Badge>
                </TableCell>
                <TableCell>{e.actor_user_id ?? "None"}</TableCell>
                <TableCell className="max-w-96 break-all whitespace-normal">
                  {summaryText(e.summary_json, 80)}
                </TableCell>
              </TableRow>
            ))}
            {feed.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  No events yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <div className="mt-2">
          <Link
            to="/ghost/events"
            className="text-muted-foreground hover:text-foreground text-sm underline underline-offset-3"
          >
            View All Events &raquo;
          </Link>
        </div>
      </section>
    </div>
  );
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0 (page not routed yet; proves it type-checks against ghost-api and the ui components).
- [ ] Commit with message: `frontend: Ghost Mirror home page with 3s live event feed`

---

### Task 5: Chats page — Switch toggles, expandable Advanced row, pagination

**Files:**
- Create: `frontend/src/pages/ghost-chats-page.tsx`

**Interfaces:**
- `export function GhostChatsPage()`

**Behavioral contract (from `ghost/chats.html` + `ghost/base.html` script):**
- `?page=N` via `useSearchParams` (default 1); Prev/Next buttons write it back; "Page X of Y" between them.
- Per row: monitor Switch, then 5 core config Switches (Log New / Mirror New / Log Edits / Log Deletes / Log Joins — same column order as classic), gear button toggling an in-place Advanced row (`useState<Set<number>>`) with 6 labeled Switches (Admin / Restrict / Invites / Bots / Bio / Reactions).
- Toggle handlers flip optimistically, then POST; on failure show a destructive Alert and refetch the page to resync (classic did `window.location.reload()` on failure).

**Steps:**

- [ ] Create `frontend/src/pages/ghost-chats-page.tsx` with exactly this content:

```tsx
import { Fragment, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Settings2 } from "lucide-react";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchChats,
  toggleConfig,
  toggleMonitor,
  type ChatsData,
  type GhostChat,
  type ToggleKey,
} from "@/lib/ghost-api";

const CORE_TOGGLES: { key: ToggleKey; label: string }[] = [
  { key: "toggle_log_new", label: "Log New" },
  { key: "toggle_mirror_new", label: "Mirror New" },
  { key: "toggle_edits", label: "Log Edits" },
  { key: "toggle_deletes", label: "Log Deletes" },
  { key: "toggle_joins", label: "Log Joins" },
];

const ADVANCED_TOGGLES: { key: ToggleKey; label: string }[] = [
  { key: "toggle_admin", label: "Admin" },
  { key: "toggle_restrict", label: "Restrict" },
  { key: "toggle_invites", label: "Invites" },
  { key: "toggle_bots", label: "Bots" },
  { key: "toggle_bio_worker", label: "Bio" },
  { key: "toggle_reactions", label: "Reactions" },
];

export function GhostChatsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const [data, setData] = useState<ChatsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    try {
      setData(await fetchChats(page));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [page]);

  useEffect(() => {
    setData(null);
    void load();
  }, [load]);

  function patchChat(chatId: number, patch: Partial<GhostChat>) {
    setData((prev) =>
      prev
        ? {
            ...prev,
            chats: prev.chats.map((c) =>
              c.chat_id === chatId ? { ...c, ...patch } : c,
            ),
          }
        : prev,
    );
  }

  // Optimistic flip; on failure surface the error and resync from the server
  // (the classic page reloaded the whole window on a failed toggle).
  async function handleConfig(chatId: number, key: ToggleKey, value: boolean) {
    patchChat(chatId, { [key]: value ? 1 : 0 } as Partial<GhostChat>);
    try {
      await toggleConfig(chatId, key, value);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      void load();
    }
  }

  async function handleMonitor(chatId: number, value: boolean) {
    patchChat(chatId, { monitored: value ? 1 : 0 });
    try {
      await toggleMonitor(chatId, value);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      void load();
    }
  }

  function toggleExpanded(chatId: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(chatId)) {
        next.delete(chatId);
      } else {
        next.add(chatId);
      }
      return next;
    });
  }

  function goto(p: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(p));
    setSearchParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Chats" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Chats Management</h1>
        {data && <Badge variant="secondary">Total: {data.total_chats}</Badge>}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Monitor</TableHead>
                <TableHead>Title (Type)</TableHead>
                <TableHead>Backup Chat</TableHead>
                <TableHead>Members</TableHead>
                {CORE_TOGGLES.map((t) => (
                  <TableHead key={t.key}>{t.label}</TableHead>
                ))}
                <TableHead>Adv</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.chats.map((c) => (
                <Fragment key={c.chat_id}>
                  <TableRow>
                    <TableCell>
                      <Switch
                        checked={c.monitored === 1}
                        onCheckedChange={(checked) =>
                          void handleMonitor(c.chat_id, checked)
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{c.title}</div>
                      <div className="text-muted-foreground text-xs">
                        {c.type} | ID: {c.chat_id}
                      </div>
                    </TableCell>
                    <TableCell>{c.backup_chat_id}</TableCell>
                    <TableCell>{c.member_count}</TableCell>
                    {CORE_TOGGLES.map((t) => (
                      <TableCell key={t.key}>
                        <Switch
                          checked={!!c[t.key]}
                          onCheckedChange={(checked) =>
                            void handleConfig(c.chat_id, t.key, checked)
                          }
                        />
                      </TableCell>
                    ))}
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label="Advanced toggles"
                        onClick={() => toggleExpanded(c.chat_id)}
                      >
                        <Settings2 />
                      </Button>
                    </TableCell>
                  </TableRow>
                  {expanded.has(c.chat_id) && (
                    <TableRow className="bg-muted/50">
                      <TableCell colSpan={10}>
                        <div className="flex flex-wrap items-center gap-6 px-2 py-1">
                          <span className="font-medium">Advanced:</span>
                          {ADVANCED_TOGGLES.map((t) => (
                            <label
                              key={t.key}
                              className="flex items-center gap-2 text-sm"
                            >
                              {t.label}
                              <Switch
                                checked={!!c[t.key]}
                                onCheckedChange={(checked) =>
                                  void handleConfig(c.chat_id, t.key, checked)
                                }
                              />
                            </label>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))}
              {data.chats.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} className="text-muted-foreground">
                    No chats.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goto(page - 1)}
            >
              &laquo; Prev
            </Button>
            <span className="text-muted-foreground text-sm">
              Page {data.page} of {data.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => goto(page + 1)}
            >
              Next &raquo;
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: Ghost chats page with monitor/config switches and advanced row`

---

### Task 6: Setup page — chat→backup mapping with per-row Save

**Files:**
- Create: `frontend/src/pages/ghost-setup-page.tsx`

**Interfaces:**
- `export function GhostSetupPage()`
- Local `SetupRow({ chat, destinations })` child component holding per-row edit state

**Behavioral contract (from `ghost/setup.html`):**
- `?q=` title filter via `useSearchParams`; Input + Filter button submits it (empty clears the param).
- Each row: monitor Switch, source title + id, type badge, backup-destination Select (self excluded, `"none"` sentinel for no backup), computed status badge (`Saving...` / `Error` / `No Backup Set!` when monitored without backup / `Active` / `Inactive`), Save button calling `saveChatMapping`.
- Deliberate simplifications vs classic: the 500 ms post-save status delay is dropped; rows are keyed `${q}:${chat_id}` so per-row draft state resets on refilter (classic reset via full page load).

**Steps:**

- [ ] Create `frontend/src/pages/ghost-setup-page.tsx` with exactly this content:

```tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchSetup,
  saveChatMapping,
  type Destination,
  type SetupChat,
  type SetupData,
} from "@/lib/ghost-api";

type SaveState = "idle" | "saving" | "error";

function SetupRow({
  chat,
  destinations,
}: {
  chat: SetupChat;
  destinations: Destination[];
}) {
  const [monitored, setMonitored] = useState(chat.monitored === 1);
  const [backup, setBackup] = useState<number | null>(chat.backup_chat_id);
  const [saveState, setSaveState] = useState<SaveState>("idle");

  async function save() {
    setSaveState("saving");
    try {
      await saveChatMapping(chat.chat_id, monitored, backup);
      setSaveState("idle");
    } catch {
      setSaveState("error");
    }
  }

  let status: React.ReactNode;
  if (saveState === "saving") {
    status = <Badge variant="secondary">Saving...</Badge>;
  } else if (saveState === "error") {
    status = <Badge variant="destructive">Error</Badge>;
  } else if (monitored && backup === null) {
    status = <Badge className="bg-yellow-500 text-black">No Backup Set!</Badge>;
  } else if (monitored) {
    status = <Badge className="bg-green-600 text-white">Active</Badge>;
  } else {
    status = <span className="text-muted-foreground">Inactive</span>;
  }

  return (
    <TableRow>
      <TableCell className="text-center">
        <Switch
          checked={monitored}
          onCheckedChange={(checked) => setMonitored(checked)}
        />
      </TableCell>
      <TableCell>
        <div className="font-medium">{chat.title}</div>
        <div className="text-muted-foreground text-xs">{chat.chat_id}</div>
      </TableCell>
      <TableCell>
        <Badge variant="secondary">{chat.type}</Badge>
      </TableCell>
      <TableCell>
        <Select
          value={backup === null ? "none" : String(backup)}
          onValueChange={(v) =>
            setBackup(String(v) === "none" ? null : Number(v))
          }
        >
          <SelectTrigger className="w-full max-w-72">
            <SelectValue placeholder="-- No Backup / Select --" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">-- No Backup / Select --</SelectItem>
            {destinations
              .filter((d) => d.chat_id !== chat.chat_id)
              .map((d) => (
                <SelectItem key={d.chat_id} value={String(d.chat_id)}>
                  {d.title} ({d.chat_id})
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>{status}</TableCell>
      <TableCell>
        <Button size="sm" disabled={saveState === "saving"} onClick={() => void save()}>
          Save
        </Button>
      </TableCell>
    </TableRow>
  );
}

export function GhostSetupPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const [qInput, setQInput] = useState(q);
  const [data, setData] = useState<SetupData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setQInput(q), [q]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchSetup(q)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [q]);

  function submitFilter(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = qInput.trim();
    setSearchParams(trimmed ? { q: trimmed } : {});
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Setup" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Setup &amp; Mapping</h1>
        {data && (
          <Badge variant="secondary">Total Sources: {data.chats.length}</Badge>
        )}
      </div>

      <form onSubmit={submitFilter} className="flex items-center gap-2">
        <Input
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          placeholder="Filter by Title..."
          className="max-w-64"
        />
        <Button type="submit" variant="outline">
          Filter
        </Button>
      </form>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Monitor</TableHead>
              <TableHead>Source Chat</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Backup Destination</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.chats.map((chat) => (
              <SetupRow
                key={`${q}:${chat.chat_id}`}
                chat={chat}
                destinations={data.destinations}
              />
            ))}
            {data.chats.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground">
                  No chats match.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: Ghost setup page with backup mapping and per-row save`

---

### Task 7: Events page — paginated log with type filter

**Files:**
- Create: `frontend/src/pages/ghost-events-page.tsx`

**Interfaces:**
- `export function GhostEventsPage()`

**Behavioral contract (from `ghost/events.html`):** `?page=N&type=...` via `useSearchParams`; the six classic filter options plus "All Events"; changing the filter drops `page` (classic's form submitted only `type`); Prev/Next preserve `type`; event_id shown truncated to 8 chars; summary shown as a code block.

**Steps:**

- [ ] Create `frontend/src/pages/ghost-events-page.tsx` with exactly this content:

```tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchEvents, type EventsData } from "@/lib/ghost-api";

// Same six options as the classic events.html filter form.
const EVENT_TYPES = [
  { value: "message_new", label: "New Message" },
  { value: "message_edit", label: "Edits" },
  { value: "message_delete", label: "Deletes" },
  { value: "user_join", label: "Joins" },
  { value: "user_leave", label: "Leaves" },
  { value: "mirror_failed_total", label: "Failures" },
];

export function GhostEventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const typeFilter = searchParams.get("type") ?? "";
  const [data, setData] = useState<EventsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchEvents(page, typeFilter)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [page, typeFilter]);

  function setType(value: string) {
    // Changing the filter resets to page 1 (classic form dropped ?page too).
    setSearchParams(value === "all" ? {} : { type: value });
  }

  function goto(p: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(p));
    setSearchParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Events" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Events Log</h1>
        {data && (
          <Badge variant="secondary">Total Events: {data.total_events}</Badge>
        )}
      </div>

      <Select
        value={typeFilter === "" ? "all" : typeFilter}
        onValueChange={(v) => setType(String(v))}
      >
        <SelectTrigger className="max-w-56">
          <SelectValue placeholder="All Events" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Events</SelectItem>
          {EVENT_TYPES.map((t) => (
            <SelectItem key={t.value} value={t.value}>
              {t.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event ID</TableHead>
                <TableHead>Time (UTC)</TableHead>
                <TableHead>Chat ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.events.map((e) => (
                <TableRow key={e.event_id}>
                  <TableCell className="text-muted-foreground text-xs">
                    {e.event_id.slice(0, 8)}
                  </TableCell>
                  <TableCell>{e.ts}</TableCell>
                  <TableCell>{e.chat_id}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{e.event_type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-96">
                    <code className="text-xs break-all whitespace-pre-wrap">
                      {e.summary_json}
                    </code>
                  </TableCell>
                </TableRow>
              ))}
              {data.events.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    No events.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goto(page - 1)}
            >
              &laquo; Prev
            </Button>
            <span className="text-muted-foreground text-sm">
              Page {data.page} of {data.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => goto(page + 1)}
            >
              Next &raquo;
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: Ghost events page with type filter and pagination`

---

### Task 8: Users page — paginated directory with search

**Files:**
- Create: `frontend/src/pages/ghost-users-page.tsx`

**Interfaces:**
- `export function GhostUsersPage()`

**Behavioral contract (from `ghost/users.html`):** `?page=N&q=...` via `useSearchParams`; search Input + button (submits `q`, drops `page` — classic's form submitted only `q`); Prev/Next preserve `q`; username shown as `@name` or an em-dash; is_bot renders BOT (yellow) / USER (green) badges.

**Steps:**

- [ ] Create `frontend/src/pages/ghost-users-page.tsx` with exactly this content:

```tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchUsers, type UsersData } from "@/lib/ghost-api";

export function GhostUsersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const q = searchParams.get("q") ?? "";
  const [qInput, setQInput] = useState(q);
  const [data, setData] = useState<UsersData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setQInput(q), [q]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchUsers(page, q)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [page, q]);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = qInput.trim();
    // Search resets to page 1 (classic form submitted only q).
    setSearchParams(trimmed ? { q: trimmed } : {});
  }

  function goto(p: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(p));
    setSearchParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Users" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">User Directory</h1>
        {data && (
          <Badge variant="secondary">Total Users: {data.total_users}</Badge>
        )}
      </div>

      <form onSubmit={submitSearch} className="flex items-center gap-2">
        <Input
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          placeholder="Search username, ID or name..."
          className="max-w-72"
        />
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User ID</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>First Name</TableHead>
                <TableHead>Last Name</TableHead>
                <TableHead>Last Seen</TableHead>
                <TableHead>Bot?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.users.map((u) => (
                <TableRow key={u.user_id}>
                  <TableCell>{u.user_id}</TableCell>
                  <TableCell>
                    {u.username ? `@${u.username}` : "—"}
                  </TableCell>
                  <TableCell>{u.first_name}</TableCell>
                  <TableCell>{u.last_name}</TableCell>
                  <TableCell>{u.last_seen}</TableCell>
                  <TableCell>
                    {u.is_bot ? (
                      <Badge className="bg-yellow-500 text-black">BOT</Badge>
                    ) : (
                      <Badge className="bg-green-600 text-white">USER</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {data.users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-muted-foreground">
                    No users found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goto(page - 1)}
            >
              &laquo; Prev
            </Button>
            <span className="text-muted-foreground text-sm">
              Page {data.page} of {data.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => goto(page + 1)}
            >
              Next &raquo;
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: Ghost users page with search and pagination`

---

### Task 9: Router wiring — five routes, mark `/ghost` migrated

**Files:**
- Modify: `frontend/src/main.tsx`

**Interfaces:** none new — five route entries plus `"/ghost"` appended to `MIGRATED_URLS`. Only the bare nav-item URL `/ghost` goes into `MIGRATED_URLS` (that array only excludes nav items from the `NotMigratedPage` mapping); sub-routes like `/ghost/chats` are separate router entries reached via links — same pattern as `/groups/:groupId/users` and `/sessions/login`. Do NOT touch `nav.ts` (item exists) or `nav-match.ts` (prefix matching already highlights the sidebar on sub-routes).

**Steps:**

- [ ] Replace the full content of `frontend/src/main.tsx` with exactly:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";

import "./index.css";
import { Layout } from "@/components/layout";
import { NotMigratedPage } from "@/components/not-migrated-page";
import { ALL_NAV_ITEMS } from "@/lib/nav";
import { ChatsPage } from "@/pages/chats-page";
import { GhostChatsPage } from "@/pages/ghost-chats-page";
import { GhostEventsPage } from "@/pages/ghost-events-page";
import { GhostHomePage } from "@/pages/ghost-home-page";
import { GhostSetupPage } from "@/pages/ghost-setup-page";
import { GhostUsersPage } from "@/pages/ghost-users-page";
import { GroupUsersPage } from "@/pages/group-users-page";
import { ReplyPage } from "@/pages/reply-page";
import { ScrapePage } from "@/pages/scrape-page";
import { SessionsLoginPhonePage } from "@/pages/sessions-login-phone-page";
import { SessionsLoginQrPage } from "@/pages/sessions-login-qr-page";
import { SessionsPage } from "@/pages/sessions-page";
import { StatsPage } from "@/pages/stats-page";

// Only bare nav-item URLs belong here (the array excludes nav items from the
// NotMigratedPage mapping); sub-routes like /ghost/chats are separate router
// entries reached via links, same as /groups/:groupId/users.
const MIGRATED_URLS = ["/sessions", "/stats", "/reply", "/chats", "/scrape", "/ghost"];

const router = createBrowserRouter(
  [
    {
      element: <Layout />,
      children: [
        { index: true, element: <Navigate to="/sessions" replace /> },
        { path: "/sessions", element: <SessionsPage /> },
        { path: "/sessions/login", element: <SessionsLoginPhonePage /> },
        { path: "/sessions/login/qr", element: <SessionsLoginQrPage /> },
        { path: "/stats", element: <StatsPage /> },
        { path: "/chats", element: <ChatsPage /> },
        { path: "/groups/:groupId/users", element: <GroupUsersPage /> },
        { path: "/scrape", element: <ScrapePage /> },
        { path: "/reply", element: <ReplyPage /> },
        { path: "/ghost", element: <GhostHomePage /> },
        { path: "/ghost/chats", element: <GhostChatsPage /> },
        { path: "/ghost/setup", element: <GhostSetupPage /> },
        { path: "/ghost/events", element: <GhostEventsPage /> },
        { path: "/ghost/users", element: <GhostUsersPage /> },
        ...ALL_NAV_ITEMS.filter(
          (item) => !MIGRATED_URLS.includes(item.url),
        ).map((item) => ({
          path: item.url,
          element: (
            <NotMigratedPage
              title={item.title}
              fallbackHref={item.fallbackHref ?? item.url}
            />
          ),
        })),
        { path: "*", element: <Navigate to="/sessions" replace /> },
      ],
    },
  ],
  { basename: "/app" },
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
```

- [ ] Test gate: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: wire /ghost routes, exclude Ghost Mirror from NotMigratedPage`

---

### Task 10: Verification — build, lint, py_compile, curl, Playwright-MCP smoke test

**Files:** none created or modified (fix-forward commits only if a defect is found).

**Steps:**

- [ ] From `frontend/`: `npm run build` — exit 0 (also refreshes `frontend/dist`, which the dashboard serves at `/app`).
- [ ] From `frontend/`: `npm run lint` — exit 0 (oxlint).
- [ ] From the repo root: `venv/bin/python -m py_compile dashboard/routes/ghost_mirror.py` — exit 0.
- [ ] Start the dashboard in the background from the repo root: `venv/bin/python dashboard/app.py` (binds `127.0.0.1:8000`). Wait for startup.
- [ ] `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/app/ghost` → `200`.
- [ ] `curl -s http://127.0.0.1:8000/ghost/api/home | venv/bin/python -c 'import json,sys; d=json.load(sys.stdin); assert set(d) >= {"monitored_count","message_count","event_count","failures","recent_events","config_bump","schema_version"}, d.keys(); print("ok")'` → `ok`.
- [ ] `curl -s "http://127.0.0.1:8000/ghost/api/chats?page=1" | venv/bin/python -c 'import json,sys; d=json.load(sys.stdin); assert set(d) >= {"chats","page","total_pages","total_chats"}, d.keys(); print("ok")'` → `ok`; spot-check `/ghost/api/setup`, `/ghost/api/events?page=1`, `/ghost/api/users?page=1` the same way.
- [ ] `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ghost` → `200` (classic Jinja2 page still reachable, unmodified — fallback intact).
- [ ] **Playwright-MCP live-browser smoke checklist** (manual drive against the running server — this repo has no browser test framework; if no Playwright MCP tooling is available, fall back to the curl checks and explicitly note which of the following was NOT covered):
  1. Navigate to `http://127.0.0.1:8000/app/ghost` — tab strip renders (Home active), 3 stat tiles show numbers, sidebar highlights "Ghost Mirror", no console errors.
  2. Stay ~7 s on Home — network log shows `/ghost/api/recent_events_v2?after_ts=...` requests every ~3 s; if the ghost worker is live and produces events, confirm new rows appear at the top with a brief highlight.
  3. Click "Chats" — table renders with switches; flip one core toggle → POST returns 200; hard-reload the page → the toggle persisted; flip it back to restore. Click a gear → Advanced row expands in place with 6 switches; click again → collapses. Click Next/Prev → URL `?page=` and rows change; browser Back returns to the previous page.
  4. Click "Setup" — enter a title fragment, click Filter → URL gets `?q=`, rows narrow. On one row change the backup destination and click Save → status badge updates (Active / No Backup Set!); hard-reload → persisted; restore the original value and Save again.
  5. Click "Events" — pick a type from the filter → URL gets `?type=`, rows filter, page resets to 1; Next/Prev preserve the type in the URL.
  6. Click "Users" — search a known username or ID → URL gets `?q=`, rows filter; clear the search → full list returns; paginate once.
  7. Confirm sidebar still highlights "Ghost Mirror" on every sub-route, and classic `http://127.0.0.1:8000/ghost/chats` still renders the old Jinja2 page.
- [ ] Stop the background dashboard process.
- [ ] No commit for this task unless a defect was found and fixed; commit fixes as `fix(frontend): <short description>` or `fix(ghost): <short description>` and re-run the full sequence.

---

## Self-Review Notes

**Spec coverage map** (spec: `docs/superpowers/specs/2026-08-03-ghost-mirror-react-shadcn-design.md`):
- "Five additive GET endpoints, same shapes as the Jinja routes; recent_events_v2 and the 3 POSTs reused as-is" → Task 1 (queries copied verbatim, including the quirky `(total // limit) + 1` pagination arithmetic) + Task 2 (POST helper URLs match `api_toggle`/`api_monitor`/`api_chat_mapping` exactly, `X-CSRF-Token` via `lib/csrf.ts`).
- "Five routes under /app/ghost, nav item added to MIGRATED_URLS" → Task 9.
- "Shared GhostTabs strip mirroring ghost/base.html navbar" → Task 3.
- "Home keeps the 3s live-polling prepend feed" → Task 4 (contract section maps line-by-line to the classic script: ASC batch, lastTs advance, reverse-prepend, 200-row cap, 2s highlight, silent poll errors).
- "Chats: Switch toggles, expandable Advanced row via `useState<Set<chatId>>`, page-number pagination" → Task 5.
- "Setup: Select destination picker, per-row Save, title filter" → Task 6.
- "Events type filter / Users search via useSearchParams" → Tasks 7–8.
- "Testing: npm run build + lint, py_compile, Playwright live verification of toggle persistence / mapping save / pagination / live feed" → Task 10.
- "Out of scope: POST logic changes, /reply/setup, retiring classic pages, WS for non-Home pages" → Global Constraints; Task 10 verifies classic pages still serve.

**Spec correction incorporated:** the spec claims shadcn `Select` is "already installed from Sessions/Stats" — verified false (`frontend/src/components/ui/` has neither `select.tsx` nor `switch.tsx`); Task 3 installs both and includes a verify-generated-API step since base-nova output is the source of truth.

**Placeholder scan:** every Steps code block is complete literal file content — no `...`, no TODO, no "similar to". Elisions exist only in prose contract sections.

**Type/name consistency:** `ghost-api.ts` exports match every import in Tasks 4–8 (`fetchHome`/`fetchRecentEvents`/`GhostEvent`/`HomeData`; `fetchChats`/`toggleConfig`/`toggleMonitor`/`ChatsData`/`GhostChat`/`ToggleKey`; `fetchSetup`/`saveChatMapping`/`Destination`/`SetupChat`/`SetupData`; `fetchEvents`/`EventsData`; `fetchUsers`/`UsersData`). Page exports (`GhostHomePage` etc.) match Task 9's imports and file names. `GhostTabs` `active` values used ("Home"/"Chats"/"Setup"/"Events"/"Users") are members of `GhostTab`. `toggle_*` union mirrors `valid_keys` in `api_toggle` (11 keys). No `asChild` anywhere; the only `render={...}` candidates (nav links) use plain `Link` styling instead, which is allowed. The one cast (`as Partial<GhostChat>` on a computed-key patch) is annotated in place.

**Deliberate simplifications (all noted inline):** 2s class-swap highlight instead of CSS fade; Setup drops the classic 500ms post-save delay and computes status from local row state; Setup rows keyed `${q}:${chat_id}` to reset drafts on refilter; Events/Users classic 4-color badge palette collapsed to secondary/green/yellow overrides (Sessions precedent).

**Risk register:** (1) base-nova generated Switch/Select API could differ from the assumed `checked`/`onCheckedChange` and `value`/`onValueChange` — Task 3 verifies right after generation, before any page uses them, with explicit adapt-and-note instructions. (2) FastAPI route-order collisions — checked: all five new GET paths are distinct literals, existing `/api/*` overlaps are POST-only. (3) Home poll racing the initial load — guarded by the `loaded` gate (documented, prevents the oldest-events bug the naive port would have).
