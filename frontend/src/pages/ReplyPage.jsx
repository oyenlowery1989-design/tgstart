import { useEffect, useState, useCallback } from "react";

const POLL_INTERVAL_MS = 10000;

function StatusBadge({ status }) {
  const styles = {
    sent: "bg-green-900 text-green-300",
    rejected: "bg-yellow-900 text-yellow-300",
    failed: "bg-red-900 text-red-300",
  };
  const cls = styles[status] || "bg-slate-800 text-slate-300";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs ${cls}`}>{status}</span>
  );
}

export default function ReplyPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [rowErrors, setRowErrors] = useState({});

  const fetchQueue = useCallback(() => {
    fetch("/reply/api/queue")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError("Failed to load queue."));
  }, []);

  useEffect(() => {
    fetchQueue();
    const id = setInterval(fetchQueue, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchQueue]);

  async function resolve(id, action) {
    const resp = await fetch(`/reply/api/pending/${id}/${action}`, { method: "POST" });
    if (resp.status === 409) {
      const body = await resp.json();
      setRowErrors((prev) => ({ ...prev, [id]: `Already resolved: ${body.detail || ""}` }));
      return;
    }
    if (!resp.ok) {
      setRowErrors((prev) => ({ ...prev, [id]: `Error: ${resp.status}` }));
      return;
    }
    fetchQueue();
  }

  async function retry(id) {
    const resp = await fetch(`/reply/api/pending/${id}/retry`, { method: "POST" });
    if (!resp.ok) {
      setRowErrors((prev) => ({ ...prev, [id]: `Retry failed: ${resp.status}` }));
      return;
    }
    fetchQueue();
  }

  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!data) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Bot Reply Queue</h1>
      <p className="text-slate-500 text-sm mb-4">
        <a href="/reply/setup" className="text-blue-400 underline">
          Chat setup &amp; settings &raquo;
        </a>
      </p>

      {!data.configured && (
        <p className="bg-yellow-950 border border-yellow-800 text-yellow-300 text-sm rounded px-3 py-2 mb-4">
          Bot Reply is not fully configured — the runner will not start. Set a session on{" "}
          <a href="/reply/setup" className="underline">
            Chat setup &amp; settings
          </a>{" "}
          and ensure <code>BOT_REPLY_APPROVAL_BOT_TOKEN</code> /{" "}
          <code>BOT_REPLY_OPERATOR_USER_ID</code> are set in <code>.env</code>, then
          restart the dashboard.
        </p>
      )}

      <h2 className="text-lg font-semibold mt-6 mb-2">Pending approval</h2>
      <div className="bg-slate-900 border border-slate-800 rounded overflow-hidden">
        {data.pending.length === 0 ? (
          <p className="text-slate-500 text-sm px-3 py-3">Nothing pending.</p>
        ) : (
          data.pending.map((r) => (
            <div key={r.id} className="border-b border-slate-800 last:border-0 px-3 py-3">
              <div className="text-sm text-slate-300">
                <span className="font-medium">{r.chat_title}</span> — {r.source_sender}
              </div>
              <div className="text-sm text-slate-500 mt-1">{r.source_text}</div>
              <div className="text-sm text-slate-100 mt-1">{r.draft_text}</div>
              <div className="mt-2 flex gap-2 items-center">
                <button
                  className="bg-green-600 hover:bg-green-500 text-white text-xs font-medium px-3 py-1 rounded"
                  onClick={() => resolve(r.id, "approve")}
                >
                  Approve
                </button>
                <button
                  className="bg-red-600 hover:bg-red-500 text-white text-xs font-medium px-3 py-1 rounded"
                  onClick={() => resolve(r.id, "reject")}
                >
                  Reject
                </button>
                {rowErrors[r.id] && (
                  <span className="text-red-400 text-xs">{rowErrors[r.id]}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <h2 className="text-lg font-semibold mt-6 mb-2">Approved, sending</h2>
      <div className="bg-slate-900 border border-slate-800 rounded overflow-hidden">
        {data.approved.length === 0 ? (
          <p className="text-slate-500 text-sm px-3 py-3">None waiting to send.</p>
        ) : (
          data.approved.map((r) => (
            <div key={r.id} className="border-b border-slate-800 last:border-0 px-3 py-3">
              <div className="text-sm text-slate-300">
                <span className="font-medium">{r.chat_title}</span> — {r.source_sender}
              </div>
              <div className="text-sm text-slate-500 mt-1">{r.source_text}</div>
              <div className="text-sm text-slate-100 mt-1">{r.draft_text}</div>
            </div>
          ))
        )}
      </div>

      <h2 className="text-lg font-semibold mt-6 mb-2">Recent</h2>
      <div className="bg-slate-900 border border-slate-800 rounded overflow-hidden">
        {data.recent.length === 0 ? (
          <p className="text-slate-500 text-sm px-3 py-3">No recent activity.</p>
        ) : (
          data.recent.map((r) => (
            <div key={r.id} className="border-b border-slate-800 last:border-0 px-3 py-3">
              <div className="text-sm text-slate-300 flex items-center gap-2">
                <StatusBadge status={r.status} />
                <span className="font-medium">{r.chat_title}</span> — {r.source_sender}
              </div>
              <div className="text-sm text-slate-500 mt-1">{r.source_text}</div>
              <div className="text-sm text-slate-100 mt-1">{r.draft_text}</div>
              {r.status === "failed" && r.error && (
                <div className="text-red-400 text-xs mt-1">{r.error}</div>
              )}
              {r.status === "failed" && (
                <div className="mt-2 flex gap-2 items-center">
                  <button
                    className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-3 py-1 rounded"
                    onClick={() => retry(r.id)}
                  >
                    Retry
                  </button>
                  {rowErrors[r.id] && (
                    <span className="text-red-400 text-xs">{rowErrors[r.id]}</span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
