import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { GhostTabs } from "@/components/ghost-tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  fetchSetup,
  saveChatMapping,
  type Destination,
  type SetupChat,
  type SetupData,
} from "@/lib/ghost-api";

type SaveState = "idle" | "saving" | "error";

function SetupRow({
  chat,
  destinations,
}: {
  chat: SetupChat;
  destinations: Destination[];
}) {
  const [monitored, setMonitored] = useState(chat.monitored === 1);
  const [backup, setBackup] = useState<number | null>(chat.backup_chat_id);
  const [saveState, setSaveState] = useState<SaveState>("idle");

  async function save() {
    setSaveState("saving");
    try {
      await saveChatMapping(chat.chat_id, monitored, backup);
      setSaveState("idle");
    } catch {
      setSaveState("error");
    }
  }

  let status: React.ReactNode;
  if (saveState === "saving") {
    status = <Badge variant="secondary">Saving...</Badge>;
  } else if (saveState === "error") {
    status = <Badge variant="destructive">Error</Badge>;
  } else if (monitored && backup === null) {
    status = <Badge className="bg-yellow-500 text-black">No Backup Set!</Badge>;
  } else if (monitored) {
    status = <Badge className="bg-green-600 text-white">Active</Badge>;
  } else {
    status = <span className="text-muted-foreground">Inactive</span>;
  }

  return (
    <TableRow>
      <TableCell className="text-center">
        <Switch
          checked={monitored}
          onCheckedChange={(checked) => setMonitored(checked)}
        />
      </TableCell>
      <TableCell>
        <div className="font-medium">{chat.title}</div>
        <div className="text-muted-foreground text-xs">{chat.chat_id}</div>
      </TableCell>
      <TableCell>
        <Badge variant="secondary">{chat.type}</Badge>
      </TableCell>
      <TableCell>
        <Select
          value={backup === null ? "none" : String(backup)}
          onValueChange={(v) =>
            setBackup(String(v) === "none" ? null : Number(v))
          }
        >
          <SelectTrigger className="w-full max-w-72">
            <SelectValue placeholder="-- No Backup / Select --" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">-- No Backup / Select --</SelectItem>
            {destinations
              .filter((d) => d.chat_id !== chat.chat_id)
              .map((d) => (
                <SelectItem key={d.chat_id} value={String(d.chat_id)}>
                  {d.title} ({d.chat_id})
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>{status}</TableCell>
      <TableCell>
        <Button size="sm" disabled={saveState === "saving"} onClick={() => void save()}>
          Save
        </Button>
      </TableCell>
    </TableRow>
  );
}

export function GhostSetupPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const [qInput, setQInput] = useState(q);
  const [data, setData] = useState<SetupData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setQInput(q), [q]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchSetup(q)
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
  }, [q]);

  function submitFilter(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = qInput.trim();
    setSearchParams(trimmed ? { q: trimmed } : {});
  }

  return (
    <div className="flex flex-col gap-4">
      <GhostTabs active="Setup" />

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Setup &amp; Mapping</h1>
        {data && (
          <Badge variant="secondary">Total Sources: {data.chats.length}</Badge>
        )}
      </div>

      <form onSubmit={submitFilter} className="flex items-center gap-2">
        <Input
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          placeholder="Filter by Title..."
          className="max-w-64"
        />
        <Button type="submit" variant="outline">
          Filter
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
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Monitor</TableHead>
              <TableHead>Source Chat</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Backup Destination</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.chats.map((chat) => (
              <SetupRow
                key={`${q}:${chat.chat_id}`}
                chat={chat}
                destinations={data.destinations}
              />
            ))}
            {data.chats.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground">
                  No chats match.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
