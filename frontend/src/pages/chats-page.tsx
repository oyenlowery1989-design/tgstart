import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { fetchDialogs, type DialogsData } from "@/lib/chats-api";

export function ChatsPage() {
  const [data, setData] = useState<DialogsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetchDialogs());
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Chats</h1>
          {data && (
            <p className="text-muted-foreground text-sm">
              {data.active_session}
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={() => void refetch()}
        >
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!data && !error && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      )}

      {data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>ID</TableHead>
              <TableHead>Username</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.type}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell className="text-muted-foreground">
                  {r.id}
                </TableCell>
                <TableCell>{r.username ?? ""}</TableCell>
                <TableCell>
                  {(r.type === "GROUP" || r.type === "CHANNEL") && (
                    <Button
                      size="sm"
                      variant="outline"
                      render={<Link to={`/groups/${r.id}/users`} />}
                    >
                      View users
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {data.rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  No dialogs found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}

      {data && (
        <p className="text-muted-foreground text-sm">
          {data.rows.length} dialogs. Saved to{" "}
          <code>3_chat_management/30_data/30_dialogs.csv</code>.
        </p>
      )}
    </div>
  );
}
