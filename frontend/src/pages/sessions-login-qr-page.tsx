import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { wsUrl } from "@/lib/sessions-api";

type QrState = "connecting" | "waiting" | "need_2fa" | "done" | "error";

type QrMessage = {
  state: string;
  qr_png_b64?: string;
  session_name?: string;
  error?: string;
};

const STATUS_TEXT: Record<QrState, string> = {
  connecting: "Connecting...",
  waiting: "Scan with Telegram: Settings → Devices → Link Desktop Device",
  need_2fa: "Two-step verification required.",
  done: "Logged in. Redirecting...",
  error: "Login failed.",
};

export function SessionsLoginQrPage() {
  const navigate = useNavigate();
  const wsRef = useRef<WebSocket | null>(null);
  const [state, setState] = useState<QrState>("connecting");
  const [qrSrc, setQrSrc] = useState<string | null>(null);
  const [sessionName, setSessionName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");

  useEffect(() => {
    // StrictMode double-invokes this effect in dev; the cleanup closes the
    // first socket, so only one QR flow survives. Production mounts once.
    const ws = new WebSocket(wsUrl("/sessions/login/qr/ws"));
    wsRef.current = ws;
    ws.onmessage = (event: MessageEvent<string>) => {
      const data = JSON.parse(event.data) as QrMessage;
      if (data.state === "waiting" && data.qr_png_b64) {
        setQrSrc(`data:image/png;base64,${data.qr_png_b64}`);
        setState("waiting");
      } else if (data.state === "need_2fa") {
        setState("need_2fa");
      } else if (data.state === "done") {
        setSessionName(data.session_name ?? "");
        setState("done");
      } else {
        setError(data.error ?? "Unknown error");
        setState("error");
      }
    };
    ws.onerror = () => {
      setError("WebSocket connection failed");
      setState("error");
    };
    return () => {
      wsRef.current = null;
      ws.close();
    };
  }, []);

  useEffect(() => {
    if (state !== "done") return;
    const t = setTimeout(() => navigate("/sessions"), 1000);
    return () => clearTimeout(t);
  }, [state, navigate]);

  function send2fa() {
    wsRef.current?.send(JSON.stringify({ password }));
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Login via QR Code</CardTitle>
        <CardDescription>
          {state === "done" && sessionName
            ? `Logged in as ${sessionName}. Redirecting...`
            : STATUS_TEXT[state]}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {qrSrc && state === "waiting" && (
          <img src={qrSrc} alt="Telegram login QR code" className="max-w-75" />
        )}
        {state === "need_2fa" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send2fa();
            }}
          >
            <Input
              type="password"
              placeholder="2FA password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={!password}>
              Submit password
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
