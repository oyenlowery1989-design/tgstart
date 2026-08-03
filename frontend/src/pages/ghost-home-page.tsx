import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
  fetchHome,
  fetchRecentEvents,
  type GhostEvent,
  type HomeData,
} from "@/lib/ghost-api";

const POLL_INTERVAL_MS = 3000;
const FEED_MAX_ROWS = 200;
const HIGHLIGHT_MS = 2000;

function summaryText(s: string | null, max: number): string {
  const text = s ?? "";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

export function GhostHomePage() {
  const [data, setData] = useState<HomeData | null>(null);
  const [feed, setFeed] = useState<GhostEvent[]>([]);
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const lastTsRef = useRef("");

  useEffect(() => {
    let cancelled = false;
    fetchHome()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setFeed(d.recent_events);
        lastTsRef.current = d.recent_events[0]?.ts ?? "";
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Classic index.html poller, translated: every 3s fetch events strictly
  // after the newest ts we have (API returns ASC / oldest-first), prepend so
  // the newest ends up on top, cap at 200 rows, highlight new rows briefly.
  // Starts only once the initial load has primed lastTs — an empty after_ts
  // would return the OLDEST events.
  const loaded = data !== null;
  useEffect(() => {
    if (!loaded) return;
    const id = setInterval(() => {
      fetchRecentEvents(lastTsRef.current)
        .then(({ events }) => {
          if (events.length === 0) return;
          const newest = events[events.length - 1];
          if (newest.ts > lastTsRef.current) {
            lastTsRef.current = newest.ts;
          }
          const newestFirst = [...events].reverse();
          setFeed((prev) => [...newestFirst, ...prev].slice(0, FEED_MAX_ROWS));
          const ids = events.map((e) => e.event_id);
          setFreshIds((prev) => new Set([...prev, ...ids]));
          setTimeout(() => {
            setFreshIds((prev) => {
              const next = new Set(prev);
              for (const eventId of ids) next.delete(eventId);
              return next;
            });
          }, HIGHLIGHT_MS);
        })
        .catch(() => {
          // Classic behavior: poll errors are ignored; next tick retries.
        });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [loaded]);

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <GhostTabs active="Home" />
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-4">
        <GhostTabs active="Home" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Home" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard Overview</h1>
        <Badge variant="secondary">
          v{data.schema_version} | Bump: {data.config_bump}
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-semibold">{data.monitored_count}</div>
            <div className="text-muted-foreground text-sm">Monitored Chats</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-semibold">{data.message_count}</div>
            <div className="text-muted-foreground text-sm">Messages Logged</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-semibold">{data.event_count}</div>
            <div className="text-muted-foreground text-sm">Total Events</div>
          </CardContent>
        </Card>
      </div>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Recent Critical Issues</h2>
        {data.failures.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time (UTC)</TableHead>
                <TableHead>Chat ID</TableHead>
                <TableHead>Error</TableHead>
                <TableHead>Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.failures.map((f) => (
                <TableRow key={f.event_id}>
                  <TableCell>{f.ts}</TableCell>
                  <TableCell>{f.chat_id}</TableCell>
                  <TableCell>
                    <Badge variant="destructive">
                      {summaryText(f.summary_json, 50)}
                    </Badge>
                  </TableCell>
                  <TableCell>{f.event_type}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-center text-green-600">
            No recent critical failures.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Latest Events</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Chat</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Summary</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {feed.map((e) => (
              <TableRow
                key={e.event_id}
                className={
                  freshIds.has(e.event_id)
                    ? "bg-accent transition-colors"
                    : "transition-colors"
                }
              >
                <TableCell>{e.ts}</TableCell>
                <TableCell>{e.chat_id}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{e.event_type}</Badge>
                </TableCell>
                <TableCell>{e.actor_user_id ?? "None"}</TableCell>
                <TableCell className="max-w-96 break-all whitespace-normal">
                  {summaryText(e.summary_json, 80)}
                </TableCell>
              </TableRow>
            ))}
            {feed.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  No events yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <div className="mt-2">
          <Link
            to="/ghost/events"
            className="text-muted-foreground hover:text-foreground text-sm underline underline-offset-3"
          >
            View All Events &raquo;
          </Link>
        </div>
      </section>
    </div>
  );
}
