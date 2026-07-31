# Stats React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the dashboard's Stats page as a React + Vite + Tailwind single-page app, served by the existing FastAPI backend, as the first migrated page of a modern (non-Jinja2) UI.

**Architecture:** A new `frontend/` Vite+React+Tailwind app builds to `frontend/dist/`, which `dashboard/app.py` serves as static files at `/app` (SPA fallback to `index.html`). A new `/api/stats/*` JSON+WebSocket router (added to the existing `dashboard/routes/stats.py`) reuses `stats_service.group_stats` unchanged. The existing `/stats` Jinja2 page and all other pages are untouched; only the navbar's "Stats" link is repointed to `/app/stats`.

**Tech Stack:** React 18, Vite 5, Tailwind CSS v4 (`@tailwindcss/vite` plugin), Recharts. Backend: existing FastAPI/Telethon stack, no new Python dependencies.

## Global Constraints

- Env var convention: `MAIN_API_ID`/`MAIN_API_HASH` falling back to `API_ID`/`API_HASH` — not touched by this plan (no new Telethon client code).
- No test framework in this repo. Python verification is `python -m py_compile`. Frontend verification is `npm run build` succeeding with no errors (its equivalent of a compile check).
- `dashboard/routes/*.py` use the shared `dashboard.templates_env.render_template` for HTML and `dashboard.ws_utils.ws_session` for websockets — new JSON/WS code in this plan follows the same patterns already used in `dashboard/routes/stats.py`.
- HTTP Basic auth (`dashboard/auth.py::require_auth`) is an app-level dependency already covering every route including websockets — new `/api/*` routes get it automatically via `app = FastAPI(..., dependencies=[Depends(require_auth)])` in `dashboard/app.py`. Do not add a second auth mechanism.
- `dist/` is already in the root `.gitignore` (unanchored, matches `frontend/dist/` too) — do not add a redundant entry. `node_modules/` is not yet ignored — this plan adds it.

---

### Task 1: Scaffold the Vite + React + Tailwind app

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/index.css`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces: a Vite project that builds to `frontend/dist/` via `npm run build`, with Tailwind utility classes available in any component via `className`.

- [ ] **Step 1: Add `node_modules` to `.gitignore`**

Add this block right after the existing `# Virtual environments` section in `.gitignore`:

```
# Frontend (Vite/React) — dist/ already covered by the unanchored dist/ rule above
frontend/node_modules/
```

- [ ] **Step 2: Write `frontend/package.json`**

```json
{
  "name": "telegram-suite-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@vitejs/plugin-react": "^4.3.1",
    "tailwindcss": "^4.0.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 3: Write `frontend/vite.config.js`**

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// base: "/app/" — the built assets are served from dashboard/app.py under
// StaticFiles(directory="frontend/dist"), mounted at /app.
export default defineConfig({
  base: "/app/",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
  },
});
```

- [ ] **Step 4: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Telegram Suite</title>
  </head>
  <body class="bg-slate-950 text-slate-100">
    <div id="root"></div>
    <script type="module" src="/app/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Write `frontend/src/index.css`**

```css
@import "tailwindcss";
```

- [ ] **Step 6: Write `frontend/src/main.jsx`**

```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 7: Write a placeholder `frontend/src/App.jsx`**

```jsx
export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <p className="text-slate-400">Loading...</p>
    </div>
  );
}
```

- [ ] **Step 8: Install dependencies and build**

```bash
cd frontend
npm install
npm run build
```

Expected: `npm install` completes with no errors; `npm run build` prints a Vite build
summary ending in something like `✓ built in <N>ms` and creates `frontend/dist/index.html`
plus a `frontend/dist/assets/` directory. No red error output from either command.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html \
  frontend/src/main.jsx frontend/src/App.jsx frontend/src/index.css \
  frontend/package-lock.json .gitignore
git commit -m "feat(frontend): scaffold Vite + React + Tailwind app"
```

---

### Task 2: Sidebar layout

**Files:**
- Create: `frontend/src/components/Sidebar.jsx`
- Create: `frontend/src/components/Layout.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: nothing from earlier tasks besides the Tailwind/React setup from Task 1
- Produces:
  - `Sidebar` (default export) — renders the grouped nav, no props
  - `Layout` (default export) — props: `{ children }`; renders `Sidebar` plus a main content area wrapping `children`

- [ ] **Step 1: Write `frontend/src/components/Sidebar.jsx`**

```jsx
const NAV_GROUPS = [
  {
    label: "Accounts",
    items: [{ label: "Sessions", href: "/sessions", external: true }],
  },
  {
    label: "Data",
    items: [
      { label: "Chats", href: "/chats", external: true },
      { label: "Groups", href: "/groups", external: true },
      { label: "Scrape", href: "/scrape", external: true },
      { label: "Stats", href: "/app/stats", external: false },
    ],
  },
  {
    label: "Automation",
    items: [
      { label: "Ghost Mirror", href: "/ghost", external: true },
      { label: "Bot Reply", href: "/reply", external: true },
    ],
  },
];

export default function Sidebar() {
  const currentPath = window.location.pathname;
  return (
    <nav className="w-56 shrink-0 bg-slate-900 border-r border-slate-800 min-h-screen px-3 py-4">
      <div className="text-slate-200 font-semibold text-lg px-2 mb-6">
        Telegram Suite
      </div>
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-5">
          <div className="text-slate-500 text-xs uppercase tracking-wide px-2 mb-2">
            {group.label}
          </div>
          {group.items.map((item) => {
            const active = !item.external && currentPath === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                className={
                  "block px-2 py-1.5 rounded text-sm mb-0.5 " +
                  (active
                    ? "bg-slate-800 text-slate-50 border-l-2 border-blue-400 -ml-px pl-2"
                    : "text-slate-300 hover:bg-slate-800 hover:text-slate-50")
                }
              >
                {item.label}
              </a>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/Layout.jsx`**

```jsx
import Sidebar from "./Sidebar.jsx";

export default function Layout({ children }) {
  return (
    <div className="flex bg-slate-950 text-slate-100">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Wire `Layout` into `App.jsx`**

```jsx
import Layout from "./components/Layout.jsx";

export default function App() {
  return (
    <Layout>
      <p className="text-slate-400">Loading...</p>
    </Layout>
  );
}
```

- [ ] **Step 4: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors (same success signal as Task 1 Step 8).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Sidebar.jsx frontend/src/components/Layout.jsx frontend/src/App.jsx
git commit -m "feat(frontend): add grouped sidebar layout"
```

---

### Task 3: Backend — `/api/stats` JSON + WebSocket router

**Files:**
- Modify: `dashboard/services/stats_service.py`
- Modify: `dashboard/routes/stats.py`

**Interfaces:**
- Consumes: `dashboard.state.get_active_session`, `dashboard.state.list_sessions`,
  `dashboard.ws_utils.ws_session` (all existing)
- Produces:
  - `StatsResult` gains two fields: `unique_senders: int`, `busiest_hour: Optional[int]`
    (backward compatible — existing `/stats/ws` handler explicitly selects the fields it
    sends, so this addition doesn't change its output)
  - `api_router = APIRouter(prefix="/api/stats")` in `dashboard/routes/stats.py`, with:
    - `GET /api/stats/session` — returns `{"active_session": str|None, "all_sessions": list[str]}`
    - `WS /api/stats/ws` — same request shape as `/stats/ws` (`{"group_id", "limit"?}`),
      same progress messages, and a final message additionally including
      `"unique_senders"` and `"busiest_hour"`

- [ ] **Step 1: Extend `StatsResult` and `group_stats` in `dashboard/services/stats_service.py`**

Change the `StatsResult` dataclass (currently lines 16-22):

```python
@dataclass
class StatsResult:
    total_scanned: int
    top_users: List[Tuple[str, int, float]]
    peak_hours: List[Tuple[int, int]]
    csv_path: str
    unique_senders: int
    busiest_hour: Optional[int]
```

Change the `return StatsResult(...)` line inside `group_stats` (currently line 60):

```python
            busiest_hour = hours.most_common(1)[0][0] if hours else None
            csv_path = _save_csv(entity, total_scanned, user_msgs, user_names, hours)
            return StatsResult(
                total_scanned=total_scanned, top_users=top_users, peak_hours=peak_hours,
                csv_path=csv_path, unique_senders=len(user_msgs), busiest_hour=busiest_hour,
            )
```

- [ ] **Step 2: Compile-check the service module**

```bash
python -m py_compile dashboard/services/stats_service.py
```

Expected: no output, exit code 0.

- [ ] **Step 3: Add the `api_router` to `dashboard/routes/stats.py`**

Append to the end of `dashboard/routes/stats.py` (after the existing `stats_ws` function):

```python
api_router = APIRouter(prefix="/api/stats")


@api_router.get("/session")
async def api_stats_session(request: Request):
    return {"active_session": get_active_session(request), "all_sessions": list_sessions()}


@api_router.websocket("/ws")
async def api_stats_ws(websocket: WebSocket):
    async with ws_session(websocket) as session_name:
        if not session_name:
            return
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        limit = int(params["limit"]) if params.get("limit") else 2000

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await group_stats(session_name, group_id, limit=limit, progress_cb=progress_cb)
        await websocket.send_json({
            "current": result.total_scanned, "total": result.total_scanned,
            "message": f"Done. Saved {result.csv_path}", "done": True,
            "top_users": result.top_users, "peak_hours": result.peak_hours,
            "total_scanned": result.total_scanned, "unique_senders": result.unique_senders,
            "busiest_hour": result.busiest_hour,
        })
```

This requires `list_sessions` in the existing import line from `dashboard.state` — update it:

```python
from dashboard.state import get_active_session, list_sessions
```

(If that import already includes `list_sessions`, leave it as-is.)

- [ ] **Step 4: Compile-check the route module**

```bash
python -m py_compile dashboard/routes/stats.py
```

Expected: no output, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add dashboard/services/stats_service.py dashboard/routes/stats.py
git commit -m "feat(dashboard): add /api/stats JSON+WS router with unique_senders/busiest_hour"
```

---

### Task 4: Wire the frontend into `dashboard/app.py`

**Files:**
- Modify: `dashboard/app.py`
- Modify: `dashboard/templates/base.html`

**Interfaces:**
- Consumes: `dashboard.routes.stats.api_router` (Task 3), `frontend/dist/` build output (Task 1-2)
- Produces: `/app/*` serves the built SPA (with `index.html` fallback for client-side
  paths like `/app/stats`), `/api/stats/*` is reachable, and the dashboard's navbar
  "Stats" link points at the new page

- [ ] **Step 1: Mount the frontend build and include `api_router` in `dashboard/app.py`**

Replace the existing static mount line and router imports:

```python
# dashboard/app.py — replace the app.mount("/static", ...) line and the router
# import/include block
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

from dashboard.routes import ghost_mirror, sessions, chats, groups, scrape, stats, utilities, bot_reply
app.include_router(ghost_mirror.router)
app.include_router(sessions.router)
app.include_router(chats.router)
app.include_router(groups.router)
app.include_router(scrape.router)
app.include_router(stats.router)
app.include_router(stats.api_router)
app.include_router(utilities.router)
app.include_router(bot_reply.router)

if FRONTEND_DIST.is_dir():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    print(f"[dashboard] {FRONTEND_DIST} not found — run 'npm run build' in frontend/ "
          "to enable the new UI at /app. Falling back to the classic dashboard only.")
```

`StaticFiles(..., html=True)` serves `index.html` for any path under `/app` that isn't a
real file on disk (e.g. `/app/stats`), which is what lets the client-side app render for
that URL — there is no server-side React Router, but this mount config makes `/app/stats`
resolve to the same `index.html` as `/app/`, and the SPA reads `window.location.pathname`
itself (see `Sidebar.jsx`'s `active` check from Task 2).

- [ ] **Step 2: Point the navbar's Stats link at the new page**

In `dashboard/templates/base.html`, change:

```html
<a href="/stats">Stats</a>
```

to:

```html
<a href="/app/stats">Stats</a>
```

- [ ] **Step 3: Full app import check**

```bash
source venv/bin/activate
python -c "
import sys; sys.path.insert(0, '.')
from dashboard import app
print('APP_OK, routes:', len(app.app.routes))
"
```

Expected: `APP_OK, routes: <count>`, no traceback. (If `frontend/dist/` doesn't exist yet
in this environment, the printed fallback message appears on stderr/stdout but the import
still succeeds — the `if FRONTEND_DIST.is_dir()` guard exists exactly so a missing build
doesn't crash the whole dashboard.)

- [ ] **Step 4: Manual smoke test**

```bash
source venv/bin/activate
python dashboard/app.py
```

In a browser, visit `http://127.0.0.1:8000/app/stats`. Expected: page loads showing the
dark sidebar (Accounts/Data/Automation) and "Loading..." placeholder text, no 404, no
blank page. Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py dashboard/templates/base.html
git commit -m "feat(dashboard): serve the new frontend at /app and link Stats to it"
```

---

### Task 5: Stats page — form, WebSocket wiring, progress

**Files:**
- Create: `frontend/src/pages/StatsPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `/api/stats/session` (GET, Task 3), `/api/stats/ws` (WebSocket, Task 3)
- Produces: `StatsPage` (default export, no props) — the full page component, rendered by
  `App.jsx`. Internally tracks scan state and exposes the final result object (shape:
  `{ total_scanned, unique_senders, busiest_hour, top_users, peak_hours }`) via
  `useState`, ready for Task 6 to render as tiles/charts.

- [ ] **Step 1: Write `frontend/src/pages/StatsPage.jsx`**

```jsx
import { useEffect, useState } from "react";

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

export default function StatsPage() {
  const [session, setSession] = useState(null);
  const [groupId, setGroupId] = useState("");
  const [limit, setLimit] = useState("2000");
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch("/api/stats/session")
      .then((r) => r.json())
      .then(setSession)
      .catch(() => setSession({ active_session: null, all_sessions: [] }));
  }, []);

  function startScan() {
    setError(null);
    setResult(null);
    setProgress(0);
    setStatus("Connecting...");
    setScanning(true);

    const ws = new WebSocket(wsUrl("/api/stats/ws"));
    ws.onopen = () => {
      ws.send(JSON.stringify({ group_id: groupId, limit }));
    };
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.error) {
        setError(data.error);
        setScanning(false);
        return;
      }
      setStatus(data.message || "");
      if (data.total) {
        setProgress(Math.round((data.current / data.total) * 100));
      }
      if (data.done) {
        setResult(data);
        setScanning(false);
      }
    };
    ws.onerror = () => {
      setError("WebSocket connection error.");
      setScanning(false);
    };
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Group Analytics</h1>
      <p className="text-slate-500 text-sm mb-4">
        Session:{" "}
        {session?.active_session ? (
          session.active_session
        ) : (
          <a href="/sessions" className="text-blue-400 underline">
            no active session — set one
          </a>
        )}
      </p>

      <div className="flex gap-2 mb-4">
        <input
          className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm flex-1"
          placeholder="Group ID"
          value={groupId}
          onChange={(e) => setGroupId(e.target.value)}
        />
        <input
          className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm w-32"
          placeholder="Limit: 2000"
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
        />
        <button
          className="bg-blue-500 hover:bg-blue-400 disabled:opacity-50 text-white text-sm font-medium px-4 py-1.5 rounded"
          onClick={startScan}
          disabled={scanning || !groupId}
        >
          Scan
        </button>
      </div>

      {(scanning || status) && (
        <div className="mb-4">
          <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-slate-500 text-xs mt-1">{status}</p>
        </div>
      )}

      {error && <p className="text-red-400 text-sm mb-4">Error: {error}</p>}

      {result && (
        <pre className="text-xs text-slate-400 bg-slate-900 p-3 rounded overflow-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
```

(The raw `<pre>` dump of `result` is intentionally temporary — Task 6 replaces it with
tiles and charts, without changing anything above it in this file.)

- [ ] **Step 2: Render `StatsPage` from `App.jsx`**

```jsx
import Layout from "./components/Layout.jsx";
import StatsPage from "./pages/StatsPage.jsx";

export default function App() {
  return (
    <Layout>
      <StatsPage />
    </Layout>
  );
}
```

- [ ] **Step 3: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 4: Manual smoke test**

```bash
python dashboard/app.py
```

Visit `http://127.0.0.1:8000/app/stats`. With an active session set (via `/sessions`),
enter a real group ID you're a member of and click Scan. Expected: progress bar advances,
status text updates, and on completion a raw JSON block appears showing `total_scanned`,
`unique_senders`, `busiest_hour`, `top_users`, `peak_hours`. Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/StatsPage.jsx frontend/src/App.jsx
git commit -m "feat(frontend): wire Stats page form and WebSocket scan progress"
```

---

### Task 6: Stats page — summary tiles and charts

**Files:**
- Create: `frontend/src/components/StatTile.jsx`
- Modify: `frontend/src/pages/StatsPage.jsx`

**Interfaces:**
- Consumes: `result` state shape from Task 5 (`{ total_scanned, unique_senders, busiest_hour, top_users, peak_hours }`)
- Produces: `StatTile` (default export) — props: `{ label: string, value: string|number }`;
  `StatsPage`'s `<pre>` result dump (Task 5 Step 1) is replaced with 3 `StatTile`s plus two
  Recharts bar charts

- [ ] **Step 1: Write `frontend/src/components/StatTile.jsx`**

```jsx
export default function StatTile({ label, value }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded px-4 py-3 flex-1">
      <div className="text-slate-500 text-xs uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className="text-2xl font-semibold text-slate-100">{value}</div>
    </div>
  );
}
```

- [ ] **Step 2: Replace the `<pre>` block in `StatsPage.jsx` with tiles and charts**

Add this import at the top of `frontend/src/pages/StatsPage.jsx`:

```jsx
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import StatTile from "../components/StatTile.jsx";
```

Replace the `{result && (...)}` block (from Task 5 Step 1) with:

```jsx
      {result && (
        <>
          <div className="flex gap-3 mb-4">
            <StatTile label="Total scanned" value={result.total_scanned} />
            <StatTile label="Unique senders" value={result.unique_senders} />
            <StatTile
              label="Busiest hour"
              value={
                result.busiest_hour === null || result.busiest_hour === undefined
                  ? "—"
                  : `${String(result.busiest_hour).padStart(2, "0")}:00`
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded p-3">
              <div className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                Top Users
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={result.top_users.map(([name, count]) => ({ name, count }))}
                  layout="vertical"
                >
                  <XAxis type="number" stroke="#64748b" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#64748b"
                    fontSize={11}
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded p-3">
              <div className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                Peak Hours
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={result.peak_hours.map(([hour, count]) => ({
                    hour: `${String(hour).padStart(2, "0")}:00`,
                    count,
                  }))}
                >
                  <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
```

- [ ] **Step 3: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 4: Manual smoke test**

```bash
python dashboard/app.py
```

Visit `http://127.0.0.1:8000/app/stats`, run a scan against a real group. Expected: after
completion, 3 tiles appear (Total scanned / Unique senders / Busiest hour) followed by two
side-by-side bar charts (Top Users, Peak Hours) rendered in dark theme with blue bars — no
console errors in the browser dev tools. Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StatTile.jsx frontend/src/pages/StatsPage.jsx
git commit -m "feat(frontend): render Stats results as tiles and Recharts bar charts"
```

---

## Self-Review Notes

**Spec coverage:**
- `frontend/` Vite+React+Tailwind, built to static, served by FastAPI at `/api/*` +
  static mount → Tasks 1, 4. ✓
- Grouped sidebar (Accounts/Data/Automation), dark/dense theme → Task 2. ✓
- Stats MVP slice: form, tiles, Top Users + Peak Hours charts (Recharts), WS progress
  kept → Tasks 3, 5, 6. ✓
- Auth: `/api/*` behind existing HTTP Basic (`Depends(require_auth)` at app level,
  unchanged) → Task 4 (no new auth code added, confirmed by reading `dashboard/app.py`
  and `dashboard/auth.py` — the dependency is already app-wide). ✓
- Error handling: WS `{"error": ...}` shape (matches existing `ws_utils.ws_session`
  behavior) surfaced in the UI → Task 5. ✓
- Other pages stay on Jinja2, reachable via full-page links from the new sidebar →
  Task 2 (`external: true` items). ✓
- Testing convention: `python -m py_compile` for Python, `npm run build` for frontend →
  every task. ✓

**Placeholder scan:** no TBD/TODO; every step has literal file contents, not descriptions.

**Type/name consistency check:** `StatsResult.unique_senders`/`busiest_hour` (Task 3)
flow through the `/api/stats/ws` final message (Task 3) into `StatsPage`'s `result` state
(Task 5) and `StatTile` props (Task 6) with the same names throughout. `api_router` is
defined in Task 3 and imported/included in Task 4 with the same name. `Sidebar`/`Layout`
(Task 2) and `StatsPage`/`StatTile` (Tasks 5-6) are all default exports imported by
matching relative paths.

**Scope check:** single subsystem (Stats page migration), matches
`docs/superpowers/specs/2026-07-31-stats-react-frontend-design.md` exactly — no other
pages touched, no backend logic beyond the two additive `StatsResult` fields and the new
router.
