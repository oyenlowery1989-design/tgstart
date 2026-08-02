# Admin Dashboard Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the incrementally-migrated React frontend with a shadcn/ui + TypeScript admin shell (sidebar + topbar + breadcrumb, React Router, 8 placeholder pages), served unchanged from `dashboard/app.py`'s existing `/app` catch-all.

**Architecture:** `frontend/` is deleted and re-scaffolded as a Vite + React + TypeScript project with Tailwind v4 and shadcn/ui; the official `sidebar-07` block (collapsible icon sidebar + breadcrumb header) provides the layout, adapted to this suite's three nav groups. React Router (`react-router-dom`, basename `/app`) owns client-side routing under the existing FastAPI catch-all; every route renders one shared `NotMigratedPage` component linking out to its Jinja2 equivalent. Nav decision: "Bot Reply" (queue, `/reply`) and "Bot Reply Setup" (`/reply/setup`) are **two separate flat nav entries** under Automation — 8 nav entries, 8 routes total — matching the spec's "queue + setup" wording and keeping nav data and routes generated from one shared list.

**Tech Stack:** Vite 6+, React 19, TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`), shadcn/ui (CLI `npx shadcn@latest`), react-router-dom v7, lucide-react. Backend untouched except one `base.html` edit.

## Global Constraints
- Zero backend routing changes: `dashboard/app.py` is NOT modified this cycle (spec: "serving mechanism is unchanged").
- No new Python dependencies; no new `/api/*` endpoints (spec: "UI scaffolding only").
- Vite config MUST keep `base: "/app/"` so built asset URLs match the existing `/app/assets` `StaticFiles` mount.
- React Router MUST use `basename="/app"` so in-app routes resolve against the `/app/{full_path:path}` catch-all.
- The ONLY Python/template change is `dashboard/templates/base.html`: hardcode the Stats and Bot Reply navbar links to `/stats` and `/reply` (regression guard); Sessions/Chats/Scraping/Ghost Mirror/Utilities lines untouched.
- No auth code: `require_auth` is an app-level dependency already covering `/app/*`.
- No test framework: verification is `npm run build` (includes `tsc -b` type-checking) in `frontend/`, and `python -m py_compile` for touched Python (none expected; `base.html` is a template, verified by the smoke test).
- One reusable `NotMigratedPage` component instantiated per-route with props — no per-page duplicate components.
- Old Jinja2 pages stay reachable; they are the fallback targets: `/sessions`, `/chats`, `/groups`, `/scrape`, `/stats`, `/ghost`, `/reply`, `/reply/setup` (all verified against `dashboard/routes/*.py` router prefixes).

---

### Task 1: Delete old frontend, scaffold Vite + React + TypeScript

**Files:**
- Delete: entire `frontend/` directory (`index.html`, `package.json`, `package-lock.json`, `vite.config.js`, `src/**`)
- Create (via scaffolder): `frontend/` with `index.html`, `package.json`, `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`, `vite.config.ts`, `src/main.tsx`, `src/App.tsx`, `src/index.css`, etc.

**Interfaces:** Produces a compiling Vite React-TS project whose `npm run build` runs `tsc -b && vite build` into `frontend/dist/`. Consumed by every later task.

- [ ] **Step 1: Delete the old frontend directory.**
  ```bash
  rm -rf /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend
  ```
- [ ] **Step 2: Scaffold the new project with the Vite react-ts template.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && npm create vite@latest frontend -- --template react-ts
  ```
- [ ] **Step 3: Install dependencies.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm install
  ```
- [ ] **Step 4: Verify the build script type-checks.** Open `frontend/package.json` and confirm `"build": "tsc -b && vite build"` (the react-ts template's default). If it differs, edit the `scripts` block to exactly:
  ```json
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  }
  ```
- [ ] **Step 5: Set the page title.** Replace the `<title>` line in `frontend/index.html` with:
  ```html
    <title>Telegram Suite</title>
  ```
- [ ] **Step 6: Build check.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build
  ```
  Confirm it exits 0 and `frontend/dist/index.html` exists.
- [ ] **Step 7: Commit.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add -A frontend && git commit -m "shell: replace old frontend with fresh Vite react-ts scaffold"
  ```

---

### Task 2: Tailwind v4, path alias, `base: "/app/"`, shadcn init

**Files:**
- Modify: `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/src/index.css`
- Create (via CLI): `frontend/components.json`, `frontend/src/lib/utils.ts`
- Delete: `frontend/src/App.css`, `frontend/src/assets/react.svg` (template leftovers)

**Interfaces:** Consumes Task 1's scaffold. Produces: `@/` path alias, Tailwind v4 wired via `@tailwindcss/vite`, shadcn configured (`components.json`, `cn()` in `src/lib/utils.ts`, theme variables in `src/index.css`) — required before any `shadcn add` in Task 3.

- [ ] **Step 1: Install Tailwind and node types.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm install tailwindcss @tailwindcss/vite && npm install -D @types/node
  ```
- [ ] **Step 2: Replace `frontend/src/index.css` entirely with:**
  ```css
  @import "tailwindcss";
  ```
  (shadcn init will expand this with theme variables in Step 6.)
- [ ] **Step 3: Replace `frontend/vite.config.ts` entirely with:**
  ```ts
  import path from "node:path";
  import tailwindcss from "@tailwindcss/vite";
  import react from "@vitejs/plugin-react";
  import { defineConfig } from "vite";

  // base: "/app/" — built assets are served by dashboard/app.py's StaticFiles
  // mount at /app/assets and the /app/{path} catch-all. Do not change.
  export default defineConfig({
    base: "/app/",
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  });
  ```
- [ ] **Step 4: Add the path alias to `frontend/tsconfig.json`.** Add `compilerOptions` so the file reads (keep the existing `references` entries exactly as generated):
  ```json
  {
    "files": [],
    "references": [
      { "path": "./tsconfig.app.json" },
      { "path": "./tsconfig.node.json" }
    ],
    "compilerOptions": {
      "baseUrl": ".",
      "paths": {
        "@/*": ["./src/*"]
      }
    }
  }
  ```
- [ ] **Step 5: Add the same alias inside `frontend/tsconfig.app.json`'s existing `compilerOptions` block** (do not remove any generated options; insert these two keys):
  ```json
      "baseUrl": ".",
      "paths": {
        "@/*": ["./src/*"]
      }
  ```
- [ ] **Step 6: Run shadcn init (non-interactive).**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npx shadcn@latest init --yes --base-color neutral
  ```
  Confirm afterwards that `frontend/components.json` and `frontend/src/lib/utils.ts` exist and `frontend/src/index.css` now contains `@import "tailwindcss";` plus `:root`/`.dark` CSS variable blocks.
- [ ] **Step 7: Remove template leftovers and fix `App.tsx`.**
  ```bash
  rm /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/App.css /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/assets/react.svg
  ```
  Replace `frontend/src/App.tsx` entirely with (temporary; deleted in Task 5):
  ```tsx
  export default function App() {
    return <div className="p-4 text-sm">Telegram Suite shell</div>;
  }
  ```
- [ ] **Step 8: Build check.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build
  ```
- [ ] **Step 9: Commit.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add -A frontend && git commit -m "shell: wire tailwind v4, @ alias, base /app/, shadcn init"
  ```

---

### Task 3: Add the `sidebar-07` block, extra components, and react-router-dom

**Files:**
- Create (via CLI): `frontend/src/components/ui/sidebar.tsx`, `button.tsx`, `breadcrumb.tsx`, `separator.tsx`, `card.tsx`, `sheet.tsx`, `tooltip.tsx`, `input.tsx`, `skeleton.tsx` (block dependencies), `frontend/src/hooks/use-mobile.ts`, plus block demo files: `frontend/src/components/app-sidebar.tsx`, `nav-main.tsx`, `nav-projects.tsx`, `nav-user.tsx`, `team-switcher.tsx`, and a generated demo page (path varies by CLI version, e.g. `frontend/src/app/dashboard/page.tsx`)
- Delete: the block's demo files (all except `app-sidebar.tsx`, which Task 4 overwrites) and the demo page
- Modify: `frontend/package.json` (react-router-dom)

**Interfaces:** Consumes Task 2's `components.json`/alias. Produces: shadcn `ui/*` primitives (`Sidebar*`, `Button`, `Card*`, `Breadcrumb*`, `Separator`) and `react-router-dom` — consumed by Tasks 4–5. `sidebar-07` is shadcn's standard collapsible-icon sidebar + breadcrumb-header admin layout block in the official blocks registry.

- [ ] **Step 1: Add the block and the explicitly-needed components.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npx shadcn@latest add sidebar-07 card button breadcrumb separator --yes --overwrite
  ```
- [ ] **Step 2: Install react-router-dom.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm install react-router-dom
  ```
- [ ] **Step 3: Delete the block's demo scaffolding** (everything the block added outside `src/components/ui/`, `src/hooks/`, `src/lib/`, except `app-sidebar.tsx`). First list what the add created:
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git status --porcelain frontend/src
  ```
  Then delete the demo files (adjust only if the listing shows different paths — the rule is: remove every non-`ui/` file the block created except `app-sidebar.tsx`, `hooks/use-mobile.ts`, `lib/utils.ts`):
  ```bash
  rm -f /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/components/nav-main.tsx \
        /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/components/nav-projects.tsx \
        /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/components/nav-user.tsx \
        /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/components/team-switcher.tsx
  rm -rf /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/app
  ```
- [ ] **Step 4: Neutralize `app-sidebar.tsx` so the build passes before Task 4 rewrites it.** Replace `frontend/src/components/app-sidebar.tsx` entirely with:
  ```tsx
  import { Sidebar } from "@/components/ui/sidebar";

  export function AppSidebar() {
    return <Sidebar collapsible="icon" />;
  }
  ```
- [ ] **Step 5: Build check.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build
  ```
- [ ] **Step 6: Commit.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add -A frontend && git commit -m "shell: add shadcn sidebar-07 block, ui primitives, react-router-dom"
  ```

---

### Task 4: Nav data, sidebar, layout, and NotMigratedPage

**Files:**
- Create: `frontend/src/lib/nav.ts`, `frontend/src/components/layout.tsx`, `frontend/src/components/not-migrated-page.tsx`
- Modify: `frontend/src/components/app-sidebar.tsx`

**Interfaces:** Consumes Task 3's `ui/*` primitives and react-router-dom. Produces: `NAV_GROUPS`/`ALL_NAV_ITEMS` (single source of truth for sidebar, breadcrumb, and Task 5's routes; each item's `url` doubles as its Jinja2 fallback href since router paths mirror the classic paths exactly), `Layout` (root layout with `<Outlet />`), `NotMigratedPage` (the one shared placeholder).

- [ ] **Step 1: Create `frontend/src/lib/nav.ts` with:**
  ```ts
  import {
    BarChart3,
    Download,
    Ghost,
    MessageSquare,
    Reply,
    Settings2,
    Users,
    UsersRound,
  } from "lucide-react";
  import type { LucideIcon } from "lucide-react";

  export type NavItem = {
    title: string;
    /** Router path under basename /app; identical to the classic Jinja2 URL,
     *  so it doubles as the placeholder's fallback href. */
    url: string;
    icon: LucideIcon;
  };

  export type NavGroup = {
    label: string;
    items: NavItem[];
  };

  export const NAV_GROUPS: NavGroup[] = [
    {
      label: "Accounts",
      items: [{ title: "Sessions", url: "/sessions", icon: Users }],
    },
    {
      label: "Data",
      items: [
        { title: "Chats", url: "/chats", icon: MessageSquare },
        { title: "Groups", url: "/groups", icon: UsersRound },
        { title: "Scrape", url: "/scrape", icon: Download },
        { title: "Stats", url: "/stats", icon: BarChart3 },
      ],
    },
    {
      label: "Automation",
      items: [
        { title: "Ghost Mirror", url: "/ghost", icon: Ghost },
        { title: "Bot Reply", url: "/reply", icon: Reply },
        { title: "Bot Reply Setup", url: "/reply/setup", icon: Settings2 },
      ],
    },
  ];

  export const ALL_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);
  ```
- [ ] **Step 2: Replace `frontend/src/components/app-sidebar.tsx` entirely with:**
  ```tsx
  import { Link, useLocation } from "react-router-dom";

  import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarRail,
  } from "@/components/ui/sidebar";
  import { NAV_GROUPS } from "@/lib/nav";

  export function AppSidebar() {
    const { pathname } = useLocation();
    return (
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <div className="px-2 py-1.5 text-sm font-semibold group-data-[collapsible=icon]:hidden">
            Telegram Suite
          </div>
        </SidebarHeader>
        <SidebarContent>
          {NAV_GROUPS.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton
                      asChild
                      isActive={pathname === item.url}
                      tooltip={item.title}
                    >
                      <Link to={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroup>
          ))}
        </SidebarContent>
        <SidebarRail />
      </Sidebar>
    );
  }
  ```
- [ ] **Step 3: Create `frontend/src/components/layout.tsx` with:**
  ```tsx
  import { Outlet, useLocation } from "react-router-dom";

  import { AppSidebar } from "@/components/app-sidebar";
  import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbList,
    BreadcrumbPage,
  } from "@/components/ui/breadcrumb";
  import { Separator } from "@/components/ui/separator";
  import {
    SidebarInset,
    SidebarProvider,
    SidebarTrigger,
  } from "@/components/ui/sidebar";
  import { ALL_NAV_ITEMS } from "@/lib/nav";

  export function Layout() {
    const { pathname } = useLocation();
    const current = ALL_NAV_ITEMS.find((item) => item.url === pathname);
    return (
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbPage>
                    {current?.title ?? "Telegram Suite"}
                  </BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </header>
          <main className="flex flex-1 flex-col p-4">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
    );
  }
  ```
- [ ] **Step 4: Create `frontend/src/components/not-migrated-page.tsx` with:**
  ```tsx
  import { Button } from "@/components/ui/button";
  import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
  } from "@/components/ui/card";

  export function NotMigratedPage({
    title,
    fallbackHref,
  }: {
    title: string;
    fallbackHref: string;
  }) {
    return (
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            This page has not been migrated to the new dashboard yet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Plain <a>: escapes the /app router basename for a full-page
              load of the classic Jinja2 page. */}
          <Button asChild>
            <a href={fallbackHref}>Open the classic {title} page</a>
          </Button>
        </CardContent>
      </Card>
    );
  }
  ```
- [ ] **Step 5: Build check** (`Layout`/`NotMigratedPage` are not yet imported by `main.tsx`; unused-file noise is fine, but `tsc -b` must pass).
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build
  ```
- [ ] **Step 6: Commit.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add -A frontend && git commit -m "shell: nav data, app sidebar, layout, shared NotMigratedPage"
  ```

---

### Task 5: Router with basename `/app` and all 8 placeholder routes

**Files:**
- Modify: `frontend/src/main.tsx`
- Delete: `frontend/src/App.tsx`

**Interfaces:** Consumes Task 4's `Layout`, `NotMigratedPage`, `ALL_NAV_ITEMS`. Produces the complete shell app: routes `/app/sessions`, `/app/chats`, `/app/groups`, `/app/scrape`, `/app/stats`, `/app/ghost`, `/app/reply`, `/app/reply/setup`, plus `/app` and unknown paths redirecting to `/app/sessions`.

- [ ] **Step 1: Replace `frontend/src/main.tsx` entirely with:**
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

  const router = createBrowserRouter(
    [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/sessions" replace /> },
          ...ALL_NAV_ITEMS.map((item) => ({
            path: item.url,
            element: (
              <NotMigratedPage title={item.title} fallbackHref={item.url} />
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
- [ ] **Step 2: Delete the temporary App component.**
  ```bash
  rm /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/src/App.tsx
  ```
- [ ] **Step 3: Build check.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build
  ```
  Confirm exit 0 and that `frontend/dist/index.html` references assets under `/app/assets/`:
  ```bash
  grep -o '/app/assets/[^"]*' /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend/dist/index.html
  ```
- [ ] **Step 4: Commit.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add -A frontend && git commit -m "shell: router with /app basename and 8 placeholder routes"
  ```

---

### Task 6: `base.html` regression guard — hardcode Stats and Bot Reply navbar links

**Files:**
- Modify: `dashboard/templates/base.html` (navbar block only)

**Interfaces:** Independent of frontend tasks. Produces the old-navbar behavior Task 7 smoke-tests: Stats/Bot Reply point at the still-working Jinja2 pages instead of the new placeholders.

- [ ] **Step 1: Edit the navbar in `dashboard/templates/base.html`.** Change exactly two lines. Before:
  ```html
  <div class="navbar">
    <a href="/sessions">Sessions</a>
    <a href="/chats">Chats</a>
    <a href="/scrape">Scraping</a>
    <a href="{% if frontend_available %}/app/stats{% else %}/stats{% endif %}">Stats</a>
    <a href="/ghost">Ghost Mirror</a>
    <a href="{% if frontend_available %}/app/reply{% else %}/reply{% endif %}">Bot Reply</a>
    <a href="/utilities/participation">Utilities</a>
  </div>
  ```
  After:
  ```html
  <div class="navbar">
    <a href="/sessions">Sessions</a>
    <a href="/chats">Chats</a>
    <a href="/scrape">Scraping</a>
    <a href="/stats">Stats</a>
    <a href="/ghost">Ghost Mirror</a>
    <a href="/reply">Bot Reply</a>
    <a href="/utilities/participation">Utilities</a>
  </div>
  ```
  (Regression guard from the spec: `/app/stats` and `/app/reply` are placeholders until sub-projects 3 and 4 ship; restore the conditional then. No other lines change; no Python files change.)
- [ ] **Step 2: Verify no Python was touched and the tree diff is only this template.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git diff --stat
  ```
  Expected: only `dashboard/templates/base.html`. (No `.py` touched, so `python -m py_compile` has nothing to check.)
- [ ] **Step 3: Commit.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add dashboard/templates/base.html && git commit -m "shell: hardcode old-navbar Stats/Bot Reply links to /stats and /reply (regression guard)"
  ```

---

### Task 7: End-to-end smoke test against the running dashboard

**Files:** none (verification only)

**Interfaces:** Consumes everything: `frontend/dist/` from Task 5 (makes `FRONTEND_AVAILABLE` true in `dashboard/state.py`), navbar edit from Task 6.

- [ ] **Step 1: Rebuild to guarantee `frontend/dist/` is current.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build
  ```
- [ ] **Step 2: Start the dashboard on a non-default port in the background.** (`dashboard/auth.py` loads `.env`; loopback requests pass without a password, otherwise HTTP Basic with `DASHBOARD_USER`/`DASHBOARD_PASSWORD`.)
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && python -m uvicorn dashboard.app:app --host 127.0.0.1 --port 8123
  ```
  Run this in the background; wait until the log shows `Uvicorn running on http://127.0.0.1:8123`.
- [ ] **Step 3: Build curl auth args from `.env` if a password is set.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && export $(grep -E '^DASHBOARD_(USER|PASSWORD)=' .env 2>/dev/null | xargs) ; AUTH=""; [ -n "$DASHBOARD_PASSWORD" ] && AUTH="-u ${DASHBOARD_USER:-admin}:$DASHBOARD_PASSWORD"; echo "AUTH=$AUTH"
  ```
- [ ] **Step 4: Curl all 8 app routes — each must return 200 with the SPA's index.html.**
  ```bash
  for p in sessions chats groups scrape stats ghost reply reply/setup; do
    code=$(curl -s -o /dev/null -w '%{http_code}' $AUTH "http://127.0.0.1:8123/app/$p")
    echo "/app/$p -> $code"
  done
  ```
  Expected: eight `-> 200` lines. Then confirm the payload is the built SPA shell:
  ```bash
  curl -s $AUTH http://127.0.0.1:8123/app/sessions | grep -o '<title>Telegram Suite</title>'
  curl -s $AUTH http://127.0.0.1:8123/app/sessions | grep -o '/app/assets/[^"]*' | head -3
  ```
  Expected: the title matches and asset URLs start with `/app/assets/` (placeholder text itself is client-rendered, so the HTML check is title + asset paths).
- [ ] **Step 5: Confirm the JS bundle is actually served (catch-all/mount agreement).**
  ```bash
  js=$(curl -s $AUTH http://127.0.0.1:8123/app/sessions | grep -o '/app/assets/[^"]*\.js' | head -1)
  curl -s -o /dev/null -w '%{http_code}\n' $AUTH "http://127.0.0.1:8123$js"
  ```
  Expected: `200`.
- [ ] **Step 6: Confirm the old navbar's regression guard.**
  ```bash
  curl -s $AUTH http://127.0.0.1:8123/sessions | grep -E 'href="/(stats|reply)"'
  curl -s $AUTH http://127.0.0.1:8123/sessions | grep -c '/app/stats\|/app/reply'
  ```
  Expected: the first grep prints `<a href="/stats">Stats</a>` and `<a href="/reply">Bot Reply</a>`; the second prints `0`.
- [ ] **Step 7: Stop the background uvicorn server.**
- [ ] **Step 8: Final full verification.**
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start/frontend && npm run build && cd .. && git status --porcelain
  ```
  If any fixes were made during smoke testing, commit them:
  ```bash
  cd /Users/_monitor/MyData/CODE/vibecode/telegram-start && git add -A && git commit -m "shell: smoke-test fixes"
  ```

---

## Self-Review Notes

**Spec coverage map:**
- "Delete `frontend/` entirely and re-scaffold via shadcn init (Vite, TypeScript, Tailwind)" → Tasks 1–2.
- "Add react-router-dom and shadcn's official dashboard block (sidebar + topbar + breadcrumbs)" → Task 3 (`sidebar-07`, the standard collapsible-icon-sidebar + breadcrumb-header block in shadcn's blocks registry), Task 5 (router, basename `/app`).
- "Adapt its nav data to this suite's pages" / three-group nav (Accounts / Data / Automation) with 8 destinations → Task 4 (`nav.ts`, `app-sidebar.tsx`). Architecture decision stated: Bot Reply queue and setup are two flat nav entries.
- "Every page renders a placeholder Card with a button linking to its Jinja2 equivalent" → Task 4 (`NotMigratedPage`) + Task 5 (8 instantiations via `ALL_NAV_ITEMS.map`). Fallback URLs verified against actual router prefixes in `dashboard/routes/*.py` (`/sessions`, `/chats`, `/groups`, `/scrape`, `/stats`, `/ghost`, `/reply`, `/reply/setup`).
- "`dashboard/app.py` serving mechanism unchanged; no new Python deps; no new `/api/*`" → no task touches `app.py` or any `.py`; Task 6 Step 2 verifies the diff is template-only.
- "Transition regression guard: hardcode base.html Stats/Bot Reply to `/stats`/`/reply`" → Task 6, exact before/after HTML.
- "Testing: npm run build (tsc type-check); py_compile for touched Python" → build check ends every frontend task; no `.py` is touched (verified Task 6 Step 2); Task 7 is the manual smoke test (8×200 on `/app/*`, asset serving, navbar links, server stopped).
- `base: "/app/"` preserved → Task 2 Step 3 (with comment), verified by Task 5 Step 3 and Task 7 Step 5.

**Placeholder scan:** every code step contains complete literal file contents or exact commands; no "implement X" steps and no "same as Task N" cross-references (the only conditional instructions are CLI-output-dependent cleanup in Task 3 Step 3 and env-dependent auth in Task 7 Step 3, both with explicit rules and expected outcomes). The `NotMigratedPage` placeholder page is a spec deliverable, not a plan placeholder.

**Type/name consistency:** `NavItem { title, url, icon }` and `NAV_GROUPS`/`ALL_NAV_ITEMS` defined once in Task 4 Step 1 and consumed with those exact names in Task 4 Steps 2–3 and Task 5 Step 1. `NotMigratedPage` props `{ title, fallbackHref }` (Task 4 Step 4) match Task 5's call site (`fallbackHref={item.url}` — valid because router paths equal classic Jinja2 paths, noted in `nav.ts`). Component names `AppSidebar`, `Layout` match imports across tasks. Task 3 Step 4's temporary `AppSidebar` is fully replaced by Task 4 Step 2.

**Scope check:** no real page content, no new API endpoints, no auth changes, no Jinja2 page retirement, no `app.py` edits — all explicitly out of scope per the spec and absent from every task. Deliberate simplifications: `fallbackHref` collapsed into `url` (they are identical for all 8 pages; split the fields when a rebuilt page's route diverges from its classic URL), single-crumb breadcrumb (add hierarchy when pages gain sub-views), no dark-mode toggle (shadcn theme vars are in place; add when requested).
