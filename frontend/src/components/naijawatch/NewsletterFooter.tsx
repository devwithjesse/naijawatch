import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Mail, Loader2 } from "lucide-react";
import { toast } from "sonner";

export function NewsletterFooter() {
  const [email, setEmail] = useState("");
  const { mutate, isPending } = useMutation({
    mutationFn: (vars: { email: string }) =>
      apiFetch<unknown>("/api/digest/subscribe", {
        method: "POST",
        body: JSON.stringify(vars),
      }),
    onSuccess: () => {
      toast.success("Confirmation email sent. Check your inbox.");
      setEmail("");
    },
    onError: (e: Error) => toast.error(e.message ?? "Subscription failed"),
  });

  return (
    <footer className="border-t border-border bg-card/60 backdrop-blur-xl">
      <div className="mx-auto flex max-w-400 flex-col gap-6 px-4 py-8 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-primary/40 bg-primary/10">
            <Mail className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Daily Intelligence Digest</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Get a curated brief of Nigerian security events, risk shifts, and travel advisories —
              every morning.
            </p>
          </div>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!email.trim()) return toast.error("Enter your email");
            mutate({ email: email.trim() });
          }}
          className="flex w-full max-w-md items-center gap-2"
        >
          <Input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="font-mono-data text-sm"
          />
          <Button
            type="submit"
            disabled={isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Subscribe"}
          </Button>
        </form>
      </div>
      <div className="border-t border-border px-4 py-3 text-center font-mono-data text-[10px] uppercase tracking-[0.25em] text-muted-foreground sm:px-6">
        NaijaWatch · Command Console v1.0
      </div>

      <div className="px-4 py-3 text-center text-xs text-muted-foreground sm:px-6">
        <p>
          Disclaimer: All data displayed in this application is derived from public news sources
          across Nigeria and is provided for situational awareness only. While we aggregate and
          process information to the best of our ability, we do not guarantee accuracy or
          completeness. Use the information responsibly.
        </p>
      </div>
    </footer>
  );
}
