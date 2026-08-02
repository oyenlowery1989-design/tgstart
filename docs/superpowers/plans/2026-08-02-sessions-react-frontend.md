# Sessions React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "Not migrated yet" placeholder at `/app/sessions` with a real React Sessions page (list/status/switch/delete + phone-login wizard + QR-login page) at full parity with the classic Jinja2 pages.

**Architecture:** One new backend endpoint (`GET /sessions/api/list`) exposes the exact data `sessions_page` already assembles, via a shared `_list_data()` helper (same pattern as Bot Reply's `_queue_data()`); all other existing endpoints (`POST /sessions/active`, `POST /sessions/{name}/delete`, the three phone-login POSTs, and the QR WebSocket) are called from React unchanged. Three new routes are wired directly in `main.tsx` under the existing `/app` basename, and the shell's breadcrumb/sidebar active-matching switches from exact-match to longest-prefix `startsWith` so the two login sub-routes still highlight "Sessions".

**Tech Stack:** FastAPI (backend), React 19 + TypeScript + react-router-dom 7 + shadcn/ui **base-ui variant** + Tailwind v4 + Vite 8 (frontend).

## Global Constraints

- shadcn here is the **base-ui** variant, NOT Radix: composition is `render={<Element />}` — `asChild` does not exist on any component. Any generated or hand-written component code containing `asChild` is a bug.
- No test framework exists: frontend verification is `npm run build` (runs `tsc -b`); backend verification is `python -m py_compile`.
- Do NOT modify `frontend/src/lib/nav.ts` — `/sessions` already exists in `ALL_NAV_ITEMS` and must not be duplicated or removed.
- Do NOT modify `frontend/src/components/not-migrated-page.tsx` — still used by the 7 other placeholder pages.
- Do NOT change `sessions_service.py` login/check/delete logic — reused as-is.
- Do NOT retire the Jinja2 `/sessions`, `/sessions/login`, `/sessions/login/qr` pages — `sessions_page` keeps rendering `sessions.html` with identical template context.
- Every new `fetch` checks `resp.ok` before parsing, and clears stale error state on a successful refetch (the corrected Bot Reply pattern, applied from the start).
- `POST /sessions/active` and `POST /sessions/{name}/delete` return 303 redirects with no JSON body — treat any `resp.ok` as success, never parse the body.
- All frontend routes/navigation use react-router paths without the `/app` prefix (router `basename: "/app"` handles it); all `fetch`/WebSocket URLs use real backend paths (`/sessions/...`, no `/app` prefix).
- Auth is unchanged: `require_auth` is an app-level dependency; the new endpoint needs no auth code.
- `.gitignore` note: sub-project 1 already anchored the `lib/` pattern to `/lib/`, so new files under `frontend/src/lib/` are tracked correctly — this is resolved, not a risk.
- Node v22.23.1, npm 10.9.8. Frontend commands run from `frontend/`; Python commands from the repo root.

---

### Task 1: Backend — `_list_data()` helper and `GET /sessions/api/list`

**Files:**
- Modify: `dashboard/routes/sessions.py`

**Interfaces:**
- Consumes: existing `check_all_sessions()`, `get_active_session(request)`, `list_sessions()` (unchanged).
- Produces: `GET /sessions/api/list` → JSON `{"results": [{"name", "status", "details"}, ...], "active_session": str|null, "all_sessions": [str, ...]}` — consumed by Task 3's `fetchSessionList()` and Task 4's page.

- [ ] **Step 1: Replace the `sessions_page` route in `dashboard/routes/sessions.py`.** Find this exact block:

```python
@router.get("", response_class=HTMLResponse)
async def sessions_page(request: Request):
    results = await check_all_sessions()
    html = _render_template("sessions.html", {
        "request": request,
        "results": results,
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
    })
    return html
```

Replace it with (mirrors `_queue_data()` in `dashboard/routes/bot_reply.py`):

```python
async def _list_data(request: Request) -> dict:
    return {
        "results": await check_all_sessions(),
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
    }


@router.get("", response_class=HTMLResponse)
async def sessions_page(request: Request):
    data = await _list_data(request)
    html = _render_template("sessions.html", {
        "request": request, **data,
        "frontend_available": FRONTEND_AVAILABLE,
    })
    return html


@router.get("/api/list")
async def api_list(request: Request):
    return await _list_data(request)
```

No other changes to the file — imports already cover everything used.
- [ ] **Step 2: Verify compile.** Run from the repo root: `python -m py_compile dashboard/routes/sessions.py` — must exit 0.
- [ ] **Step 3: Commit.** `git add dashboard/routes/sessions.py && git commit -m "sessions: extract _list_data() and add GET /sessions/api/list for the React page"`

---

### Task 2: Frontend — install shadcn `table`, `badge`, `alert`

**Files:**
- Create (via CLI): `frontend/src/components/ui/table.tsx`, `frontend/src/components/ui/badge.tsx`, `frontend/src/components/ui/alert.tsx`

**Interfaces:**
- Produces: `Table/TableHeader/TableBody/TableRow/TableHead/TableCell`, `Badge` (variants: `default`, `secondary`, `destructive`, `outline`), `Alert/AlertTitle/AlertDescription` — consumed by Tasks 4–6.

- [ ] **Step 1: Run the CLI.** From `frontend/`: `npx shadcn@latest add table badge alert --overwrite`. Since the project was initialized with the base-ui variant (`sidebar-07` init), the generated code should already be base-ui style. The CLI output may differ from expectations (sub-project 1 had to adapt CLI output too) — read what it actually created before proceeding.
- [ ] **Step 2: Verify no `asChild`.** Run `grep -rn "asChild" frontend/src/components/ui/table.tsx frontend/src/components/ui/badge.tsx frontend/src/components/ui/alert.tsx` — must return nothing. If any hit appears, replace that composition with the `render={<Element />}` pattern (see `frontend/src/components/not-migrated-page.tsx` for the house style) before continuing.
- [ ] **Step 3: Verify Badge exports a `variant` prop with `secondary` and `destructive` variants** (open `frontend/src/components/ui/badge.tsx` and confirm the cva variants). If the generated names differ, note the actual names — Task 4 uses `variant="destructive"` and `variant="secondary"`.
- [ ] **Step 4: Build check.** From `frontend/`: `npm run build` — must pass (`tsc -b` + vite).
- [ ] **Step 5: Commit.** `git add frontend/src/components/ui/table.tsx frontend/src/components/ui/badge.tsx frontend/src/components/ui/alert.tsx frontend/package.json frontend/package-lock.json && git commit -m "frontend: add shadcn table, badge, alert primitives (base-ui variant)"` (include package files only if the CLI changed them; check `git status` first).

---

### Task 3: Frontend — shared sessions API module

**Files:**
- Create: `frontend/src/lib/sessions-api.ts`

**Interfaces:**
- Consumes: `GET /sessions/api/list` from Task 1.
- Produces: `SessionResult`, `SessionListData` types, `fetchSessionList()`, `postForm()`, `wsUrl()` — consumed by Tasks 4, 5, 6.

- [ ] **Step 1: Create `frontend/src/lib/sessions-api.ts`** with exactly:

```ts
// Shared helpers for the Sessions pages. Backend endpoints live under
// /sessions (no /app prefix — that's only the SPA router basename).

export type SessionResult = {
  name: string;
  status: "ACTIVE" | "INVALID" | "ERROR" | "UNKNOWN";
  details: string;
};

export type SessionListData = {
  results: SessionResult[];
  active_session: string | null;
  all_sessions: string[];
};

export async function fetchSessionList(): Promise<SessionListData> {
  const resp = await fetch("/sessions/api/list");
  if (!resp.ok) {
    throw new Error(`Failed to load sessions (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<SessionListData>;
}

/**
 * POSTs application/x-www-form-urlencoded data. Endpoints that answer with a
 * 303 redirect (switch active, delete) resolve transparently through fetch —
 * resp.ok is the only success signal; never parse their body. Endpoints that
 * answer JSON (the login steps) call resp.json() on the returned Response.
 */
export async function postForm(
  url: string,
  data: Record<string, string>,
): Promise<Response> {
  const resp = await fetch(url, {
    method: "POST",
    body: new URLSearchParams(data),
  });
  if (!resp.ok) {
    throw new Error(`Request failed (HTTP ${resp.status})`);
  }
  return resp;
}

export function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}
```

- [ ] **Step 2: Build check.** From `frontend/`: `npm run build` — must pass (unused-export warnings are fine; nothing imports this yet).
- [ ] **Step 3: Commit.** `git add frontend/src/lib/sessions-api.ts && git commit -m "frontend: shared sessions API types, form-POST helper, wsUrl helper"`

---

### Task 4: Frontend — `SessionsPage` (list, badges, switcher, delete, login links)

**Files:**
- Create: `frontend/src/pages/sessions-page.tsx` (creates the new `frontend/src/pages/` directory — the convention for migrated pages)

**Interfaces:**
- Consumes: Task 2 primitives (`Table*`, `Badge`, `Alert*`), Task 3 module, existing `Button`, `Skeleton`.
- Produces: `export function SessionsPage()` — wired into the router in Task 7. Table columns Name/Status/Details/Actions match the classic `sessions.html`; delete keeps a `window.confirm` guard.

- [ ] **Step 1: Create `frontend/src/pages/sessions-page.tsx`** with exactly:

```tsx
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  fetchSessionList,
  postForm,
  type SessionListData,
  type SessionResult,
} from "@/lib/sessions-api";

function StatusBadge({ status }: { status: SessionResult["status"] }) {
  if (status === "ACTIVE") {
    return <Badge className="bg-green-600 text-white">ACTIVE</Badge>;
  }
  if (status === "INVALID" || status === "ERROR") {
    return <Badge variant="destructive">{status}</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export function SessionsPage() {
  const [data, setData] = useState<SessionListData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetchSessionList());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  async function handleSwitch(sessionName: string) {
    try {
      await postForm("/sessions/active", { session_name: sessionName });
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    await refetch();
  }

  async function handleDelete(name: string) {
    if (!window.confirm(`Delete session "${name}"?`)) return;
    try {
      await postForm(`/sessions/${encodeURIComponent(name)}/delete`, {});
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    await refetch();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Sessions</h1>
        <div className="flex items-center gap-2">
          <Button render={<Link to="/sessions/login" />} variant="outline">
            Add account (phone)
          </Button>
          <Button render={<Link to="/sessions/login/qr" />} variant="outline">
            Add account (QR)
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {data && data.all_sessions.length > 0 && (
        <label className="flex items-center gap-2 text-sm">
          Active session:
          <select
            className="border-input bg-background h-9 rounded-md border px-3 text-sm"
            value={data.active_session ?? ""}
            onChange={(e) => void handleSwitch(e.target.value)}
          >
            {data.all_sessions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      )}

      {loading && !data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Details</TableHead>
              <TableHead className="w-24" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data?.results ?? []).map((r) => (
              <TableRow key={r.name}>
                <TableCell className="font-medium">{r.name}</TableCell>
                <TableCell>
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell>{r.details}</TableCell>
                <TableCell>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => void handleDelete(r.name)}
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {data && data.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  No sessions yet — add an account with phone or QR login.
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

Note: no polling — the list refetches only after mutations, matching the spec. React StrictMode double-runs the mount effect in dev; the second fetch is harmless.
- [ ] **Step 2: Build check.** From `frontend/`: `npm run build` — must pass. (The page isn't routed yet; that's Task 7.) If `Button` doesn't accept `size="sm"` or the `Badge` variant names differ from the generated files, adapt to what `frontend/src/components/ui/button.tsx` / `badge.tsx` actually export — do not edit the ui primitives.
- [ ] **Step 3: Commit.** `git add frontend/src/pages/sessions-page.tsx && git commit -m "frontend: SessionsPage — table, status badges, active-session switcher, delete, login links"`

---

### Task 5: Frontend — `SessionsLoginPhonePage` (phone → code → optional 2FA wizard)

**Files:**
- Create: `frontend/src/pages/sessions-login-phone-page.tsx`

**Interfaces:**
- Consumes: Task 3's `postForm`; existing `Button`, `Input`, `Card*`, Task 2's `Alert*`. Backend JSON shapes: `POST /sessions/login/phone` → `{status: "code_sent", flow_id}` | `{status: "error", error}`; `POST /sessions/login/code` → `{status: "done"}` | `{status: "need_2fa"}` | `{status: "error", error}`; `POST /sessions/login/2fa` → `{status: "done"}` | `{status: "error", error}`.
- Produces: `export function SessionsLoginPhonePage()` — wired in Task 7. Navigates to `/sessions` (SPA route, resolves to `/app/sessions`) on `done`.

- [ ] **Step 1: Create `frontend/src/pages/sessions-login-phone-page.tsx`** with exactly:

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";

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
import { postForm } from "@/lib/sessions-api";

type LoginResponse = {
  status: string;
  flow_id?: string;
  error?: string;
};

const STEP_DESCRIPTIONS = {
  phone: "Enter your phone number in international format.",
  code: "Enter the code Telegram just sent you.",
  "2fa": "This account has two-step verification. Enter your password.",
} as const;

export function SessionsLoginPhonePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"phone" | "code" | "2fa">("phone");
  const [flowId, setFlowId] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(
    url: string,
    data: Record<string, string>,
  ): Promise<LoginResponse | null> {
    setBusy(true);
    setError(null);
    try {
      const resp = await postForm(url, data);
      return (await resp.json()) as LoginResponse;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function sendPhone() {
    const r = await submit("/sessions/login/phone", { phone });
    if (!r) return;
    if (r.status === "code_sent" && r.flow_id) {
      setFlowId(r.flow_id);
      setStep("code");
    } else {
      setError(r.error ?? "Unknown error");
    }
  }

  async function sendCode() {
    const r = await submit("/sessions/login/code", { flow_id: flowId, code });
    if (!r) return;
    if (r.status === "done") {
      navigate("/sessions");
    } else if (r.status === "need_2fa") {
      setStep("2fa");
    } else {
      setError(r.error ?? "Unknown error");
    }
  }

  async function send2fa() {
    const r = await submit("/sessions/login/2fa", {
      flow_id: flowId,
      password,
    });
    if (!r) return;
    if (r.status === "done") {
      navigate("/sessions");
    } else {
      setError(r.error ?? "Unknown error");
    }
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Login via Phone Number</CardTitle>
        <CardDescription>{STEP_DESCRIPTIONS[step]}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Login failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {step === "phone" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void sendPhone();
            }}
          >
            <Input
              type="text"
              placeholder="+1234567890"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy || !phone}>
              Send code
            </Button>
          </form>
        )}
        {step === "code" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void sendCode();
            }}
          >
            <Input
              type="text"
              placeholder="Code from Telegram"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy || !code}>
              Submit code
            </Button>
          </form>
        )}
        {step === "2fa" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void send2fa();
            }}
          >
            <Input
              type="password"
              placeholder="2FA password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy || !password}>
              Submit password
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Build check.** From `frontend/`: `npm run build` — must pass.
- [ ] **Step 3: Commit.** `git add frontend/src/pages/sessions-login-phone-page.tsx && git commit -m "frontend: phone login wizard page (phone -> code -> optional 2FA)"`

---

### Task 6: Frontend — `SessionsLoginQrPage` (WebSocket-driven QR flow)

**Files:**
- Create: `frontend/src/pages/sessions-login-qr-page.tsx`

**Interfaces:**
- Consumes: Task 3's `wsUrl`; existing `Button`, `Input`, `Card*`, Task 2's `Alert*`. WS server→client messages: `{state: "waiting", qr_png_b64}`, `{state: "need_2fa"}`, `{state: "done", session_name}`, `{state: "error", error}`. Client→server (only after `need_2fa`): `{password}`.
- Produces: `export function SessionsLoginQrPage()` — wired in Task 7. Navigates to `/sessions` one second after `done`.

- [ ] **Step 1: Create `frontend/src/pages/sessions-login-qr-page.tsx`** with exactly:

```tsx
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

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
import { wsUrl } from "@/lib/sessions-api";

type QrState = "connecting" | "waiting" | "need_2fa" | "done" | "error";

type QrMessage = {
  state: string;
  qr_png_b64?: string;
  session_name?: string;
  error?: string;
};

const STATUS_TEXT: Record<QrState, string> = {
  connecting: "Connecting...",
  waiting: "Scan with Telegram: Settings → Devices → Link Desktop Device",
  need_2fa: "Two-step verification required.",
  done: "Logged in. Redirecting...",
  error: "Login failed.",
};

export function SessionsLoginQrPage() {
  const navigate = useNavigate();
  const wsRef = useRef<WebSocket | null>(null);
  const [state, setState] = useState<QrState>("connecting");
  const [qrSrc, setQrSrc] = useState<string | null>(null);
  const [sessionName, setSessionName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");

  useEffect(() => {
    // StrictMode double-invokes this effect in dev; the cleanup closes the
    // first socket, so only one QR flow survives. Production mounts once.
    const ws = new WebSocket(wsUrl("/sessions/login/qr/ws"));
    wsRef.current = ws;
    ws.onmessage = (event: MessageEvent<string>) => {
      const data = JSON.parse(event.data) as QrMessage;
      if (data.state === "waiting" && data.qr_png_b64) {
        setQrSrc(`data:image/png;base64,${data.qr_png_b64}`);
        setState("waiting");
      } else if (data.state === "need_2fa") {
        setState("need_2fa");
      } else if (data.state === "done") {
        setSessionName(data.session_name ?? "");
        setState("done");
      } else {
        setError(data.error ?? "Unknown error");
        setState("error");
      }
    };
    ws.onerror = () => {
      setError("WebSocket connection failed");
      setState("error");
    };
    return () => {
      wsRef.current = null;
      ws.close();
    };
  }, []);

  useEffect(() => {
    if (state !== "done") return;
    const t = setTimeout(() => navigate("/sessions"), 1000);
    return () => clearTimeout(t);
  }, [state, navigate]);

  function send2fa() {
    wsRef.current?.send(JSON.stringify({ password }));
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Login via QR Code</CardTitle>
        <CardDescription>
          {state === "done" && sessionName
            ? `Logged in as ${sessionName}. Redirecting...`
            : STATUS_TEXT[state]}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {qrSrc && state === "waiting" && (
          <img src={qrSrc} alt="Telegram login QR code" className="max-w-75" />
        )}
        {state === "need_2fa" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send2fa();
            }}
          >
            <Input
              type="password"
              placeholder="2FA password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={!password}>
              Submit password
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
```

Note: each WS connection starts a fresh QR flow server-side; the abandoned StrictMode-dev flow's temp session is cleaned up by the service's error path when the socket drops mid-send. No client-side mitigation needed.
- [ ] **Step 2: Build check.** From `frontend/`: `npm run build` — must pass. If Tailwind's `max-w-75` utility doesn't exist in this config, use `className="w-full max-w-[300px]"` instead (matches the classic page's 300px cap).
- [ ] **Step 3: Commit.** `git add frontend/src/pages/sessions-login-qr-page.tsx && git commit -m "frontend: QR login page driven by /sessions/login/qr/ws"`

---

### Task 7: Router wiring + `startsWith` active-nav matching

**Files:**
- Create: `frontend/src/lib/nav-match.ts`
- Modify: `frontend/src/main.tsx`, `frontend/src/components/layout.tsx`, `frontend/src/components/app-sidebar.tsx`

**Interfaces:**
- Consumes: `SessionsPage` (Task 4), `SessionsLoginPhonePage` (Task 5), `SessionsLoginQrPage` (Task 6), existing `ALL_NAV_ITEMS`/`NAV_GROUPS` (unchanged).
- Produces: routes `/sessions`, `/sessions/login`, `/sessions/login/qr` under basename `/app`; `findActiveNavItem(pathname)` used by both the breadcrumb and the sidebar highlight.

- [ ] **Step 1: Create `frontend/src/lib/nav-match.ts`** with exactly:

```ts
import { ALL_NAV_ITEMS, type NavItem } from "@/lib/nav";

/**
 * Prefix-matches the current pathname against nav items so sub-routes
 * (e.g. /sessions/login/qr) still resolve to their parent nav entry.
 * Longest URL wins, so a more specific item beats a shorter prefix.
 */
export function findActiveNavItem(pathname: string): NavItem | undefined {
  return [...ALL_NAV_ITEMS]
    .sort((a, b) => b.url.length - a.url.length)
    .find(
      (item) => pathname === item.url || pathname.startsWith(`${item.url}/`),
    );
}
```

- [ ] **Step 2: Replace `frontend/src/main.tsx`** with exactly (note `/sessions` is filtered out of the placeholder map so it is defined exactly once; every other nav item keeps its `NotMigratedPage`, including Groups' `fallbackHref`):

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

const router = createBrowserRouter(
  [
    {
      element: <Layout />,
      children: [
        { index: true, element: <Navigate to="/sessions" replace /> },
        { path: "/sessions", element: <SessionsPage /> },
        { path: "/sessions/login", element: <SessionsLoginPhonePage /> },
        { path: "/sessions/login/qr", element: <SessionsLoginQrPage /> },
        ...ALL_NAV_ITEMS.filter((item) => item.url !== "/sessions").map(
          (item) => ({
            path: item.url,
            element: (
              <NotMigratedPage
                title={item.title}
                fallbackHref={item.fallbackHref ?? item.url}
              />
            ),
          }),
        ),
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

- [ ] **Step 3: Fix the breadcrumb match in `frontend/src/components/layout.tsx`.** Replace the import line `import { ALL_NAV_ITEMS } from "@/lib/nav";` with `import { findActiveNavItem } from "@/lib/nav-match";`, and replace the line

```tsx
  const current = ALL_NAV_ITEMS.find((item) => item.url === pathname);
```

with

```tsx
  const current = findActiveNavItem(pathname);
```

Nothing else in the file changes.
- [ ] **Step 4: Fix the sidebar highlight in `frontend/src/components/app-sidebar.tsx`.** Add the import `import { findActiveNavItem } from "@/lib/nav-match";` after the `NAV_GROUPS` import, add one line at the top of the component body right after `const { pathname } = useLocation();`:

```tsx
  const activeItem = findActiveNavItem(pathname);
```

and change the `SidebarMenuButton` prop from `isActive={pathname === item.url}` to:

```tsx
                    isActive={activeItem?.url === item.url}
```

Nothing else in the file changes.
- [ ] **Step 5: Build check.** From `frontend/`: `npm run build` — must pass.
- [ ] **Step 6: Commit.** `git add frontend/src/lib/nav-match.ts frontend/src/main.tsx frontend/src/components/layout.tsx frontend/src/components/app-sidebar.tsx && git commit -m "frontend: wire Sessions routes, prefix-match breadcrumb and sidebar active state"`

---

### Task 8: Smoke test — server up, routes reachable, render verification

**Files:** none created or modified (verification only; `frontend/dist/` is rebuilt but not committed).

**Interfaces:** Consumes everything from Tasks 1–7. Produces a verification report in the task output.

- [ ] **Step 1: Fresh production build.** From `frontend/`: `npm run build` (the FastAPI app serves `frontend/dist/` at `/app` only when it exists — `FRONTEND_AVAILABLE`).
- [ ] **Step 2: Compile-check backend.** From the repo root: `python -m py_compile dashboard/routes/sessions.py dashboard/services/sessions_service.py`.
- [ ] **Step 3: Start the dashboard in the background.** From the repo root: `python -m uvicorn dashboard.app:app --host 127.0.0.1 --port 8000` (run in background; auth allows loopback without `DASHBOARD_PASSWORD`). Wait until it logs startup.
- [ ] **Step 4: Curl the routes.** All must return HTTP 200:
  - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/app/sessions`
  - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/app/sessions/login`
  - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/app/sessions/login/qr`
  - `curl -s http://127.0.0.1:8000/sessions/api/list` — must return JSON with `results`, `active_session`, `all_sessions` keys.
  - `curl -s http://127.0.0.1:8000/sessions | grep -c "<table>"` — classic page still renders (must be ≥ 1).
- [ ] **Step 5: Live render check (curl can't prove React mounted).** First check whether headless browser tooling is already available: `grep -i playwright frontend/package.json package.json 2>/dev/null` and check whether a Playwright MCP browser tool is available in your environment. If yes: load `http://127.0.0.1:8000/app/sessions` and confirm the page snapshot contains the "Sessions" heading, the table headers Name/Status/Details, and the two "Add account" links; load `/app/sessions/login` and confirm the phone input renders; load `/app/sessions/login/qr` and confirm the card renders (a QR image requires a live Telegram API, so `connecting`/`error` states are acceptable). Do NOT install Playwright or any new dependency if absent. If no headless tooling exists: fall back to the reduced-scope pattern from sub-project 1 — do a line-by-line read-through of the three page components against the route wiring and the backend JSON shapes, confirm the built `frontend/dist/index.html` references the hashed assets that `npm run build` just emitted, and state explicitly in your report which checks were done via curl+read-through and what a browser check would have covered (React mount, sidebar highlight on sub-routes, WS QR image).
- [ ] **Step 6: Stop the background server** and confirm `git status` shows a clean tree (dist/ is gitignored).
- [ ] **Step 7: Commit — none needed.** This task produces no file changes; if any fix was required to make the smoke test pass, commit it as `fix: sessions frontend smoke-test fixes` with the specific files.

---

## Self-Review Notes

**Spec coverage map:**
- Spec: one new endpoint `GET /sessions/api/list` via shared `_list_data()` (mirroring `_queue_data()`), old Jinja2 page unchanged → Task 1.
- Spec: session list/status/switch/delete parity (table columns, confirm-before-delete, switcher, links to both login flows) → Task 4 (native `<select>` used deliberately instead of adding a shadcn `select` — one control, per the design's minimalism).
- Spec: phone wizard with exact JSON shapes and `useNavigate` on done → Task 5.
- Spec: QR page with exact WS message shapes, base64 image, optional 2FA, redirect on done → Task 6 (fresh `wsUrl` helper in Task 3, since the old JSX pages were deleted in sub-project 1).
- Spec: three routes in `main.tsx` not derived from `nav.ts`; `/sessions` defined exactly once → Task 7 Step 2 (filter + explicit routes).
- Spec: `startsWith` breadcrumb/active-nav fix, longest-match-first, applied to both `layout.tsx` and `app-sidebar.tsx` → Task 7 Steps 1, 3, 4.
- Spec: `r.ok`-before-parse and stale-error-clearing from the start → Task 3 `postForm`/`fetchSessionList`, and every handler in Tasks 4–6 calls `setError(null)` on success paths.
- Spec testing section (`npm run build`, `py_compile`, curl + live render check with no-new-tooling fallback) → Task 8.
- Spec out-of-scope (no service-logic changes, no other pages, Jinja2 pages stay) → respected; `not-migrated-page.tsx` and `nav.ts` untouched.

**Placeholder scan:** every code step contains complete literal file contents or exact before/after line replacements; no "implement X" or "similar to Task N" references. The only conditional instructions are CLI-output adaptation (Task 2) and the Tailwind `max-w-75` fallback (Task 6), both with explicit alternatives.

**Type/name consistency:** `SessionResult`/`SessionListData`/`fetchSessionList`/`postForm`/`wsUrl` defined once in Task 3 and imported by name in Tasks 4–6; `findActiveNavItem` defined in Task 7 Step 1 before use in Steps 3–4; page component names in Task 7's `main.tsx` imports match the exports of Tasks 4–6; backend field names (`results`, `active_session`, `all_sessions`, `flow_id`, `qr_png_b64`, `session_name`) match `sessions.py`/`sessions_service.py` verbatim.

**Scope check:** no new npm dependencies (shadcn CLI only adds source files); no polling; no shadcn `select`/`dialog` additions beyond the three required primitives; no auth changes; no `.gitignore` changes (the `lib/` anchoring is already fixed, so `sessions-api.ts` and `nav-match.ts` are tracked); no test framework introduced.
