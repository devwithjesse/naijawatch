import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { apiFetch, buildQuery } from "@/lib/api";
import { CheckCircle2, XCircle, Loader2, Mail } from "lucide-react";

export const Route = createFileRoute("/confirm")({
  head: () => ({ meta: [{ title: "Confirm Subscription · NaijaWatch" }] }),
  component: ConfirmPage,
});

function ConfirmPage() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setMessage("Missing confirmation token.");
      return;
    }
    apiFetch<{ message?: string }>(`/api/digest/confirm${buildQuery({ token })}`)
      .then((r) => { setStatus("ok"); setMessage(r?.message ?? "Your subscription is confirmed."); })
      .catch((e: Error) => { setStatus("error"); setMessage(e.message); });
  }, []);

  return (
    <ResultShell
      icon={<Mail className="h-6 w-6 text-primary" />}
      title="Subscription Confirmation"
      status={status}
      message={message}
    />
  );
}

export function ResultShell({
  icon, title, status, message,
}: {
  icon: React.ReactNode;
  title: string;
  status: "loading" | "ok" | "error";
  message: string;
}) {
  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-2xl">
        <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full border border-primary/40 bg-primary/10 glow-cyan">
          {icon}
        </div>
        <h1 className="font-mono-data text-xs uppercase tracking-[0.3em] text-muted-foreground">{title}</h1>
        <div className="mt-6 flex flex-col items-center gap-3">
          {status === "loading" && <Loader2 className="h-8 w-8 animate-spin text-primary" />}
          {status === "ok" && <CheckCircle2 className="h-10 w-10 text-primary text-glow-cyan" />}
          {status === "error" && <XCircle className="h-10 w-10 text-destructive text-glow-red" />}
          <p className={`text-sm ${status === "error" ? "text-destructive" : "text-foreground"}`}>
            {status === "loading" ? "Processing your request…" : message}
          </p>
        </div>
        <Link
          to="/"
          className="mt-6 inline-block font-mono-data text-xs uppercase tracking-[0.2em] text-primary hover:underline"
        >
          ← Back to Console
        </Link>
      </div>
    </div>
  );
}