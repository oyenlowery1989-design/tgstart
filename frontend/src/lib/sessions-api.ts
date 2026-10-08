// Shared helpers for the Sessions pages. Backend endpoints live under
// /sessions (no /app prefix — that's only the SPA router basename).

import { csrfToken } from "@/lib/csrf";

export type SessionResult = {
  name: string;
  status: "ACTIVE" | "INVALID" | "ERROR" | "UNKNOWN";
  details: string;
  phone?: string;
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
 *
 * All of these endpoints require the CSRF token as a form field (not a
 * header) since the backend validates them the same way as native <form>
 * posts — see dashboard/csrf.py's require_csrf_form.
 */
export async function postForm(
  url: string,
  data: Record<string, string>,
): Promise<Response> {
  const resp = await fetch(url, {
    method: "POST",
    body: new URLSearchParams({ ...data, csrf_token: csrfToken() }),
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
