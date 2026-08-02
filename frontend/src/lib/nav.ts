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
   *  so it doubles as the placeholder's fallback href by default. */
  url: string;
  /** Overrides the placeholder's fallback href when the classic Jinja2 UI
   *  has no page at `url` itself. Defaults to `url` when absent. */
  fallbackHref?: string;
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
      {
        title: "Groups",
        url: "/groups",
        // No classic /groups page exists — you view a group's users from a
        // link inside the Chats list, so fall back there instead.
        fallbackHref: "/chats",
        icon: UsersRound,
      },
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
