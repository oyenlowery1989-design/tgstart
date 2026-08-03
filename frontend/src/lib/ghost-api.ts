// Shared helpers for the Ghost Mirror pages. Backend endpoints live under
// /ghost (no /app prefix — that's only the SPA router basename). The five
// GET endpoints are the new JSON API; the three POSTs and recent_events_v2
// are the pre-existing endpoints the classic Jinja2 pages already used.

import { csrfToken } from "@/lib/csrf";

/** Row from the events table; summary_json is stored as TEXT (a JSON string). */
export type GhostEvent = {
  event_id: string;
  ts: string;
  chat_id: number;
  event_type: string;
  actor_user_id: number | null;
  summary_json: string | null;
};

export type HomeData = {
  monitored_count: number;
  message_count: number;
  event_count: number;
  failures: GhostEvent[];
  recent_events: GhostEvent[];
  config_bump: string;
  schema_version: string;
};

/**
 * chats row LEFT JOINed with config: every toggle_* is null when the chat
 * has no config row yet — treated as off, matching the classic template's
 * truthiness checks. Only fields the UI reads are typed (house convention).
 */
export type GhostChat = {
  chat_id: number;
  title: string | null;
  type: string | null;
  monitored: number;
  backup_chat_id: number | null;
  member_count: number | null;
  toggle_log_new: number | null;
  toggle_mirror_new: number | null;
  toggle_edits: number | null;
  toggle_deletes: number | null;
  toggle_joins: number | null;
  toggle_admin: number | null;
  toggle_restrict: number | null;
  toggle_invites: number | null;
  toggle_bots: number | null;
  toggle_bio_worker: number | null;
  toggle_reactions: number | null;
};

export type ChatsData = {
  chats: GhostChat[];
  page: number;
  total_pages: number;
  total_chats: number;
};

/** Narrowed chats row for the Setup page (no config join there). */
export type SetupChat = {
  chat_id: number;
  title: string | null;
  type: string | null;
  monitored: number;
  backup_chat_id: number | null;
};

export type Destination = { chat_id: number; title: string | null };

export type SetupData = {
  chats: SetupChat[];
  destinations: Destination[];
  query: string;
};

export type EventsData = {
  events: GhostEvent[];
  page: number;
  total_pages: number;
  total_events: number;
  type_filter: string;
};

export type GhostUser = {
  user_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  last_seen: string | null;
  is_bot: number;
};

export type UsersData = {
  users: GhostUser[];
  page: number;
  total_pages: number;
  total_users: number;
  query: string;
};

/** Mirrors valid_keys in dashboard/routes/ghost_mirror.py api_toggle. */
export type ToggleKey =
  | "toggle_log_new"
  | "toggle_mirror_new"
  | "toggle_edits"
  | "toggle_deletes"
  | "toggle_joins"
  | "toggle_admin"
  | "toggle_restrict"
  | "toggle_invites"
  | "toggle_bots"
  | "toggle_bio_worker"
  | "toggle_reactions";

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Failed to load ${url} (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<T>;
}

export function fetchHome(): Promise<HomeData> {
  return getJson("/ghost/api/home");
}

export function fetchChats(page: number): Promise<ChatsData> {
  return getJson(`/ghost/api/chats?page=${page}`);
}

export function fetchSetup(q: string): Promise<SetupData> {
  return getJson(`/ghost/api/setup?q=${encodeURIComponent(q)}`);
}

export function fetchEvents(page: number, type: string): Promise<EventsData> {
  return getJson(`/ghost/api/events?page=${page}&type=${encodeURIComponent(type)}`);
}

export function fetchUsers(page: number, q: string): Promise<UsersData> {
  return getJson(`/ghost/api/users?page=${page}&q=${encodeURIComponent(q)}`);
}

/** API returns events ASC (oldest first), strictly after afterTs when given. */
export function fetchRecentEvents(afterTs: string): Promise<{ events: GhostEvent[] }> {
  const qs = afterTs ? `?after_ts=${encodeURIComponent(afterTs)}` : "";
  return getJson(`/ghost/api/recent_events_v2${qs}`);
}

async function postOrThrow(url: string, body?: unknown): Promise<void> {
  const headers: Record<string, string> = { "X-CSRF-Token": csrfToken() };
  const init: RequestInit = { method: "POST", headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`Action failed (HTTP ${resp.status})`);
  }
}

export function toggleConfig(chatId: number, key: ToggleKey, value: boolean): Promise<void> {
  return postOrThrow(`/ghost/api/toggle/${chatId}/${key}?value=${value ? 1 : 0}`);
}

export function toggleMonitor(chatId: number, value: boolean): Promise<void> {
  return postOrThrow(`/ghost/api/chats/${chatId}/monitor?value=${value ? 1 : 0}`);
}

export function saveChatMapping(
  chatId: number,
  monitored: boolean,
  backupChatId: number | null,
): Promise<void> {
  return postOrThrow("/ghost/api/chat_mapping", {
    chat_id: chatId,
    monitored,
    backup_chat_id: backupChatId,
  });
}
