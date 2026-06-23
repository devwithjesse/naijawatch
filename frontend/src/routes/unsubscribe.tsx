import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { apiFetch, buildQuery } from "@/lib/api";
import { MailX } from "lucide-react";
import { ResultShell } from "./confirm";

export const Route = createFileRoute("/unsubscribe")({
  head: () => ({ meta: [{ title: "Unsubscribe · NaijaWatch" }] }),
  component: UnsubscribePage,
});

function UnsubscribePage() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setMessage("Missing unsubscribe token.");
      return;
    }
    apiFetch<{ message?: string }>(`/api/digest/unsubscribe${buildQuery({ token })}`)
      .then((r) => { setStatus("ok"); setMessage(r?.message ?? "You have been unsubscribed."); })
      .catch((e: Error) => { setStatus("error"); setMessage(e.message); });
  }, []);

  return (
    <ResultShell
      icon={<MailX className="h-6 w-6 text-primary" />}
      title="Unsubscribe"
      status={status}
      message={message}
    />
  );
}