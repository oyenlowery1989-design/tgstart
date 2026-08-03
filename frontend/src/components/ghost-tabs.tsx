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
