// Shared helpers for the Stats page. Backend endpoints live under
// /api/stats (top-level prefix — NOT nested under the /stats page route).
//
// wsUrl is intentionally duplicated from sessions-api.ts: page modules do
// not import from each other. A future sub-project may hoist shared
// helpers into a common lib/api.ts.

export type SessionInfo = {
  active_session: string | null;
  all_sessions: string[];
};

/** Streaming progress frame. `done` is absent (or false) until the scan finishes. */
export type ScanProgressMessage = {
  current: number;
  total: number;
  message: string;
  done?: false;
};

/**
 * Final frame. `top_users` / `peak_hours` are arrays of tuples (Python
 * tuples serialize as JSON arrays): [name, count, pct] and [hour, count].
 */
export type ScanResult = {
  current: number;
  total: number;
  message: string;
  done: true;
  top_users: [string, number, number][];
  peak_hours: [number, number][];
  total_scanned: number;
  unique_senders: number;
  busiest_hour: number | null;
};

/** Sent by ws_session when there is no active session; has no other keys. */
export type ScanErrorMessage = {
  error: string;
};

export type ScanMessage = ScanProgressMessage | ScanResult | ScanErrorMessage;

export async function fetchSessionInfo(): Promise<SessionInfo> {
  const resp = await fetch("/api/stats/session");
  if (!resp.ok) {
    throw new Error(`Failed to load session info (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<SessionInfo>;
}

export function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}
