# Stats React (shadcn) Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Stats "Not migrated yet" placeholder with a real React page: Group ID/limit form → WebSocket-driven progress bar → summary tiles + two Recharts bar charts, against the existing unchanged backend.

**Architecture:** Pure frontend work inside the existing Vite/React/shadcn shell. One new route `/app/stats` (explicit route in `main.tsx`, excluded from the generic `NotMigratedPage` mapping), one page-scoped API module (`stats-api.ts`) holding types + fetch + `wsUrl`, one page component (`stats-page.tsx`). The backend `GET /api/stats/session` and `WS /api/stats/ws` in `dashboard/routes/stats.py` are reused exactly as-is.

**Tech Stack:** React 19, TypeScript, react-router-dom v7, shadcn/ui (base-ui variant), Tailwind v4, recharts (new dependency), native WebSocket.

## Global Constraints

- NO backend changes — `dashboard/routes/stats.py`, `stats_service.py`, and all WS message shapes stay untouched.
- The old Jinja2 `/stats` page stays reachable and unmodified.
- shadcn here is the **base-ui variant, NOT Radix** — components use `render={<Element/>}`, never `asChild`. After any `npx shadcn add`, verify the generated file contains no `asChild`.
- No test framework — verification is `npm run build` (`tsc -b` type-check) run from `frontend/`.
- Do not import across page modules (no imports from `sessions-api.ts`); duplicate the `wsUrl` helper verbatim into `stats-api.ts`. Hoisting shared helpers is a future sub-project, out of scope.
- Do not modify `frontend/src/lib/nav.ts`, `layout.tsx`, or `app-sidebar.tsx` — `/stats` already exists as a nav item and has no sub-routes, so existing `findActiveNavItem` matching already handles it.
- Group ID input must be `type="text"` (Telegram group IDs are large negative numbers), validated as an integer before parsing.
- Guard all `JSON.parse` of WS `event.data` with try/catch (proactive fix of the deferred minor finding from the Sessions sub-project review).
- The WS endpoint is `/api/stats/ws` (top-level `api_router` prefix `/api/stats` — NOT nested under `/stats`).
- `top_users` / `peak_hours` arrive as JSON arrays-of-arrays (Python tuples): index positions, not named keys.
- `ws_session` may send `{"error": "..."}` with no other keys (no active session) — must be handled explicitly before checking `done`.
- Node v22.23.1, npm 10.9.8. All frontend commands run from `frontend/`.

---

### Task 1: Install recharts and the shadcn Progress component

**Files:**
- `frontend/package.json` (modified by npm)
- `frontend/package-lock.json` (modified by npm)
- `frontend/src/components/ui/progress.tsx` (created by shadcn CLI)

**Interfaces:**
- `Progress` component from `@/components/ui/progress` accepting a `value` prop (0–100 percentage).
- `recharts` importable: `BarChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip`, `ResponsiveContainer`.

**Steps:**

- [ ] Verify recharts is currently absent, then install it:
  ```bash
  cd frontend
  grep recharts package.json || echo "absent, as expected"
  npm install recharts
  grep recharts package.json
  ```
  Expect a `"recharts": "^..."` entry in `dependencies` after install.
- [ ] Add the shadcn Progress component:
  ```bash
  cd frontend
  npx shadcn@latest add progress --overwrite
  ```
- [ ] Verify the generated component is base-ui-safe and exposes `value`:
  ```bash
  grep -c asChild frontend/src/components/ui/progress.tsx || echo "no asChild — OK"
  grep -n "value" frontend/src/components/ui/progress.tsx
  ```
  Expect zero `asChild` occurrences and a `value` prop in the component signature. If `asChild` appears, the wrong (Radix) variant was generated — stop and re-run the add; the project's `components.json` should select the base-ui registry automatically as it did for all prior adds.
- [ ] Build check:
  ```bash
  cd frontend && npm run build
  ```
  Must exit 0.
- [ ] Commit:
  ```bash
  git add frontend/package.json frontend/package-lock.json frontend/src/components/ui/progress.tsx
  git commit -m "frontend: add recharts dependency and shadcn Progress component"
  ```

---

### Task 2: Create `frontend/src/lib/stats-api.ts`

**Files:**
- `frontend/src/lib/stats-api.ts` (new)

**Interfaces:**
- `SessionInfo`, `ScanProgressMessage`, `ScanResult`, `ScanErrorMessage`, `ScanMessage` types
- `fetchSessionInfo(): Promise<SessionInfo>`
- `wsUrl(path: string): string`

**Steps:**

- [ ] Create `frontend/src/lib/stats-api.ts` with exactly this content:
  ```ts
  // Shared helpers for the Stats page. Backend endpoints live under
  // /api/stats (top-level prefix — NOT nested under the /stats page route).
  //
  // wsUrl is intentionally duplicated from sessions-api.ts: page modules do
  // not import from each other. A future sub-project may hoist shared
  // helpers into a common lib/api.ts.

  export type SessionInfo = {
    active_session: string | null;
    all_sessions: string[];
  };

  /** Streaming progress frame. `done` is absent (or false) until the scan finishes. */
  export type ScanProgressMessage = {
    current: number;
    total: number;
    message: string;
    done?: false;
  };

  /**
   * Final frame. `top_users` / `peak_hours` are arrays of tuples (Python
   * tuples serialize as JSON arrays): [name, count, pct] and [hour, count].
   */
  export type ScanResult = {
    current: number;
    total: number;
    message: string;
    done: true;
    top_users: [string, number, number][];
    peak_hours: [number, number][];
    total_scanned: number;
    unique_senders: number;
    busiest_hour: number | null;
  };

  /** Sent by ws_session when there is no active session; has no other keys. */
  export type ScanErrorMessage = {
    error: string;
  };

  export type ScanMessage = ScanProgressMessage | ScanResult | ScanErrorMessage;

  export async function fetchSessionInfo(): Promise<SessionInfo> {
    const resp = await fetch("/api/stats/session");
    if (!resp.ok) {
      throw new Error(`Failed to load session info (HTTP ${resp.status})`);
    }
    return resp.json() as Promise<SessionInfo>;
  }

  export function wsUrl(path: string): string {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}${path}`;
  }
  ```
- [ ] Build check:
  ```bash
  cd frontend && npm run build
  ```
  Must exit 0 (the module is not imported anywhere yet; this only proves it type-checks).
- [ ] Commit:
  ```bash
  git add frontend/src/lib/stats-api.ts
  git commit -m "frontend: stats-api module with WS message types and session fetch"
  ```

---

### Task 3: Create `frontend/src/pages/stats-page.tsx`

**Files:**
- `frontend/src/pages/stats-page.tsx` (new)

**Interfaces:**
- `export function StatsPage()` — the page component, consumed by `main.tsx` in Task 4.
- Consumes from `@/lib/stats-api`: `fetchSessionInfo`, `wsUrl`, `ScanMessage`, `ScanResult`.
- Consumes installed UI: `Alert`/`AlertTitle`/`AlertDescription`, `Button`, `Card` family, `Input`, `Progress`; recharts `ResponsiveContainer`/`BarChart`/`Bar`/`XAxis`/`YAxis`/`Tooltip`.

**Steps:**

- [ ] Create `frontend/src/pages/stats-page.tsx` with exactly this content:
  ```tsx
  import { useEffect, useRef, useState } from "react";
  import {
    Bar,
    BarChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
  } from "recharts";

  import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
  import { Button } from "@/components/ui/button";
  import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
  } from "@/components/ui/card";
  import { Input } from "@/components/ui/input";
  import { Progress } from "@/components/ui/progress";
  import { fetchSessionInfo, wsUrl } from "@/lib/stats-api";
  import type { ScanMessage, ScanResult } from "@/lib/stats-api";

  type ScanProgress = { current: number; total: number; message: string };

  export function StatsPage() {
    const wsRef = useRef<WebSocket | null>(null);
    const [activeSession, setActiveSession] = useState<string | null>(null);
    const [groupId, setGroupId] = useState("");
    const [limit, setLimit] = useState("");
    const [scanning, setScanning] = useState(false);
    const [progress, setProgress] = useState<ScanProgress | null>(null);
    const [result, setResult] = useState<ScanResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      let cancelled = false;
      fetchSessionInfo()
        .then((info) => {
          if (!cancelled) setActiveSession(info.active_session);
        })
        .catch(() => {
          if (!cancelled) setActiveSession(null);
        });
      return () => {
        cancelled = true;
      };
    }, []);

    // Close any in-flight scan socket on unmount.
    useEffect(() => {
      return () => {
        wsRef.current?.close();
        wsRef.current = null;
      };
    }, []);

    function startScan() {
      const trimmedGroupId = groupId.trim();
      if (!/^-?\d+$/.test(trimmedGroupId)) {
        setError("Group ID must be an integer (e.g. -1001234567890)");
        return;
      }
      const trimmedLimit = limit.trim();
      if (trimmedLimit && !/^\d+$/.test(trimmedLimit)) {
        setError("Limit must be a positive integer");
        return;
      }
      setError(null);
      setResult(null);
      setProgress({ current: 0, total: 0, message: "Connecting..." });
      setScanning(true);

      const ws = new WebSocket(wsUrl("/api/stats/ws"));
      wsRef.current = ws;
      ws.onopen = () => {
        // JSON.stringify drops undefined-valued keys, so limit is omitted
        // entirely when blank and the server default (2000) applies.
        ws.send(
          JSON.stringify({
            group_id: Number(trimmedGroupId),
            limit: trimmedLimit ? Number(trimmedLimit) : undefined,
          }),
        );
      };
      ws.onmessage = (event: MessageEvent<string>) => {
        let data: ScanMessage;
        try {
          data = JSON.parse(event.data) as ScanMessage;
        } catch {
          setError("Received an unreadable message from the server");
          setScanning(false);
          ws.close();
          return;
        }
        if ("error" in data) {
          setError(data.error);
          setScanning(false);
          ws.close();
          return;
        }
        if (data.done) {
          setResult(data);
          setScanning(false);
          ws.close();
          return;
        }
        setProgress({
          current: data.current,
          total: data.total,
          message: data.message,
        });
      };
      ws.onerror = () => {
        setError("WebSocket connection failed");
        setScanning(false);
      };
    }

    const progressPct =
      progress && progress.total > 0
        ? Math.round((progress.current / progress.total) * 100)
        : 0;

    const topUsersData =
      result?.top_users.map(([name, count]) => ({ name, count })) ?? [];
    const peakHoursData =
      result?.peak_hours.map(([hour, count]) => ({
        hour: `${String(hour).padStart(2, "0")}:00`,
        count,
      })) ?? [];

    return (
      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Group Stats</CardTitle>
            <CardDescription>
              Scan a group's recent messages for activity stats. Session:{" "}
              {activeSession ?? "none"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {error && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <form
              className="flex flex-wrap gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                startScan();
              }}
            >
              <Input
                type="text"
                inputMode="numeric"
                placeholder="Group ID (e.g. -1001234567890)"
                className="max-w-60"
                value={groupId}
                onChange={(e) => setGroupId(e.target.value)}
                disabled={scanning}
              />
              <Input
                type="text"
                inputMode="numeric"
                placeholder="Limit (default 2000)"
                className="max-w-45"
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
                disabled={scanning}
              />
              <Button type="submit" disabled={scanning || !groupId.trim()}>
                {scanning ? "Scanning..." : "Scan"}
              </Button>
            </form>
            {scanning && progress && (
              <div className="flex flex-col gap-1">
                <Progress value={progressPct} />
                <p className="text-sm text-muted-foreground">
                  {progress.message}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {result && (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardDescription>Total scanned</CardDescription>
                  <CardTitle className="text-2xl">
                    {result.total_scanned}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Unique senders</CardDescription>
                  <CardTitle className="text-2xl">
                    {result.unique_senders}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Busiest hour</CardDescription>
                  <CardTitle className="text-2xl">
                    {result.busiest_hour !== null
                      ? `${String(result.busiest_hour).padStart(2, "0")}:00`
                      : "—"}
                  </CardTitle>
                </CardHeader>
              </Card>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Top Users</CardTitle>
                </CardHeader>
                <CardContent className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topUsersData}>
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="var(--chart-1)" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Peak Hours</CardTitle>
                </CardHeader>
                <CardContent className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={peakHoursData}>
                      <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="var(--chart-2)" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    );
  }
  ```
  Notes for the implementer (context, not extra work): the `"error" in data` check runs before `data.done` because the error frame has no `done`/`current`/`total` keys at all; `--chart-1`/`--chart-2` CSS variables already exist in `frontend/src/index.css`; the `type="text"` inputs are deliberate — Telegram group IDs like `-1001234567890` break `type="number"` UX.
- [ ] Build check:
  ```bash
  cd frontend && npm run build
  ```
  Must exit 0 (the page is not routed yet; this proves it type-checks, including the recharts and Progress imports).
- [ ] Commit:
  ```bash
  git add frontend/src/pages/stats-page.tsx
  git commit -m "frontend: Stats page with WS-driven scan progress, tiles, and bar charts"
  ```

---

### Task 4: Wire the `/stats` route in `main.tsx`

**Files:**
- `frontend/src/main.tsx` (modified)

**Interfaces:**
- New route `{ path: "/stats", element: <StatsPage /> }`; filter predicate now excludes both `/sessions` and `/stats`.

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
  import { SessionsLoginPhonePage } from "@/pages/sessions-login-phone-page";
  import { SessionsLoginQrPage } from "@/pages/sessions-login-qr-page";
  import { SessionsPage } from "@/pages/sessions-page";
  import { StatsPage } from "@/pages/stats-page";

  const MIGRATED_URLS = ["/sessions", "/stats"];

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
- [ ] Do NOT touch `frontend/src/lib/nav.ts`, `frontend/src/components/layout.tsx`, or `frontend/src/components/app-sidebar.tsx`. The `/stats` nav item already exists in `nav.ts` (Data group, `BarChart3` icon), and `findActiveNavItem` (added in the Sessions sub-project) already handles active-state matching for a route with no sub-routes. There is nothing to fix there — verify by reading, not editing.
- [ ] Build check:
  ```bash
  cd frontend && npm run build
  ```
  Must exit 0.
- [ ] Commit:
  ```bash
  git add frontend/src/main.tsx
  git commit -m "frontend: wire /stats route, exclude it from NotMigratedPage mapping"
  ```

---

### Task 5: Smoke test (no code changes expected)

**Files:**
- None modified. Read-only verification of `dashboard/routes/stats.py` behavior and the built frontend.

**Interfaces:** None new.

**Steps:**

- [ ] Fresh production build so `dashboard/app.py` serves the new bundle:
  ```bash
  cd frontend && npm run build
  ```
- [ ] Start the dashboard in the background (from repo root, using the project venv):
  ```bash
  ./venv/bin/python dashboard/app.py
  ```
  Run this via a background process; wait until it logs the uvicorn startup line for `http://127.0.0.1:8000`. Note: auth is loopback-open when `DASHBOARD_PASSWORD` is unset, so local curl needs no credentials; if a password is set in `.env`, add `-u "$DASHBOARD_USER:$DASHBOARD_PASSWORD"` to each curl.
- [ ] Verify endpoints:
  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/app/stats
  curl -s http://127.0.0.1:8000/api/stats/session
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/stats
  ```
  Expect: `200` for `/app/stats`; a JSON body containing both `active_session` and `all_sessions` keys for `/api/stats/session`; `200` for the old Jinja2 `/stats` page (unmodified, still served).
- [ ] Live browser check (same pattern as sub-project 2): if a Playwright/headless-browser tool is available, navigate to `http://127.0.0.1:8000/app/stats` and confirm the page renders the "Group Stats" card with the Group ID input, Limit input, and Scan button, and that the sidebar highlights "Stats". If a real Telegram session and a real group ID are available in the environment, optionally run one scan (small limit, e.g. 50) and confirm the progress bar advances and the three tiles plus two bar charts render on completion — if no session/group is available, that's an environment limitation, note it and move on (the `{error}` Alert appearing when scanning with no active session is itself a valid partial check). If no headless tooling exists at all, fall back to the curl checks above plus a careful read-through of `stats-page.tsx` against the WS message shapes in `dashboard/routes/stats.py`, explicitly noting that a browser check would additionally have covered chart rendering and the progress-bar visuals.
- [ ] Stop the background dashboard process.
- [ ] No commit (nothing changed). If the smoke test surfaced a fix, commit it as:
  ```bash
  git commit -m "frontend: fix Stats page issue found in smoke test"
  ```

---

## Self-Review Notes

**Spec coverage map** (spec: `docs/superpowers/specs/2026-08-02-stats-react-shadcn-design.md`):
- "No backend changes; reuse `GET /api/stats/session` and `WS /api/stats/ws` as-is" → Global Constraints; Tasks 2–3 consume only those two endpoints; Task 5 confirms old `/stats` still 200s.
- "One new frontend route `/app/stats`, filtered out of `NotMigratedPage` mapping" → Task 4.
- "Single page, no sub-routes, no `findActiveNavItem` changes" → Task 4 explicitly forbids touching layout/sidebar/nav.
- "Form → WS progress bar → 3 Card tiles + 2 Recharts bar charts side by side" → Task 3 (tiles grid `sm:grid-cols-3`, charts grid `lg:grid-cols-2`, `ResponsiveContainer` both).
- "New dependency recharts" → Task 1.
- "Error handling: `resp.ok` pattern + WS errors inline like Sessions' QR page" → Task 2 (`fetchSessionInfo` throws on `!resp.ok`), Task 3 (`onerror` Alert, `{error}` frame handled before `done`, guarded `JSON.parse` — proactively fixing the deferred Sessions-review minor).
- "Testing: `npm run build` + curl `/app/stats` + live browser check with reduced-scope fallback" → build-check step in every task; Task 5.

**Placeholder scan:** All code steps contain complete literal file contents or exact commands — no "similar to", no ellipses inside code, no TODOs. `main.tsx` is given as a full-file replacement rather than a diff to avoid ambiguity.

**Type/name consistency:** `ScanMessage = ScanProgressMessage | ScanResult | ScanErrorMessage` discriminates correctly in Task 3's handler: `"error" in data` narrows out `ScanErrorMessage` (the only member with `error`), then `data.done` (optional `false` vs literal `true`) narrows `ScanResult`. Tuple types `[string, number, number][]` / `[number, number][]` match the arrays-of-arrays wire format (index access only, used at `top_users.map(([name, count]) => ...)` — the `pct` third element is intentionally unused, matching the spec's chart definition of name+count). `wsUrl` is byte-identical to `sessions-api.ts`'s copy. Import path `@/lib/stats-api` matches the file created in Task 2; `StatsPage` export name matches Task 4's import. `--chart-1`/`--chart-2` verified present in `frontend/src/index.css`.

**Scope check:** No backend files touched; `nav.ts`/`layout.tsx`/`app-sidebar.tsx` untouched; no session switcher on the Stats page (display-only line, switching stays Sessions' job); no shared `lib/api.ts` hoist; no CSV-download UI (backend mentions `csv_path` only inside the human-readable `message` string, which the page already displays); no test framework introduced.
