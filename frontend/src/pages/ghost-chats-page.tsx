import { Fragment, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Settings2 } from "lucide-react";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchChats,
  toggleConfig,
  toggleMonitor,
  type ChatsData,
  type GhostChat,
  type ToggleKey,
} from "@/lib/ghost-api";

const CORE_TOGGLES: { key: ToggleKey; label: string }[] = [
  { key: "toggle_log_new", label: "Log New" },
  { key: "toggle_mirror_new", label: "Mirror New" },
  { key: "toggle_edits", label: "Log Edits" },
  { key: "toggle_deletes", label: "Log Deletes" },
  { key: "toggle_joins", label: "Log Joins" },
];

const ADVANCED_TOGGLES: { key: ToggleKey; label: string }[] = [
  { key: "toggle_admin", label: "Admin" },
  { key: "toggle_restrict", label: "Restrict" },
  { key: "toggle_invites", label: "Invites" },
  { key: "toggle_bots", label: "Bots" },
  { key: "toggle_bio_worker", label: "Bio" },
  { key: "toggle_reactions", label: "Reactions" },
];

export function GhostChatsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const [data, setData] = useState<ChatsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    try {
      setData(await fetchChats(page));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [page]);

  useEffect(() => {
    setData(null);
    void load();
  }, [load]);

  function patchChat(chatId: number, patch: Partial<GhostChat>) {
    setData((prev) =>
      prev
        ? {
            ...prev,
            chats: prev.chats.map((c) =>
              c.chat_id === chatId ? { ...c, ...patch } : c,
            ),
          }
        : prev,
    );
  }

  // Optimistic flip; on failure surface the error and resync from the server
  // (the classic page reloaded the whole window on a failed toggle).
  async function handleConfig(chatId: number, key: ToggleKey, value: boolean) {
    patchChat(chatId, { [key]: value ? 1 : 0 } as Partial<GhostChat>);
    try {
      await toggleConfig(chatId, key, value);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      void load();
    }
  }

  async function handleMonitor(chatId: number, value: boolean) {
    patchChat(chatId, { monitored: value ? 1 : 0 });
    try {
      await toggleMonitor(chatId, value);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      void load();
    }
  }

  function toggleExpanded(chatId: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(chatId)) {
        next.delete(chatId);
      } else {
        next.add(chatId);
      }
      return next;
    });
  }

  function goto(p: number) {
    const next = new URLSearchParams(searchParams);
    next.set("page", String(p));
    setSearchParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Chats" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Chats Management</h1>
        {data && <Badge variant="secondary">Total: {data.total_chats}</Badge>}
      </div>

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
                <TableHead>Monitor</TableHead>
                <TableHead>Title (Type)</TableHead>
                <TableHead>Backup Chat</TableHead>
                <TableHead>Members</TableHead>
                {CORE_TOGGLES.map((t) => (
                  <TableHead key={t.key}>{t.label}</TableHead>
                ))}
                <TableHead>Adv</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.chats.map((c) => (
                <Fragment key={c.chat_id}>
                  <TableRow>
                    <TableCell>
                      <Switch
                        checked={c.monitored === 1}
                        onCheckedChange={(checked) =>
                          void handleMonitor(c.chat_id, checked)
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{c.title}</div>
                      <div className="text-muted-foreground text-xs">
                        {c.type} | ID: {c.chat_id}
                      </div>
                    </TableCell>
                    <TableCell>{c.backup_chat_id}</TableCell>
                    <TableCell>{c.member_count}</TableCell>
                    {CORE_TOGGLES.map((t) => (
                      <TableCell key={t.key}>
                        <Switch
                          checked={!!c[t.key]}
                          onCheckedChange={(checked) =>
                            void handleConfig(c.chat_id, t.key, checked)
                          }
                        />
                      </TableCell>
                    ))}
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label="Advanced toggles"
                        onClick={() => toggleExpanded(c.chat_id)}
                      >
                        <Settings2 />
                      </Button>
                    </TableCell>
                  </TableRow>
                  {expanded.has(c.chat_id) && (
                    <TableRow className="bg-muted/50">
                      <TableCell colSpan={10}>
                        <div className="flex flex-wrap items-center gap-6 px-2 py-1">
                          <span className="font-medium">Advanced:</span>
                          {ADVANCED_TOGGLES.map((t) => (
                            <label
                              key={t.key}
                              className="flex items-center gap-2 text-sm"
                            >
                              {t.label}
                              <Switch
                                checked={!!c[t.key]}
                                onCheckedChange={(checked) =>
                                  void handleConfig(c.chat_id, t.key, checked)
                                }
                              />
                            </label>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))}
              {data.chats.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} className="text-muted-foreground">
                    No chats.
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
