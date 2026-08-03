// Shared helpers for the Group Users page. Backend endpoints live under
// /groups/{group_id}/users/ws (no /app prefix — that's only the SPA router
// basename).
//
// wsUrl is intentionally duplicated from stats-api.ts: page modules do not
// import from each other. A future sub-project may hoist shared helpers
// into a common lib/api.ts.

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

export function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}
