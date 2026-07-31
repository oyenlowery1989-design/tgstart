import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import StatTile from "../components/StatTile.jsx";

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
        <>
          <div className="flex gap-3 mb-4">
            <StatTile label="Total scanned" value={result.total_scanned} />
            <StatTile label="Unique senders" value={result.unique_senders} />
            <StatTile
              label="Busiest hour"
              value={
                result.busiest_hour === null || result.busiest_hour === undefined
                  ? "—"
                  : `${String(result.busiest_hour).padStart(2, "0")}:00`
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded p-3">
              <div className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                Top Users
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={result.top_users.map(([name, count]) => ({ name, count }))}
                  layout="vertical"
                >
                  <XAxis type="number" stroke="#64748b" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#64748b"
                    fontSize={11}
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded p-3">
              <div className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                Peak Hours
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={result.peak_hours.map(([hour, count]) => ({
                    hour: `${String(hour).padStart(2, "0")}:00`,
                    count,
                  }))}
                >
                  <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
