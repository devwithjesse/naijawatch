import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { apiFetch, type TravelRiskResult } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Route as RouteIcon, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export function TravelRisk() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");

  const { mutate, data, isPending, reset } = useMutation({
    mutationFn: (vars: { origin: string; destination: string }) =>
      apiFetch<TravelRiskResult>("/api/travel/risk", {
        method: "POST",
        body: JSON.stringify(vars),
      }),
    onError: (e: Error) => toast.error(e.message ?? "Failed to assess route"),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!origin.trim() || !destination.trim()) {
      toast.error("Enter both origin and destination");
      return;
    }
    mutate({ origin: origin.trim(), destination: destination.trim() });
  };

  const payload = data as TravelRiskResult | undefined;
  const score = payload?.route_summary?.journey_risk_score ?? 0;
  const advisory = payload?.advisory;
  const states = (payload?.state_breakdown ?? []) as Array<{
    name?: string;
    state?: string;
    risk_score?: number;
    risk_label?: string;
  }>;
  const statesPassed = payload?.route_summary?.states_passed ?? ([] as string[]);
  const scoreColor =
    score >= 75
      ? "var(--color-destructive)"
      : score >= 50
        ? "var(--color-accent)"
        : "var(--color-primary)";

  return (
    <Card className="border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <RouteIcon className="h-4 w-4 text-primary" />
        <h2 className="font-mono-data text-xs font-semibold uppercase tracking-[0.2em]">
          Travel Risk Assessment
        </h2>
      </div>

      <form onSubmit={onSubmit} className="space-y-2">
        <Input
          placeholder="Origin (e.g. Lagos)"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          className="font-mono-data text-sm"
        />
        <div className="flex justify-center text-muted-foreground">
          <ArrowRight className="h-4 w-4 rotate-90" />
        </div>
        <Input
          placeholder="Destination (e.g. Maiduguri)"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          className="font-mono-data text-sm"
        />
        <Button
          type="submit"
          disabled={isPending}
          className="mt-2 w-full bg-primary text-primary-foreground hover:bg-primary/90 glow-cyan"
        >
          {isPending ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Scanning route…
            </span>
          ) : (
            "Assess Route"
          )}
        </Button>
      </form>

      {isPending && (
        <div className="mt-4 overflow-hidden rounded-md border border-border bg-secondary/30">
          <div className="h-1 w-1/2 animate-pulse bg-primary glow-cyan" />
          <div className="p-3 font-mono-data text-[11px] uppercase tracking-wider text-muted-foreground">
            Cross-referencing intelligence layers…
          </div>
        </div>
      )}

      {data && !isPending && (
        <div className="mt-4 space-y-3 border-t border-border pt-3">
          <div className="flex items-center justify-between">
            <span className="font-mono-data text-[11px] uppercase tracking-wider text-muted-foreground">
              Journey Risk
            </span>
            <span
              className="font-mono-data text-2xl font-bold"
              style={{ color: scoreColor, textShadow: `0 0 12px ${scoreColor}` }}
            >
              {Math.round(score)}
            </span>
          </div>
          {advisory && (
            <div className="prose prose-sm prose-invert max-w-none rounded-md border border-border bg-background/50 p-3 text-xs leading-relaxed text-foreground">
              <ReactMarkdown>{advisory}</ReactMarkdown>
            </div>
          )}

          {/* Trip details (distance and duration) */}
          {data?.trip_details && (
            <div className="text-xs text-muted-foreground">
              <div className="font-mono-data text-[11px] uppercase tracking-wider">
                Trip details
              </div>
              <div className="mt-1">
                Distance:{" "}
                <span className="font-semibold text-foreground">
                  {data.trip_details.distance_km} km
                </span>
                {typeof data.trip_details.hours === "number" &&
                  typeof data.trip_details.minutes === "number" && (
                    <span className="ml-2">
                      • Estimated:{" "}
                      <span className="font-semibold text-foreground">
                        {data.trip_details.hours}h {data.trip_details.minutes}m
                      </span>
                    </span>
                  )}
              </div>
            </div>
          )}

          {statesPassed && statesPassed.length > 0 && (
            <div className="text-xs text-muted-foreground">
              <div className="font-mono-data text-[11px] uppercase tracking-wider">
                States along route
              </div>
              <div className="mt-1">{statesPassed.join(" → ")}</div>
            </div>
          )}

          {states.length > 0 && (
            <ul className="space-y-1.5">
              {states.map((s, i) => (
                <li
                  key={`${s.name ?? s.state}-${i}`}
                  className="flex items-center justify-between rounded border border-border bg-background/40 px-2 py-1.5 text-xs"
                >
                  <span className="text-foreground">{s.name ?? s.state}</span>
                  <span
                    className="font-mono-data font-semibold"
                    style={{
                      color:
                        (s.risk_score ?? 0) >= 75
                          ? "var(--color-destructive)"
                          : (s.risk_score ?? 0) >= 50
                            ? "var(--color-accent)"
                            : "var(--color-primary)",
                    }}
                  >
                    {Math.round(s.risk_score ?? 0)} {s.risk_label ? `· ${s.risk_label}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <button
            onClick={() => reset()}
            className="font-mono-data text-[11px] uppercase tracking-wider text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
          >
            Run new assessment
          </button>
        </div>
      )}
    </Card>
  );
}
