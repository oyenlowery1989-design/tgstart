import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { fetchSessionInfo, wsUrl } from "@/lib/stats-api";
import type { ScanMessage, ScanResult } from "@/lib/stats-api";

type ScanProgress = { current: number; total: number; message: string };

export function StatsPage() {
  const wsRef = useRef<WebSocket | null>(null);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [groupId, setGroupId] = useState("");
  const [limit, setLimit] = useState("");
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSessionInfo()
      .then((info) => {
        if (!cancelled) setActiveSession(info.active_session);
      })
      .catch(() => {
        if (!cancelled) setActiveSession(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Close any in-flight scan socket on unmount.
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  function startScan() {
    const trimmedGroupId = groupId.trim();
    if (!/^-?\d+$/.test(trimmedGroupId)) {
      setError("Group ID must be an integer (e.g. -1001234567890)");
      return;
    }
    const trimmedLimit = limit.trim();
    if (trimmedLimit && !/^\d+$/.test(trimmedLimit)) {
      setError("Limit must be a positive integer");
      return;
    }
    setError(null);
    setResult(null);
    setProgress({ current: 0, total: 0, message: "Connecting..." });
    setScanning(true);

    const ws = new WebSocket(wsUrl("/api/stats/ws"));
    wsRef.current = ws;
    ws.onopen = () => {
      // JSON.stringify drops undefined-valued keys, so limit is omitted
      // entirely when blank and the server default (2000) applies.
      ws.send(
        JSON.stringify({
          group_id: Number(trimmedGroupId),
          limit: trimmedLimit ? Number(trimmedLimit) : undefined,
        }),
      );
    };
    ws.onmessage = (event: MessageEvent<string>) => {
      let data: ScanMessage;
      try {
        data = JSON.parse(event.data) as ScanMessage;
      } catch {
        setError("Received an unreadable message from the server");
        setScanning(false);
        ws.close();
        return;
      }
      if ("error" in data) {
        setError(data.error);
        setScanning(false);
        ws.close();
        return;
      }
      if (data.done) {
        setResult(data);
        setScanning(false);
        ws.close();
        return;
      }
      setProgress({
        current: data.current,
        total: data.total,
        message: data.message,
      });
    };
    ws.onerror = () => {
      setError("WebSocket connection failed");
      setScanning(false);
    };
  }

  const progressPct =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  const topUsersData =
    result?.top_users.map(([name, count]) => ({ name, count })) ?? [];
  const peakHoursData =
    result?.peak_hours.map(([hour, count]) => ({
      hour: `${String(hour).padStart(2, "0")}:00`,
      count,
    })) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Group Stats</CardTitle>
          <CardDescription>
            Scan a group's recent messages for activity stats. Session:{" "}
            {activeSession ?? "none"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <form
            className="flex flex-wrap gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              startScan();
            }}
          >
            <Input
              type="text"
              inputMode="numeric"
              placeholder="Group ID (e.g. -1001234567890)"
              className="max-w-60"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              disabled={scanning}
            />
            <Input
              type="text"
              inputMode="numeric"
              placeholder="Limit (default 2000)"
              className="max-w-45"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              disabled={scanning}
            />
            <Button type="submit" disabled={scanning || !groupId.trim()}>
              {scanning ? "Scanning..." : "Scan"}
            </Button>
          </form>
          {scanning && progress && (
            <div className="flex flex-col gap-1">
              <Progress value={progressPct} />
              <p className="text-sm text-muted-foreground">
                {progress.message}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardHeader>
                <CardDescription>Total scanned</CardDescription>
                <CardTitle className="text-2xl">
                  {result.total_scanned}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Unique senders</CardDescription>
                <CardTitle className="text-2xl">
                  {result.unique_senders}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Busiest hour</CardDescription>
                <CardTitle className="text-2xl">
                  {result.busiest_hour !== null
                    ? `${String(result.busiest_hour).padStart(2, "0")}:00`
                    : "—"}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Top Users</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topUsersData}>
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="var(--chart-1)" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Peak Hours</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={peakHoursData}>
                    <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="var(--chart-2)" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
