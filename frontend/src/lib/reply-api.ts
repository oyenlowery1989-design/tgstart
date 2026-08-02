// Shared helpers for the Bot Reply queue page. Backend endpoints live under
// /reply (no /app prefix — that's only the SPA router basename).

/**
 * Deliberate narrowing, not a mismatch: the backend returns every column of
 * the pending_replies table on every row (chat_id, source_message_id,
 * approval_msg_id, created_at, resolved_at, sent_message_id, ...). The UI
 * only reads these seven fields, so only these are typed.
 */
export type ReplyRow = {
  id: number;
  chat_title: string;
  source_sender: string;
  source_text: string;
  draft_text: string;
  status: string;
  error: string | null;
};

export type QueueData = {
  configured: boolean;
  pending: ReplyRow[];
  approved: ReplyRow[];
  recent: ReplyRow[];
};

export async function fetchQueue(): Promise<QueueData> {
  const resp = await fetch("/reply/api/queue");
  if (!resp.ok) {
    throw new Error(`Failed to load queue (HTTP ${resp.status})`);
  }
  return resp.json() as Promise<QueueData>;
}

export type ResolveAction = "approve" | "reject" | "retry";

/**
 * POSTs an approve/reject/retry action and returns the raw Response.
 * Intentionally does NOT throw on non-OK (unlike fetchQueue above): the
 * caller must distinguish 409 (already resolved elsewhere — e.g. the
 * Telegram-side approval bot won the race) from other failures, so it needs
 * the status code and body, not a thrown Error.
 */
export async function resolvePending(
  id: number,
  action: ResolveAction,
): Promise<Response> {
  return fetch(`/reply/api/pending/${id}/${action}`, { method: "POST" });
}
