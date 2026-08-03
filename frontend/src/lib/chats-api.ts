// Shared helpers for the Chats page. Backend endpoints live under /chats
// (no /app prefix — that's only the SPA router basename).

export type DialogRow = {
  type: string;
  name: string;
  id: number;
  username: string | null;
};

export type DialogsData = {
  active_session: string;
  rows: DialogRow[];
};

export async function fetchDialogs(): Promise<DialogsData> {
  const resp = await fetch("/chats/api/dialogs");
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Failed to load dialogs (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<DialogsData>;
}
