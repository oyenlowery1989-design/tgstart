# Bot Reply Queue React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the Bot Reply queue page (`/reply`) to the React frontend built for the Stats page, as the second slice of the dashboard's ongoing migration off Jinja2.

**Architecture:** `dashboard/routes/bot_reply.py` gains one new JSON endpoint, `GET /reply/api/queue`, returning the exact same data `reply_queue_page` already assembles for the Jinja2 template — no new backend logic, no changes to the existing mutating endpoints (`POST /reply/api/pending/{id}/approve|reject|retry`), which the new page reuses unchanged. `frontend/src/App.jsx` gains a minimal path-based router (no new dependency — two pages don't justify `react-router-dom`) so `/app/reply` renders the new `ReplyPage` and everything else keeps rendering `StatsPage`. `ReplyPage.jsx` polls `/reply/api/queue` every 10s and re-fetches immediately after any action, mirroring the existing Jinja2 page's three sections (Pending/Approved/Recent) and behavior (409 handling, retry-on-failed).

**Tech Stack:** Same as the Stats slice — React 18, Tailwind (already configured), no new dependencies.

## Global Constraints

- No test framework in this repo — verification is `python -m py_compile` for backend, `npm run build` for frontend.
- The Bot Reply setup page (`/reply/setup`, per-chat toggles) stays Jinja2 — out of scope for this plan.
- All mutating logic (approve/reject/retry, chat config, settings) already exists in `dashboard/routes/bot_reply.py` and must not be duplicated or reimplemented — only a new read endpoint is added.
- `dashboard/routes/bot_reply.py` uses a shared singleton sqlite connection (`_conn()`) — reuse it, do not open a second connection.
- Follow the exact conditional-link pattern already used for Stats in `dashboard/templates/base.html` (`{% if frontend_available %}/app/stats{% else %}/stats{% endif %}`) for the Bot Reply link.

---

### Task 1: Backend — `GET /reply/api/queue` JSON endpoint

**Files:**
- Modify: `dashboard/routes/bot_reply.py`

**Interfaces:**
- Consumes: `bot_reply_db.list_pending_replies`, `bot_reply_db.get_setting`, `_conn()` (all existing, already imported/defined in this file)
- Produces: `GET /reply/api/queue` returning JSON:
  ```json
  {
    "configured": true,
    "pending": [{"id": 1, "chat_title": "...", "source_sender": "...", "source_text": "...", "draft_text": "..."}],
    "approved": [{"id": 2, "chat_title": "...", "source_sender": "...", "source_text": "...", "draft_text": "..."}],
    "recent": [{"id": 3, "status": "sent", "chat_title": "...", "source_sender": "...", "source_text": "...", "draft_text": "...", "error": null}]
  }
  ```
  (each row is the raw dict `bot_reply_db.list_pending_replies` already returns — sqlite `Row` objects converted to `dict`, so this is a straight pass-through, not a reshaping)

- [ ] **Step 1: Add the JSON endpoint**

Add this route to `dashboard/routes/bot_reply.py`, directly after the existing `reply_queue_page` function (which builds this exact same data for the Jinja2 template — read that function first, since this step factors its body into a shared helper rather than duplicating it):

Replace the existing `reply_queue_page` function with this (the body is split into a shared `_queue_data()` helper, then both the HTML route and the new JSON route call it — this avoids duplicating the pending/approved/recent/configured assembly logic):

```python
def _queue_data():
    conn = _conn()
    pending = bot_reply_db.list_pending_replies(conn, status="pending")
    approved = bot_reply_db.list_pending_replies(conn, status="approved")
    recent = [r for r in bot_reply_db.list_pending_replies(conn)
              if r["status"] in ("sent", "rejected", "failed", "expired")][:20]

    session_name = bot_reply_db.get_setting(conn, "session_name")
    bot_token = os.getenv("BOT_REPLY_APPROVAL_BOT_TOKEN", "")
    operator_user_id = os.getenv("BOT_REPLY_OPERATOR_USER_ID", "")
    configured = bool(session_name) and bool(bot_token) and bool(operator_user_id)

    return {"configured": configured, "pending": pending, "approved": approved, "recent": recent}


@router.get("", response_class=HTMLResponse)
async def reply_queue_page(request: Request):
    data = _queue_data()
    return _render_template("reply/index.html", {
        "request": request, **data,
        "active_session": get_active_session(request), "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
    })


@router.get("/api/queue")
async def api_queue():
    return _queue_data()
```

- [ ] **Step 2: Compile-check**

```bash
python -m py_compile dashboard/routes/bot_reply.py
```

Expected: no output, exit code 0.

- [ ] **Step 3: Manual smoke test**

```bash
source venv/bin/activate
DASHBOARD_PORT=8001 python dashboard/app.py &
sleep 2
curl -s http://127.0.0.1:8001/reply/api/queue
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/reply
kill %1
```

Expected: the first curl returns a JSON object with `configured`, `pending`, `approved`,
`recent` keys (arrays may be empty — that's fine, it means no drafts are queued right
now). The second curl returns `200` — the existing Jinja2 `/reply` page must still work
unchanged (proves `_queue_data()` refactor didn't break the HTML route).

- [ ] **Step 4: Commit**

```bash
git add dashboard/routes/bot_reply.py
git commit -m "feat(dashboard): add GET /reply/api/queue JSON endpoint for the queue page"
```

---

### Task 2: Frontend — minimal path-based router in App.jsx

**Files:**
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `StatsPage` (existing), `ReplyPage` (Task 3 — not yet created; this task's build check will fail until Task 3 exists, so do Task 2 and Task 3 as one commit if working through them back-to-back, or stub `ReplyPage` first — see Step 1 note)
- Produces: `App` (default export) now renders `ReplyPage` when `window.location.pathname === "/app/reply"`, and `StatsPage` for every other path (including `/app`, `/app/`, `/app/stats`) — same default-to-Stats behavior as before this change

- [ ] **Step 1: Rewrite `frontend/src/App.jsx`**

```jsx
import Layout from "./components/Layout.jsx";
import StatsPage from "./pages/StatsPage.jsx";
import ReplyPage from "./pages/ReplyPage.jsx";

export default function App() {
  const isReply = window.location.pathname === "/app/reply";
  return <Layout>{isReply ? <ReplyPage /> : <StatsPage />}</Layout>;
}
```

Note: `frontend/src/pages/ReplyPage.jsx` doesn't exist until Task 3. If you're
implementing Task 2 and Task 3 in the same session back-to-back, write this file after
Task 3's `ReplyPage.jsx` exists so `npm run build` succeeds on the first try. If Task 2 is
being done standalone, create a temporary placeholder first:

```jsx
// frontend/src/pages/ReplyPage.jsx — temporary placeholder, Task 3 replaces this file
export default function ReplyPage() {
  return <p className="text-slate-400">Loading...</p>;
}
```

commit that placeholder in this task if you create it, and note in your report that Task
3 will overwrite it — do not skip Step 2's build check by leaving `ReplyPage.jsx` missing.

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
# If you created the placeholder in Step 1:
git add frontend/src/pages/ReplyPage.jsx
git commit -m "feat(frontend): add minimal path-based router for /app/reply vs /app/stats"
```

---

### Task 3: Frontend — ReplyPage (queue, actions, polling)

**Files:**
- Create (or overwrite the Task 2 placeholder): `frontend/src/pages/ReplyPage.jsx`

**Interfaces:**
- Consumes: `GET /reply/api/queue` (Task 1), `POST /reply/api/pending/{id}/approve`, `POST /reply/api/pending/{id}/reject`, `POST /reply/api/pending/{id}/retry` (all existing, unmodified)
- Produces: `ReplyPage` (default export, no props) — the full page component

- [ ] **Step 1: Write `frontend/src/pages/ReplyPage.jsx`**

```jsx
import { useEffect, useState, useCallback } from "react";

const POLL_INTERVAL_MS = 10000;

function StatusBadge({ status }) {
  const styles = {
    sent: "bg-green-900 text-green-300",
    rejected: "bg-yellow-900 text-yellow-300",
    failed: "bg-red-900 text-red-300",
  };
  const cls = styles[status] || "bg-slate-800 text-slate-300";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs ${cls}`}>{status}</span>
  );
}

export default function ReplyPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [rowErrors, setRowErrors] = useState({});

  const fetchQueue = useCallback(() => {
    fetch("/reply/api/queue")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError("Failed to load queue."));
  }, []);

  useEffect(() => {
    fetchQueue();
    const id = setInterval(fetchQueue, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchQueue]);

  async function resolve(id, action) {
    const resp = await fetch(`/reply/api/pending/${id}/${action}`, { method: "POST" });
    if (resp.status === 409) {
      const body = await resp.json();
      setRowErrors((prev) => ({ ...prev, [id]: `Already resolved: ${body.detail || ""}` }));
      return;
    }
    if (!resp.ok) {
      setRowErrors((prev) => ({ ...prev, [id]: `Error: ${resp.status}` }));
      return;
    }
    fetchQueue();
  }

  async function retry(id) {
    const resp = await fetch(`/reply/api/pending/${id}/retry`, { method: "POST" });
    if (!resp.ok) {
      setRowErrors((prev) => ({ ...prev, [id]: `Retry failed: ${resp.status}` }));
      return;
    }
    fetchQueue();
  }

  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!data) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Bot Reply Queue</h1>
      <p className="text-slate-500 text-sm mb-4">
        <a href="/reply/setup" className="text-blue-400 underline">
          Chat setup &amp; settings &raquo;
        </a>
      </p>

      {!data.configured && (
        <p className="bg-yellow-950 border border-yellow-800 text-yellow-300 text-sm rounded px-3 py-2 mb-4">
          Bot Reply is not fully configured — the runner will not start. Set a session on{" "}
          <a href="/reply/setup" className="underline">
            Chat setup &amp; settings
          </a>{" "}
          and ensure <code>BOT_REPLY_APPROVAL_BOT_TOKEN</code> /{" "}
          <code>BOT_REPLY_OPERATOR_USER_ID</code> are set in <code>.env</code>, then
          restart the dashboard.
        </p>
      )}

      <h2 className="text-lg font-semibold mt-6 mb-2">Pending approval</h2>
      <div className="bg-slate-900 border border-slate-800 rounded overflow-hidden">
        {data.pending.length === 0 ? (
          <p className="text-slate-500 text-sm px-3 py-3">Nothing pending.</p>
        ) : (
          data.pending.map((r) => (
            <div key={r.id} className="border-b border-slate-800 last:border-0 px-3 py-3">
              <div className="text-sm text-slate-300">
                <span className="font-medium">{r.chat_title}</span> — {r.source_sender}
              </div>
              <div className="text-sm text-slate-500 mt-1">{r.source_text}</div>
              <div className="text-sm text-slate-100 mt-1">{r.draft_text}</div>
              <div className="mt-2 flex gap-2 items-center">
                <button
                  className="bg-green-600 hover:bg-green-500 text-white text-xs font-medium px-3 py-1 rounded"
                  onClick={() => resolve(r.id, "approve")}
                >
                  Approve
                </button>
                <button
                  className="bg-red-600 hover:bg-red-500 text-white text-xs font-medium px-3 py-1 rounded"
                  onClick={() => resolve(r.id, "reject")}
                >
                  Reject
                </button>
                {rowErrors[r.id] && (
                  <span className="text-red-400 text-xs">{rowErrors[r.id]}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <h2 className="text-lg font-semibold mt-6 mb-2">Approved, sending</h2>
      <div className="bg-slate-900 border border-slate-800 rounded overflow-hidden">
        {data.approved.length === 0 ? (
          <p className="text-slate-500 text-sm px-3 py-3">None waiting to send.</p>
        ) : (
          data.approved.map((r) => (
            <div key={r.id} className="border-b border-slate-800 last:border-0 px-3 py-3">
              <div className="text-sm text-slate-300">
                <span className="font-medium">{r.chat_title}</span> — {r.source_sender}
              </div>
              <div className="text-sm text-slate-500 mt-1">{r.source_text}</div>
              <div className="text-sm text-slate-100 mt-1">{r.draft_text}</div>
            </div>
          ))
        )}
      </div>

      <h2 className="text-lg font-semibold mt-6 mb-2">Recent</h2>
      <div className="bg-slate-900 border border-slate-800 rounded overflow-hidden">
        {data.recent.length === 0 ? (
          <p className="text-slate-500 text-sm px-3 py-3">No recent activity.</p>
        ) : (
          data.recent.map((r) => (
            <div key={r.id} className="border-b border-slate-800 last:border-0 px-3 py-3">
              <div className="text-sm text-slate-300 flex items-center gap-2">
                <StatusBadge status={r.status} />
                <span className="font-medium">{r.chat_title}</span> — {r.source_sender}
              </div>
              <div className="text-sm text-slate-500 mt-1">{r.source_text}</div>
              <div className="text-sm text-slate-100 mt-1">{r.draft_text}</div>
              {r.status === "failed" && r.error && (
                <div className="text-red-400 text-xs mt-1">{r.error}</div>
              )}
              {r.status === "failed" && (
                <div className="mt-2 flex gap-2 items-center">
                  <button
                    className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-3 py-1 rounded"
                    onClick={() => retry(r.id)}
                  >
                    Retry
                  </button>
                  {rowErrors[r.id] && (
                    <span className="text-red-400 text-xs">{rowErrors[r.id]}</span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 3: Manual smoke test**

```bash
source venv/bin/activate
DASHBOARD_PORT=8001 python dashboard/app.py &
sleep 2
curl -s http://127.0.0.1:8001/app/reply | grep 'id="root"'
kill %1
```

Expected: the curl output contains `<div id="root">`, confirming the SPA shell serves for
`/app/reply` (same catch-all route Task 4 of the Stats plan already wired — no dashboard.py
changes needed here). A full visual/functional check (clicking Approve/Reject, watching
the 10s poll pick up a new draft) requires a live Bot Reply runner with real Telegram
credentials — if none are configured in this environment (check `bot_reply.get_setting`
output from Task 1's smoke test), note that in your report as an environment limitation,
same as the Stats plan's live-scan gap.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ReplyPage.jsx
git commit -m "feat(frontend): add Bot Reply queue page with 10s polling"
```

---

### Task 4: Wire the sidebar and old navbar to the new page

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `dashboard/templates/base.html`

**Interfaces:**
- Consumes: nothing new
- Produces: `/app/reply` reachable from both the new sidebar and the old navbar, with the same build-aware fallback the Stats link already has

- [ ] **Step 1: Update `frontend/src/components/Sidebar.jsx`**

Change the Bot Reply entry in `NAV_GROUPS`'s `Automation` group from:

```jsx
{ label: "Bot Reply", href: "/reply", external: true },
```

to:

```jsx
{ label: "Bot Reply", href: "/app/reply", external: false },
```

- [ ] **Step 2: Update `dashboard/templates/base.html`**

Change:

```html
<a href="/reply">Bot Reply</a>
```

to:

```html
<a href="{% if frontend_available %}/app/reply{% else %}/reply{% endif %}">Bot Reply</a>
```

- [ ] **Step 3: Build and full import check**

```bash
cd frontend && npm run build
cd ..
source venv/bin/activate
python -c "
import sys; sys.path.insert(0, '.')
from dashboard import app
print('APP_OK, routes:', len(app.app.routes))
"
```

Expected: build succeeds; `APP_OK, routes: <count>` with no traceback.

- [ ] **Step 4: Manual smoke test**

```bash
DASHBOARD_PORT=8001 python dashboard/app.py &
sleep 2
curl -s http://127.0.0.1:8001/sessions | grep -o 'href="[^"]*">Bot Reply'
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/app/reply
kill %1
```

Expected: the first curl shows the navbar's Bot Reply link now points at `/app/reply`
(since `frontend/dist/` exists in this environment after Task 2/3's builds); the second
curl returns `200`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Sidebar.jsx dashboard/templates/base.html
git commit -m "feat(dashboard): point Bot Reply nav links at the new /app/reply page"
```

---

## Self-Review Notes

**Spec coverage:**
- New JSON queue endpoint reusing existing data-assembly logic, no duplication → Task 1
  (`_queue_data()` helper factored out, both HTML and JSON routes call it). ✓
- Minimal router, no new dependency → Task 2. ✓
- Full queue page (pending/approved/recent, approve/reject/retry, 409 handling, status
  badges) → Task 3, matches `dashboard/templates/reply/index.html`'s structure and
  behavior section-for-section. ✓
- 10s polling → Task 3 (`POLL_INTERVAL_MS = 10000`), matches the user's explicit choice
  over the Stats plan's default-recommendation pattern. ✓
- Setup page stays Jinja2, unlinked from new-page changes beyond the "Chat setup &
  settings »" link (unchanged behavior, just re-hosted) → Task 3, confirmed out of scope
  in Global Constraints. ✓
- Sidebar + old navbar both updated with the same `frontend_available` fallback pattern
  Stats already established → Task 4. ✓

**Placeholder scan:** no TBD/TODO; every step has literal code. Task 2's temporary
`ReplyPage.jsx` placeholder is explicitly conditional on execution order and instructs the
implementer to note it in their report — not a plan placeholder, a legitimate ordering
accommodation since Tasks 2 and 3 have a circular file dependency (App.jsx imports
ReplyPage, ReplyPage doesn't exist until Task 3) that has to be broken somewhere.

**Type/name consistency check:** `_queue_data()` (Task 1) returns keys `configured`,
`pending`, `approved`, `recent` — `ReplyPage.jsx` (Task 3) destructures `data.configured`,
`data.pending`, `data.approved`, `data.recent` with matching names. Row shape (`id`,
`chat_title`, `source_sender`, `source_text`, `draft_text`, `status`, `error`) matches
`bot_reply_db.list_pending_replies`'s existing dict output, unchanged by this plan — Task
1 doesn't reshape rows, it passes them through as-is, so no new field-name contract is
introduced. `/reply/api/pending/{id}/approve|reject|retry` are called with the same
paths/methods Task 1 confirms already exist unmodified.

**Scope check:** two files' worth of backend change (one new endpoint, one refactor to
avoid duplicating existing logic) plus three new/modified frontend files — proportionate
to the Stats plan's shape. Setup page, chat-config toggles, and settings form are
explicitly out of scope per Global Constraints and the approved design.
