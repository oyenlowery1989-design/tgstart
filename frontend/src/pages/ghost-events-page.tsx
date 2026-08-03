import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchEvents, type EventsData } from "@/lib/ghost-api";

// Same six options as the classic events.html filter form.
const EVENT_TYPES = [
  { value: "message_new", label: "New Message" },
  { value: "message_edit", label: "Edits" },
  { value: "message_delete", label: "Deletes" },
  { value: "user_join", label: "Joins" },
  { value: "user_leave", label: "Leaves" },
  { value: "mirror_failed_total", label: "Failures" },
];

export function GhostEventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(
    1,
    Math.floor(Number(searchParams.get("page") ?? "1") || 1),
  );
  const typeFilter = searchParams.get("type") ?? "";
  const [data, setData] = useState<EventsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchEvents(page, typeFilter)
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
  }, [page, typeFilter]);

  function setType(value: string) {
    // Changing the filter resets to page 1 (classic form dropped ?page too).
    setSearchParams(value === "all" ? {} : { type: value });
  }

  function goto(p: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(p));
    setSearchParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Events" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Events Log</h1>
        {data && (
          <Badge variant="secondary">Total Events: {data.total_events}</Badge>
        )}
      </div>

      <Select
        value={typeFilter === "" ? "all" : typeFilter}
        onValueChange={(v) => setType(String(v))}
      >
        <SelectTrigger className="max-w-56">
          <SelectValue placeholder="All Events" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Events</SelectItem>
          {EVENT_TYPES.map((t) => (
            <SelectItem key={t.value} value={t.value}>
              {t.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

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
                <TableHead>Event ID</TableHead>
                <TableHead>Time (UTC)</TableHead>
                <TableHead>Chat ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.events.map((e) => (
                <TableRow key={e.event_id}>
                  <TableCell className="text-muted-foreground text-xs">
                    {e.event_id.slice(0, 8)}
                  </TableCell>
                  <TableCell>{e.ts}</TableCell>
                  <TableCell>{e.chat_id}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{e.event_type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-96">
                    <code className="text-xs break-all whitespace-pre-wrap">
                      {e.summary_json}
                    </code>
                  </TableCell>
                </TableRow>
              ))}
              {data.events.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    No events.
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
