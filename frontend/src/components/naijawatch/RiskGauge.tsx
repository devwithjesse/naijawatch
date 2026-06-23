import { useQuery } from "@tanstack/react-query";
import { apiFetch, type NationalRisk } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus, ShieldAlert, Loader2 } from "lucide-react";

export function RiskGauge() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["national-risk"],
    queryFn: () => apiFetch<NationalRisk>("/api/stats/national-risk"),
  });

  const score = pickNumber(data, ["score", "risk_score", "national_risk"]) ?? 0;
  const safety = pickNumber(data, ["safety_index", "safety"]) ?? Math.max(0, 100 - score);
  const trend = (data?.trend as string | undefined) ?? "stable";
  const label = (data?.label as string | undefined) ?? scoreLabel(score);

  const colorVar =
    score >= 75 ? "var(--color-destructive)" :
    score >= 50 ? "var(--color-accent)" : "var(--color-primary)";
  const glowClass =
    score >= 75 ? "text-glow-red" :
    score >= 50 ? "text-glow-amber" : "text-glow-cyan";

  const pct = Math.min(100, Math.max(0, score));
  const radius = 70;
  const circumference = Math.PI * radius;
  const dash = (pct / 100) * circumference;

  return (
    <Card className="border-border bg-card p-4">
      <div className="mb-2 flex items-center gap-2">
        <ShieldAlert className="h-4 w-4 text-primary" />
        <h2 className="font-mono-data text-xs font-semibold uppercase tracking-[0.2em]">
          National Risk Score
        </h2>
      </div>

      {isLoading ? (
        <div className="flex h-[200px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : isError ? (
        <div className="grid h-[200px] place-items-center text-sm text-destructive">
          Failed to load
        </div>
      ) : (
        <div className="flex flex-col items-center pt-2">
          <div className="relative">
            <svg width="180" height="110" viewBox="0 0 180 110">
              <path
                d={`M 20 100 A ${radius} ${radius} 0 0 1 160 100`}
                fill="none"
                stroke="var(--color-secondary)"
                strokeWidth="14"
                strokeLinecap="round"
              />
              <path
                d={`M 20 100 A ${radius} ${radius} 0 0 1 160 100`}
                fill="none"
                stroke={colorVar}
                strokeWidth="14"
                strokeLinecap="round"
                strokeDasharray={`${dash} ${circumference}`}
                style={{ filter: `drop-shadow(0 0 8px ${colorVar})` }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
              <div className={`font-mono-data text-4xl font-bold ${glowClass}`} style={{ color: colorVar }}>
                {Math.round(score)}
              </div>
              <div className="font-mono-data text-[10px] uppercase tracking-widest text-muted-foreground">
                / 100
              </div>
            </div>
          </div>

          <div
            className="mt-2 inline-flex items-center gap-2 rounded-full border px-3 py-1"
            style={{
              borderColor: `color-mix(in oklab, ${colorVar} 50%, transparent)`,
              background: `color-mix(in oklab, ${colorVar} 12%, transparent)`,
            }}
          >
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: colorVar }}>
              {label}
            </span>
            <TrendIcon trend={trend} />
          </div>

          <div className="mt-4 grid w-full grid-cols-2 gap-2 border-t border-border pt-3 text-center">
            <div>
              <div className="font-mono-data text-[10px] uppercase tracking-wider text-muted-foreground">Safety</div>
              <div className="font-mono-data text-lg font-semibold text-foreground">{Math.round(safety)}</div>
            </div>
            <div>
              <div className="font-mono-data text-[10px] uppercase tracking-wider text-muted-foreground">Trend</div>
              <div className="font-mono-data text-lg font-semibold capitalize text-foreground">{trend}</div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "up") return <TrendingUp className="h-4 w-4 text-destructive" />;
  if (trend === "down") return <TrendingDown className="h-4 w-4 text-primary" />;
  return <Minus className="h-4 w-4 text-muted-foreground" />;
}

function pickNumber(obj: Record<string, unknown> | undefined, keys: string[]) {
  if (!obj) return undefined;
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "number") return v;
  }
  return undefined;
}

function scoreLabel(score: number) {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 40) return "Elevated";
  if (score >= 20) return "Moderate";
  return "Low";
}