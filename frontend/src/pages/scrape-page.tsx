import { useEffect, useRef, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { fetchSessionInfo, wsUrl } from "@/lib/scrape-api";
import type { ScanMessage } from "@/lib/scrape-api";

type ScanProgress = { current: number; total: number; message: string };

export function ScrapePage() {
  const wsRef = useRef<WebSocket | null>(null);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [groupId, setGroupId] = useState("");
  const [keyword, setKeyword] = useState("");
  const [startswith, setStartswith] = useState("");
  const [sinceDate, setSinceDate] = useState("");
  const [messageLimit, setMessageLimit] = useState("");
  const [resume, setResume] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [done, setDone] = useState(false);
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

  // Close any in-flight scrape socket on unmount.
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  function startScrape() {
    const trimmedGroupId = groupId.trim();
    if (!/^-?\d+$/.test(trimmedGroupId)) {
      setError("Group ID must be an integer (e.g. -1001234567890)");
      return;
    }
    const trimmedLimit = messageLimit.trim();
    if (trimmedLimit && !/^\d+$/.test(trimmedLimit)) {
      setError("Message limit must be a positive integer");
      return;
    }
    setError(null);
    setDone(false);
    setProgress({ current: 0, total: 0, message: "Connecting..." });
    setScanning(true);

    const ws = new WebSocket(wsUrl("/scrape/ws"));
    wsRef.current = ws;
    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          group_id: Number(trimmedGroupId),
          keyword: keyword.trim() || undefined,
          startswith: startswith.trim() || undefined,
          since_date: sinceDate.trim() || undefined,
          message_limit: trimmedLimit ? Number(trimmedLimit) : undefined,
          resume,
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
      setProgress({
        current: data.current,
        total: data.total,
        message: data.message,
      });
      if (data.done) {
        setDone(true);
        setScanning(false);
        ws.close();
      }
    };
    ws.onerror = () => {
      setError("WebSocket connection failed");
      setScanning(false);
    };
    ws.onclose = () => setScanning(false);
  }

  const progressPct =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : done
        ? 100
        : 0;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Extract Links</CardTitle>
          <CardDescription>
            Scan a group's messages for links. Session:{" "}
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
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              startScrape();
            }}
          >
            <div className="flex flex-wrap gap-2">
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
                placeholder="Keyword filter (optional)"
                className="max-w-52"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                disabled={scanning}
              />
              <Input
                type="text"
                placeholder="Starts-with filter (optional)"
                className="max-w-52"
                value={startswith}
                onChange={(e) => setStartswith(e.target.value)}
                disabled={scanning}
              />
              <Input
                type="text"
                placeholder="Since date YYYY-MM-DD (optional)"
                className="max-w-52"
                value={sinceDate}
                onChange={(e) => setSinceDate(e.target.value)}
                disabled={scanning}
              />
              <Input
                type="text"
                inputMode="numeric"
                placeholder="Message limit (default 500)"
                className="max-w-45"
                value={messageLimit}
                onChange={(e) => setMessageLimit(e.target.value)}
                disabled={scanning}
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="resume"
                checked={resume}
                onCheckedChange={(checked) => setResume(checked === true)}
                disabled={scanning}
              />
              <Label htmlFor="resume">Resume from checkpoint</Label>
            </div>
            <Button
              type="submit"
              className="w-fit"
              disabled={scanning || !groupId.trim()}
            >
              {scanning ? "Scanning..." : "Start"}
            </Button>
          </form>
          {progress && (
            <div className="flex flex-col gap-1">
              <Progress value={progressPct} />
              <p className="text-muted-foreground text-sm">
                {progress.message}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
