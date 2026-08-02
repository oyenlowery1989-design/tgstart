import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

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
import {
  fetchSessionList,
  postForm,
  type SessionListData,
  type SessionResult,
} from "@/lib/sessions-api";

function StatusBadge({ status }: { status: SessionResult["status"] }) {
  if (status === "ACTIVE") {
    return <Badge className="bg-green-600 text-white">ACTIVE</Badge>;
  }
  if (status === "INVALID" || status === "ERROR") {
    return <Badge variant="destructive">{status}</Badge>;
  }
  return <Badge variant="secondary">{status}</Badge>;
}

export function SessionsPage() {
  const [data, setData] = useState<SessionListData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetchSessionList());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  async function handleSwitch(sessionName: string) {
    try {
      await postForm("/sessions/active", { session_name: sessionName });
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    await refetch();
  }

  async function handleDelete(name: string) {
    if (!window.confirm(`Delete session "${name}"?`)) return;
    try {
      await postForm(`/sessions/${encodeURIComponent(name)}/delete`, {});
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    await refetch();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Sessions</h1>
        <div className="flex items-center gap-2">
          <Button render={<Link to="/sessions/login" />} variant="outline">
            Add account (phone)
          </Button>
          <Button render={<Link to="/sessions/login/qr" />} variant="outline">
            Add account (QR)
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {data && data.all_sessions.length > 0 && (
        <label className="flex items-center gap-2 text-sm">
          Active session:
          <select
            className="border-input bg-background h-9 rounded-md border px-3 text-sm"
            value={data.active_session ?? ""}
            onChange={(e) => void handleSwitch(e.target.value)}
          >
            {data.all_sessions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      )}

      {loading && !data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Details</TableHead>
              <TableHead className="w-24" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data?.results ?? []).map((r) => (
              <TableRow key={r.name}>
                <TableCell className="font-medium">{r.name}</TableCell>
                <TableCell>
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell>{r.details}</TableCell>
                <TableCell>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => void handleDelete(r.name)}
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {data && data.results.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground">
                  No sessions yet — add an account with phone or QR login.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
