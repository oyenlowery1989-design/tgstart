import { useState } from "react";
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
import { postForm } from "@/lib/sessions-api";

type LoginResponse = {
  status: string;
  flow_id?: string;
  error?: string;
};

const STEP_DESCRIPTIONS = {
  phone: "Enter your phone number in international format.",
  code: "Enter the code Telegram just sent you.",
  "2fa": "This account has two-step verification. Enter your password.",
} as const;

export function SessionsLoginPhonePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"phone" | "code" | "2fa">("phone");
  const [flowId, setFlowId] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(
    url: string,
    data: Record<string, string>,
  ): Promise<LoginResponse | null> {
    setBusy(true);
    setError(null);
    try {
      const resp = await postForm(url, data);
      return (await resp.json()) as LoginResponse;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function sendPhone() {
    const r = await submit("/sessions/login/phone", { phone });
    if (!r) return;
    if (r.status === "code_sent" && r.flow_id) {
      setFlowId(r.flow_id);
      setStep("code");
    } else {
      setError(r.error ?? "Unknown error");
    }
  }

  async function sendCode() {
    const r = await submit("/sessions/login/code", { flow_id: flowId, code });
    if (!r) return;
    if (r.status === "done") {
      navigate("/sessions");
    } else if (r.status === "need_2fa") {
      setStep("2fa");
    } else {
      setError(r.error ?? "Unknown error");
    }
  }

  async function send2fa() {
    const r = await submit("/sessions/login/2fa", {
      flow_id: flowId,
      password,
    });
    if (!r) return;
    if (r.status === "done") {
      navigate("/sessions");
    } else {
      setError(r.error ?? "Unknown error");
    }
  }

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Login via Phone Number</CardTitle>
        <CardDescription>{STEP_DESCRIPTIONS[step]}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Login failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {step === "phone" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void sendPhone();
            }}
          >
            <Input
              type="text"
              placeholder="+1234567890"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy || !phone}>
              Send code
            </Button>
          </form>
        )}
        {step === "code" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void sendCode();
            }}
          >
            <Input
              type="text"
              placeholder="Code from Telegram"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy || !code}>
              Submit code
            </Button>
          </form>
        )}
        {step === "2fa" && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void send2fa();
            }}
          >
            <Input
              type="password"
              placeholder="2FA password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={busy || !password}>
              Submit password
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
