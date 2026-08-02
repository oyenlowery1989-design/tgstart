# Bot Reply Queue React (shadcn) Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the "Not migrated yet" placeholder at `/app/reply` with a real React Bot Reply queue page (pending / approved / recent tables, approve/reject/retry actions, 10s polling), sub-project 4 of 9.

**Architecture:** Pure frontend — the JSON API in `dashboard/routes/bot_reply.py` (`GET /reply/api/queue`, `POST /reply/api/pending/{id}/approve|reject|retry`) is live and unchanged; we add a page-scoped API module, one page component using already-installed shadcn `Table`/`Badge`/`Button`/`Alert`, and one route entry in `main.tsx`. Behavior is an exact TypeScript+shadcn translation of the old plain-JS `ReplyPage.jsx` (as fixed in `fdfe600`), including its 10-second poll, immediate refetch after actions, and per-row 409-vs-other error distinction.

**Tech Stack:** React 19 + TypeScript, Vite, react-router (basename `/app`), shadcn/ui (base-ui variant — `render={...}`, never `asChild`), Tailwind.

## Global Constraints

- READ but do NOT modify: `dashboard/routes/bot_reply.py`, `6_messaging/bot_reply/`, `frontend/src/lib/nav.ts`, `frontend/src/components/layout.tsx`, `frontend/src/components/app-sidebar.tsx`, `dashboard/templates/reply/index.html`.
- No new dependencies, no new shadcn components (`table`, `badge`, `button`, `alert`, `skeleton` are already installed in `frontend/src/components/ui/`).
- No backend changes of any kind. No auth changes.
- "Bot Reply Setup" (`/reply/setup`) is sub-project 9 — it stays on `NotMigratedPage` and the old Jinja2 page. Do not add it to `MIGRATED_URLS`, do not create a React route for it. The link to it from this page must be a plain `<a href="/reply/setup">` (full page load, escapes the `/app` basename) — never a react-router `Link`.
- House style: page-scoped API module (`frontend/src/lib/reply-api.ts`), do NOT import from `sessions-api.ts`/`stats-api.ts`, do NOT create a shared `lib/api.ts` (the `wsUrl` hoist is tracked for a later sub-project; this page polls, no WebSocket, so it adds nothing to that debt).
- Verification: `npm run build` in `frontend/` (`tsc -b` + Vite build). No test framework. No Python changes expected, so no `py_compile` needed.
- All frontend commands run from `frontend/` (Node v22.23.1, npm 10.9.8).

---

### Task 1: Reply API module

**Files:**
- Create: `frontend/src/lib/reply-api.ts`

**Interfaces:**
- `type ReplyRow` — only the 7 fields the UI reads
- `type QueueData = { configured: boolean; pending: ReplyRow[]; approved: ReplyRow[]; recent: ReplyRow[] }`
- `async function fetchQueue(): Promise<QueueData>` — throws on non-OK (house style)
- `type ResolveAction = "approve" | "reject" | "retry"`
- `async function resolvePending(id: number, action: ResolveAction): Promise<Response>` — returns raw `Response`, deliberately does NOT throw on non-OK

**Steps:**

- [ ] Create `frontend/src/lib/reply-api.ts` with exactly this content:

```ts
// Shared helpers for the Bot Reply queue page. Backend endpoints live under
// /reply (no /app prefix — that's only the SPA router basename).

/**
 * Deliberate narrowing, not a mismatch: the backend returns every column of
 * the pending_replies table on every row (chat_id, source_message_id,
 * approval_msg_id, created_at, resolved_at, sent_message_id, ...). The UI
 * only reads these seven fields, so only these are typed.
 */
export type ReplyRow = {
  id: number;
  chat_title: string;
  source_sender: string;
  source_text: string;
  draft_text: string;
  status: string;
  error: string | null;
};

export type QueueData = {
  configured: boolean;
  pending: ReplyRow[];
  approved: ReplyRow[];
  recent: ReplyRow[];
};

export async function fetchQueue(): Promise<QueueData> {
  const resp = await fetch("/reply/api/queue");
  if (!resp.ok) {
    throw new Error(`Failed to load queue (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<QueueData>;
}

export type ResolveAction = "approve" | "reject" | "retry";

/**
 * POSTs an approve/reject/retry action and returns the raw Response.
 * Intentionally does NOT throw on non-OK (unlike fetchQueue above): the
 * caller must distinguish 409 (already resolved elsewhere — e.g. the
 * Telegram-side approval bot won the race) from other failures, so it needs
 * the status code and body, not a thrown Error.
 */
export async function resolvePending(
  id: number,
  action: ResolveAction,
): Promise<Response> {
  return fetch(`/reply/api/pending/${id}/${action}`, { method: "POST" });
}
```

- [ ] Build-check: from `frontend/`, run `npm run build` — must exit 0. (The module is not imported yet; this only proves it type-checks.)
- [ ] Commit with message: `frontend: reply-api module with queue types and resolve helper`

---

### Task 2: Bot Reply queue page component

**Files:**
- Create: `frontend/src/pages/reply-page.tsx`

**Interfaces:**
- `export function ReplyPage()` — named export, matching `SessionsPage`/`StatsPage` convention
- Local `StatusBadge({ status }: { status: string })` component

**Behavioral contract (translated exactly from the old `ReplyPage.jsx`, commit `fdfe600`):**
- Poll `fetchQueue` every 10 000 ms, plus once immediately on mount; interval cleared on unmount.
- Top-level fetch failure → destructive `Alert`, replacing the whole page body (old page's `if (error) return ...` gate).
- Per-row action errors keyed by reply id in `Record<number, string>` so one row's error never clobbers another's.
- Approve/Reject: 409 → `Already resolved: <detail>`; other non-OK → `Error: <status>`; success → clear that row's error and refetch immediately.
- Retry: any non-OK (including 409) → `Retry failed: <status>` — the old page did not special-case retry's 409 with "Already resolved" text; preserve that exactly (known minor inherited from the reference implementation, not fixed here).
- `!data.configured` → informational `Alert` (upgrade from the old raw styled `<p>`), same wording.
- Deliberate simplification: the old 4-way color map (`sent`/`rejected`/`failed`/default) becomes a 3-way shadcn-variant map — `sent` → green-overridden `Badge` (same technique as Sessions' ACTIVE badge), `rejected`/`failed` → `variant="destructive"`, everything else → `variant="secondary"`. This loses the old yellow-vs-red distinction between `rejected` and `failed` on purpose.

**Steps:**

- [ ] Create `frontend/src/pages/reply-page.tsx` with exactly this content:

```tsx
import { useCallback, useEffect, useState } from "react";

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
import { fetchQueue, resolvePending, type QueueData } from "@/lib/reply-api";

const POLL_INTERVAL_MS = 10000;

function StatusBadge({ status }: { status: string }) {
  if (status === "sent") {
    return <Badge className="bg-green-600 text-white">sent</Badge>;
  }
  if (status === "rejected" || status === "failed") {
    return <Badge variant="destructive">{status}</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export function ReplyPage() {
  const [data, setData] = useState<QueueData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});

  const refetch = useCallback(async () => {
    try {
      setData(await fetchQueue());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void refetch();
    const id = setInterval(() => void refetch(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refetch]);

  function setRowError(id: number, msg: string) {
    setRowErrors((prev) => ({ ...prev, [id]: msg }));
  }

  function clearRowError(id: number) {
    setRowErrors((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function handleResolve(id: number, action: "approve" | "reject") {
    const resp = await resolvePending(id, action);
    if (resp.status === 409) {
      const body = (await resp.json()) as { detail?: string };
      setRowError(id, `Already resolved: ${body.detail ?? ""}`);
      return;
    }
    if (!resp.ok) {
      setRowError(id, `Error: ${resp.status}`);
      return;
    }
    clearRowError(id);
    void refetch();
  }

  async function handleRetry(id: number) {
    const resp = await resolvePending(id, "retry");
    if (!resp.ok) {
      setRowError(id, `Retry failed: ${resp.status}`);
      return;
    }
    clearRowError(id);
    void refetch();
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Bot Reply Queue</h1>
        <a
          href="/reply/setup"
          className="text-muted-foreground hover:text-foreground text-sm underline underline-offset-3"
        >
          Chat setup &amp; settings &raquo;
        </a>
      </div>

      {!data.configured && (
        <Alert>
          <AlertTitle>Bot Reply not fully configured</AlertTitle>
          <AlertDescription>
            The runner will not start. Set a session on{" "}
            <a href="/reply/setup">Chat setup &amp; settings</a> and ensure{" "}
            <code>BOT_REPLY_APPROVAL_BOT_TOKEN</code> /{" "}
            <code>BOT_REPLY_OPERATOR_USER_ID</code> are set in{" "}
            <code>.env</code>, then restart the dashboard.
          </AlertDescription>
        </Alert>
      )}

      <section>
        <h2 className="mb-2 text-lg font-semibold">Pending approval</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Chat</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Draft</TableHead>
              <TableHead className="w-56">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.pending.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.chat_title}</TableCell>
                <TableCell>{r.source_sender}</TableCell>
                <TableCell className="text-muted-foreground max-w-64 whitespace-normal">
                  {r.source_text}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal">
                  {r.draft_text}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      className="bg-green-600 text-white hover:bg-green-500"
                      onClick={() => void handleResolve(r.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => void handleResolve(r.id, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                  {rowErrors[r.id] && (
                    <div className="text-destructive mt-1 text-xs">
                      {rowErrors[r.id]}
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {data.pending.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  Nothing pending.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Approved, sending</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Chat</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Draft</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.approved.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.chat_title}</TableCell>
                <TableCell>{r.source_sender}</TableCell>
                <TableCell className="text-muted-foreground max-w-64 whitespace-normal">
                  {r.source_text}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal">
                  {r.draft_text}
                </TableCell>
              </TableRow>
            ))}
            {data.approved.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  None waiting to send.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Recent</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Chat</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Draft</TableHead>
              <TableHead className="w-40">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.recent.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell className="font-medium">{r.chat_title}</TableCell>
                <TableCell>{r.source_sender}</TableCell>
                <TableCell className="text-muted-foreground max-w-64 whitespace-normal">
                  {r.source_text}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal">
                  {r.draft_text}
                  {r.status === "failed" && r.error && (
                    <div className="text-destructive mt-1 text-xs">
                      {r.error}
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  {r.status === "failed" && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleRetry(r.id)}
                      >
                        Retry
                      </Button>
                      {rowErrors[r.id] && (
                        <span className="text-destructive text-xs">
                          {rowErrors[r.id]}
                        </span>
                      )}
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {data.recent.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground">
                  No recent activity.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>
    </div>
  );
}
```

- [ ] Build-check: from `frontend/`, run `npm run build` — must exit 0. (Page not yet routed; this proves it type-checks against `reply-api.ts` and the ui components.)
- [ ] Commit with message: `frontend: Bot Reply queue page with 10s polling and approve/reject/retry`

---

### Task 3: Router wiring

**Files:**
- Modify: `frontend/src/main.tsx`

**Interfaces:** none new — adds `{ path: "/reply", element: <ReplyPage /> }` and `"/reply"` to `MIGRATED_URLS`.

Do NOT touch `nav.ts` ("Bot Reply" nav item already exists at `url: "/reply"`), `layout.tsx`, or `app-sidebar.tsx` — `/reply` has no sub-routes in this plan, so `findActiveNavItem` already highlights it correctly (same reasoning as Stats). Do NOT add `/reply/setup` — it must keep resolving to `NotMigratedPage` via the generic mapping.

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
import { ReplyPage } from "@/pages/reply-page";
import { SessionsLoginPhonePage } from "@/pages/sessions-login-phone-page";
import { SessionsLoginQrPage } from "@/pages/sessions-login-qr-page";
import { SessionsPage } from "@/pages/sessions-page";
import { StatsPage } from "@/pages/stats-page";

const MIGRATED_URLS = ["/sessions", "/stats", "/reply"];

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
        { path: "/reply", element: <ReplyPage /> },
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

- [ ] Build-check: from `frontend/`, run `npm run build` — must exit 0.
- [ ] Commit with message: `frontend: wire /reply route, exclude it from NotMigratedPage mapping`

---

### Task 4: Smoke test — build, curl, live browser check

**Files:** none created or modified (fix-forward commits only if a defect is found).

**Steps:**

- [ ] From `frontend/`, run `npm run build` — must exit 0 (this also refreshes `frontend/dist`, which the dashboard serves at `/app`).
- [ ] Start the dashboard in the background from the repo root, using the project venv: `source venv/bin/activate && python dashboard/app.py` (binds `127.0.0.1:8000` by default, no auth on loopback). Wait for the "Starting Dashboard" line.
- [ ] `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/app/reply` → expect `200`.
- [ ] `curl -s http://127.0.0.1:8000/reply/api/queue` → expect a JSON body containing all four keys `configured`, `pending`, `approved`, `recent` (e.g. pipe through `python -c 'import json,sys; d=json.load(sys.stdin); assert set(d) >= {"configured","pending","approved","recent"}, d.keys(); print("ok")'`).
- [ ] `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/reply` → expect `200` (old Jinja2 page still reachable, unmodified).
- [ ] Live browser verification (same pattern as prior sub-projects): check for headless browser tooling (e.g. Playwright MCP tools). If present: navigate to `http://127.0.0.1:8000/app/reply`, confirm the three section headings ("Pending approval", "Approved, sending", "Recent") render with their tables/empty states, and confirm the sidebar highlights "Bot Reply". If the environment's bot-reply database has a real pending draft, optionally click Approve or Reject and confirm the row leaves Pending and the page refetches; if no live drafts exist, note that as an environment limitation, not a failure. If no headless tooling is available at all, fall back to the curl checks above plus a read-through of the rendered `index.html`/bundle references, explicitly noting that a browser check would have additionally covered: section rendering, sidebar active state, poll behavior, and the action buttons.
- [ ] Stop the background dashboard process.
- [ ] No commit for this task unless a defect was found and fixed; if a fix was needed, commit it as `fix(frontend): <short description>` and re-run the full sequence above.

---

## Self-Review Notes

**Spec coverage map** (spec: `docs/superpowers/specs/2026-08-02-bot-reply-queue-shadcn-design.md`):
- "No backend changes, reuse 4 endpoints as-is" → Global Constraints + Task 1 (fetch paths match `bot_reply.py` routes exactly: `/reply/api/queue`, `/reply/api/pending/{id}/{approve|reject|retry}`).
- "One new frontend route `/app/reply`, no sub-routes" → Task 3.
- "shadcn Table, three sections, Approve/Reject, read-only Approved, Recent with Badge + Retry on failed + error text" → Task 2.
- "10s polling + immediate refetch after actions, resp.ok + error-clearing convention (`fdfe600`)" → Task 2 (`POLL_INTERVAL_MS`, `refetch` clears `error` on success, `handleResolve`/`handleRetry` clear the row error and refetch immediately on success).
- "No new dependency" → no `npm install` or `shadcn add` step anywhere.
- "Out of scope: /reply/setup, runner, old Jinja2 page retirement" → Global Constraints; Task 4 verifies old `/reply` still returns 200.
- "Testing: npm run build + curl /app/reply + reduced-scope browser fallback" → Task 4.

**Placeholder scan:** Every code step is complete literal file content — no `...`, no `// TODO`, no "similar to". The only elisions are in prose (behavioral contract), not code.

**Type/name consistency:** `ReplyPage` (named export) matches `SessionsPage`/`StatsPage` convention; `main.tsx` imports `{ ReplyPage } from "@/pages/reply-page"` matching Task 2's export. `reply-api.ts` exports `fetchQueue`, `resolvePending`, `ReplyRow`, `QueueData`, `ResolveAction`; Task 2 imports `fetchQueue`, `resolvePending`, `type QueueData` (it does not need `ReplyRow` or `ResolveAction` directly — `ResolveAction`'s literal union accepts the narrowed `"approve" | "reject"` parameter, and row fields are accessed through `QueueData`). `Button render={...}` base-ui convention is respected (only plain `onClick` buttons here, no `asChild` anywhere). Alert/Badge/Table/Skeleton imports match the actual files in `frontend/src/components/ui/`.

**Deliberate divergences from the old page (documented, intentional):**
- Card-list layout → shadcn `Table` per section (spec requirement; Sessions precedent for empty-state `colSpan` rows).
- 4-way status color map → 3-way Badge variant map (`rejected` and `failed` both destructive) — deliberate simplification.
- Raw yellow `<p>` configured warning → `Alert` with title "Bot Reply not fully configured", same substance (`/reply/setup` link, both env var names, `.env`, restart note).
- "Loading..." text → three `Skeleton` rows (shell convention from Sessions).
- Retry's 409 still shows `Retry failed: 409` (not "Already resolved") — inherited old behavior preserved on purpose, noted as a known minor.

**Scope check:** No changes to `nav.ts`, `layout.tsx`, `app-sidebar.tsx`, any `dashboard/` Python, any `6_messaging/` code, or the sessions/stats pages. No shared API module introduced (`wsUrl` hoist deferred per sub-project 3's note). Three files touched total (two new, one modified) plus a run-only smoke-test task.
