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
