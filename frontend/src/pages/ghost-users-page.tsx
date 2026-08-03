import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchUsers, type UsersData } from "@/lib/ghost-api";

export function GhostUsersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const q = searchParams.get("q") ?? "";
  const [qInput, setQInput] = useState(q);
  const [data, setData] = useState<UsersData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setQInput(q), [q]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchUsers(page, q)
      .then((d) => {
        if (!cancelled) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [page, q]);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = qInput.trim();
    // Search resets to page 1 (classic form submitted only q).
    setSearchParams(trimmed ? { q: trimmed } : {});
  }

  function goto(p: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(p));
    setSearchParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Users" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">User Directory</h1>
        {data && (
          <Badge variant="secondary">Total Users: {data.total_users}</Badge>
        )}
      </div>

      <form onSubmit={submitSearch} className="flex items-center gap-2">
        <Input
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          placeholder="Search username, ID or name..."
          className="max-w-72"
        />
        <Button type="submit" variant="outline">
          Search
        </Button>
      </form>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!data ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User ID</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>First Name</TableHead>
                <TableHead>Last Name</TableHead>
                <TableHead>Last Seen</TableHead>
                <TableHead>Bot?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.users.map((u) => (
                <TableRow key={u.user_id}>
                  <TableCell>{u.user_id}</TableCell>
                  <TableCell>
                    {u.username ? `@${u.username}` : "—"}
                  </TableCell>
                  <TableCell>{u.first_name}</TableCell>
                  <TableCell>{u.last_name}</TableCell>
                  <TableCell>{u.last_seen}</TableCell>
                  <TableCell>
                    {u.is_bot ? (
                      <Badge className="bg-yellow-500 text-black">BOT</Badge>
                    ) : (
                      <Badge className="bg-green-600 text-white">USER</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {data.users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-muted-foreground">
                    No users found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goto(page - 1)}
            >
              &laquo; Prev
            </Button>
            <span className="text-muted-foreground text-sm">
              Page {data.page} of {data.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => goto(page + 1)}
            >
              Next &raquo;
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
