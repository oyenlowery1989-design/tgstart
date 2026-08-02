import { useCallback, useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchQueue, resolvePending, type QueueData } from "@/lib/reply-api";

const POLL_INTERVAL_MS = 10000;

function StatusBadge({ status }: { status: string }) {
  if (status === "sent") {
    return <Badge className="bg-green-600 text-white">sent</Badge>;
  }
  if (status === "rejected" || status === "failed") {
    return <Badge variant="destructive">{status}</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export function ReplyPage() {
  const [data, setData] = useState<QueueData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});

  const refetch = useCallback(async () => {
    try {
      setData(await fetchQueue());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void refetch();
    const id = setInterval(() => void refetch(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refetch]);

  function setRowError(id: number, msg: string) {
    setRowErrors((prev) => ({ ...prev, [id]: msg }));
  }

  function clearRowError(id: number) {
    setRowErrors((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function handleResolve(id: number, action: "approve" | "reject") {
    const resp = await resolvePending(id, action);
    if (resp.status === 409) {
      const body = (await resp.json()) as { detail?: string };
      setRowError(id, `Already resolved: ${body.detail ?? ""}`);
      return;
    }
    if (!resp.ok) {
      setRowError(id, `Error: ${resp.status}`);
      return;
    }
    clearRowError(id);
    void refetch();
  }

  async function handleRetry(id: number) {
    const resp = await resolvePending(id, "retry");
    if (!resp.ok) {
      setRowError(id, `Retry failed: ${resp.status}`);
      return;
    }
    clearRowError(id);
    void refetch();
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-9 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Bot Reply Queue</h1>
        <a
          href="/reply/setup"
          className="text-muted-foreground hover:text-foreground text-sm underline underline-offset-3"
        >
          Chat setup &amp; settings &raquo;
        </a>
      </div>

      {!data.configured && (
        <Alert>
          <AlertTitle>Bot Reply not fully configured</AlertTitle>
          <AlertDescription>
            The runner will not start. Set a session on{" "}
            <a href="/reply/setup">Chat setup &amp; settings</a> and ensure{" "}
            <code>BOT_REPLY_APPROVAL_BOT_TOKEN</code> /{" "}
            <code>BOT_REPLY_OPERATOR_USER_ID</code> are set in{" "}
            <code>.env</code>, then restart the dashboard.
          </AlertDescription>
        </Alert>
      )}

      <section>
        <h2 className="mb-2 text-lg font-semibold">Pending approval</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Chat</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Draft</TableHead>
              <TableHead className="w-56">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.pending.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.chat_title}</TableCell>
                <TableCell>{r.source_sender}</TableCell>
                <TableCell className="text-muted-foreground max-w-64 whitespace-normal">
                  {r.source_text}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal">
                  {r.draft_text}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      className="bg-green-600 text-white hover:bg-green-500"
                      onClick={() => void handleResolve(r.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => void handleResolve(r.id, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                  {rowErrors[r.id] && (
                    <div className="text-destructive mt-1 text-xs">
                      {rowErrors[r.id]}
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {data.pending.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  Nothing pending.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Approved, sending</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Chat</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Draft</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.approved.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.chat_title}</TableCell>
                <TableCell>{r.source_sender}</TableCell>
                <TableCell className="text-muted-foreground max-w-64 whitespace-normal">
                  {r.source_text}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal">
                  {r.draft_text}
                </TableCell>
              </TableRow>
            ))}
            {data.approved.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  None waiting to send.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Recent</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Chat</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Message</TableHead>
              <TableHead>Draft</TableHead>
              <TableHead className="w-40">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.recent.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell className="font-medium">{r.chat_title}</TableCell>
                <TableCell>{r.source_sender}</TableCell>
                <TableCell className="text-muted-foreground max-w-64 whitespace-normal">
                  {r.source_text}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal">
                  {r.draft_text}
                  {r.status === "failed" && r.error && (
                    <div className="text-destructive mt-1 text-xs">
                      {r.error}
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  {r.status === "failed" && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleRetry(r.id)}
                      >
                        Retry
                      </Button>
                      {rowErrors[r.id] && (
                        <span className="text-destructive text-xs">
                          {rowErrors[r.id]}
                        </span>
                      )}
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {data.recent.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground">
                  No recent activity.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>
    </div>
  );
}
