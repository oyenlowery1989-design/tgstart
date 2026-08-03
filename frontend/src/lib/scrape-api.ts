// Shared helpers for the Scrape page. Backend endpoints live under /scrape
// (no /app prefix — that's only the SPA router basename).
//
// wsUrl is intentionally duplicated from stats-api.ts/groups-api.ts: page
// modules do not import from each other. A future sub-project may hoist
// shared helpers into a common lib/api.ts.

export type SessionInfo = {
  active_session: string | null;
  all_sessions: string[];
};

export type ScrapeParams = {
  group_id: number;
  keyword?: string;
  startswith?: string;
  since_date?: string;
  message_limit?: number;
  resume: boolean;
};

export type ScanProgressMessage = {
  current: number;
  total: number;
  message: string;
  done?: false;
};

export type ScanDoneMessage = {
  current: number;
  total: number;
  message: string;
  done: true;
};

/** Sent by ws_session when there is no active session; has no other keys. */
export type ScanErrorMessage = {
  error: string;
};

export type ScanMessage = ScanProgressMessage | ScanDoneMessage | ScanErrorMessage;

export async function fetchSessionInfo(): Promise<SessionInfo> {
  const resp = await fetch("/scrape/api/session");
  if (!resp.ok) {
    throw new Error(`Failed to load session info (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<SessionInfo>;
}

export function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}
