import { useEffect, useState } from "react";

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

export default function StatsPage() {
  const [session, setSession] = useState(null);
  const [groupId, setGroupId] = useState("");
  const [limit, setLimit] = useState("2000");
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch("/api/stats/session")
      .then((r) => r.json())
      .then(setSession)
      .catch(() => setSession({ active_session: null, all_sessions: [] }));
  }, []);

  function startScan() {
    setError(null);
    setResult(null);
    setProgress(0);
    setStatus("Connecting...");
    setScanning(true);

    const ws = new WebSocket(wsUrl("/api/stats/ws"));
    ws.onopen = () => {
      ws.send(JSON.stringify({ group_id: groupId, limit }));
    };
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.error) {
        setError(data.error);
        setScanning(false);
        return;
      }
      setStatus(data.message || "");
      if (data.total) {
        setProgress(Math.round((data.current / data.total) * 100));
      }
      if (data.done) {
        setResult(data);
        setScanning(false);
      }
    };
    ws.onerror = () => {
      setError("WebSocket connection error.");
      setScanning(false);
    };
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Group Analytics</h1>
      <p className="text-slate-500 text-sm mb-4">
        Session:{" "}
        {session?.active_session ? (
          session.active_session
        ) : (
          <a href="/sessions" className="text-blue-400 underline">
            no active session — set one
          </a>
        )}
      </p>

      <div className="flex gap-2 mb-4">
        <input
          className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm flex-1"
          placeholder="Group ID"
          value={groupId}
          onChange={(e) => setGroupId(e.target.value)}
        />
        <input
          className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm w-32"
          placeholder="Limit: 2000"
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
        />
        <button
          className="bg-blue-500 hover:bg-blue-400 disabled:opacity-50 text-white text-sm font-medium px-4 py-1.5 rounded"
          onClick={startScan}
          disabled={scanning || !groupId}
        >
          Scan
        </button>
      </div>

      {(scanning || status) && (
        <div className="mb-4">
          <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-slate-500 text-xs mt-1">{status}</p>
        </div>
      )}

      {error && <p className="text-red-400 text-sm mb-4">Error: {error}</p>}

      {result && (
        <pre className="text-xs text-slate-400 bg-slate-900 p-3 rounded overflow-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
