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
import { ReplyPage } from "@/pages/reply-page";
import { SessionsLoginPhonePage } from "@/pages/sessions-login-phone-page";
import { SessionsLoginQrPage } from "@/pages/sessions-login-qr-page";
import { SessionsPage } from "@/pages/sessions-page";
import { StatsPage } from "@/pages/stats-page";

const MIGRATED_URLS = ["/sessions", "/stats", "/reply", "/chats"];

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
