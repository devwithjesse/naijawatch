import { useQuery } from "@tanstack/react-query";
import { apiFetch, type StateRanking } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ListOrdered, TrendingUp, TrendingDown, Minus, Loader2 } from "lucide-react";

export function StateRankings() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["state-rankings"],
    queryFn: () => apiFetch<StateRanking[]>("/api/stats/states"),
  });

  const items = (data ?? [])
    .map((s) => {
      const score = Number(s.risk_score ?? (s as Record<string, unknown>).score ?? 0);
      return {
        state: String(s.state ?? s.name ?? "—"),
        score,
        label: String(s.risk_label ?? (s as Record<string, unknown>).label ?? riskLabel(score)),
        trend: (s.trend as string) ?? "stable",
      };
    })
    .sort((a, b) => b.score - a.score);

  return (
    <Card className="border-border bg-card p-0">
      <div className="flex items-center justify-between border-b border-border bg-secondary/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <ListOrdered className="h-4 w-4 text-primary" />
          <div>
            <h2 className="font-mono-data text-xs font-semibold uppercase tracking-[0.2em]">
              State Risk Rankings
            </h2>
            <div className="text-[11px] text-muted-foreground">Updated weekly</div>
          </div>
        </div>
        <span className="font-mono-data text-[11px] text-muted-foreground">{items.length}</span>
      </div>
      {isLoading ? (
        <div className="flex h-75 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : isError ? (
        <div className="grid h-75 place-items-center text-sm text-destructive">
          Failed to load
        </div>
      ) : (
        <ScrollArea className="h-75">
          <ul className="divide-y divide-border">
            {items.map((it, idx) => {
              const color = riskColor(it.score);
              return (
                <li
                  key={it.state}
                  className="flex items-center gap-3 px-4 py-2.5 transition hover:bg-secondary/40"
                >
                  <span className="w-6 font-mono-data text-[11px] text-muted-foreground">
                    #{idx + 1}
                  </span>
                  <span className="flex-1 truncate text-sm font-medium text-foreground">
                    {it.state}
                  </span>
                  <span
                    className="rounded-full px-2 py-0.5 font-mono-data text-[10px] uppercase tracking-wider"
                    style={{
                      color,
                      background: `color-mix(in oklab, ${color} 14%, transparent)`,
                      border: `1px solid color-mix(in oklab, ${color} 40%, transparent)`,
                    }}
                  >
                    {it.label}
                  </span>
                  <span
                    className="w-10 text-right font-mono-data text-sm font-semibold"
                    style={{ color }}
                  >
                    {Math.round(it.score)}
                  </span>
                  <TrendIcon trend={it.trend} />
                </li>
              );
            })}
          </ul>
        </ScrollArea>
      )}
    </Card>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "up") return <TrendingUp className="h-3.5 w-3.5 text-destructive" />;
  if (trend === "down") return <TrendingDown className="h-3.5 w-3.5 text-primary" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
}

function riskColor(score: number) {
  if (score >= 75) return "var(--color-destructive)";
  if (score >= 50) return "var(--color-accent)";
  if (score >= 25) return "oklch(0.78 0.16 200)";
  return "oklch(0.72 0.18 145)";
}
function riskLabel(score: number) {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 40) return "Elevated";
  if (score >= 20) return "Moderate";
  return "Low";
}
