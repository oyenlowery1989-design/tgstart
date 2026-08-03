import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { wsUrl, type ScanMessage } from "@/lib/groups-api";

type ScanProgress = { current: number; total: number; message: string };

export function GroupUsersPage() {
  const { groupId } = useParams<{ groupId: string }>();
  const wsRef = useRef<WebSocket | null>(null);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProgress({ current: 0, total: 0, message: "Connecting..." });
    setDone(false);
    setError(null);

    const ws = new WebSocket(wsUrl(`/groups/${groupId}/users/ws`));
    wsRef.current = ws;
    ws.onmessage = (event: MessageEvent<string>) => {
      let data: ScanMessage;
      try {
        data = JSON.parse(event.data) as ScanMessage;
      } catch {
        setError("Received an unreadable message from the server");
        return;
      }
      if ("error" in data) {
        setError(data.error);
        return;
      }
      setProgress({
        current: data.current,
        total: data.total,
        message: data.message,
      });
      if (data.done) setDone(true);
    };
    ws.onerror = () => setError("WebSocket connection failed");

    return () => ws.close();
  }, [groupId]);

  const progressPct =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : done
        ? 100
        : 0;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Group Users: {groupId}</h1>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!error && progress && (
        <div className="flex flex-col gap-1">
          <Progress value={progressPct} />
          <p className="text-muted-foreground text-sm">{progress.message}</p>
        </div>
      )}
    </div>
  );
}
