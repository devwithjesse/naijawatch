import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { apiFetch, buildQuery, eventTypeColor, type EventTypeStat } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { PieChart as PieIcon, Loader2 } from "lucide-react";
import type { GlobalFilters } from "./types";

interface Props { filters: GlobalFilters }

export function EventTypesPie({ filters }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["event-types", filters.days, filters.state],
    queryFn: () =>
      apiFetch<EventTypeStat[]>(`/api/stats/event-types${buildQuery({ days: filters.days, state: filters.state })}`),
  });

  const items = (data ?? [])
    .map((d) => ({
      name: String(d.name ?? (d as Record<string, unknown>).event_type ?? "Other"),
      value: Number(d.count ?? (d as Record<string, unknown>).value ?? 0),
    }))
    .filter((d) => d.value > 0);

  return (
    <Card className="border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <PieIcon className="h-4 w-4 text-primary" />
        <h2 className="font-mono-data text-xs font-semibold uppercase tracking-[0.2em]">
          Event Breakdown
        </h2>
      </div>

      {isLoading ? (
        <div className="flex h-55 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : isError ? (
        <div className="grid h-55 place-items-center text-sm text-destructive">Failed to load</div>
      ) : items.length === 0 ? (
        <div className="grid h-55 place-items-center text-sm text-muted-foreground">No data</div>
      ) : (
        <>
          <div className="h-50">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={items}
                  innerRadius={48}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="var(--color-card)"
                  strokeWidth={2}
                >
                  {items.map((it) => (
                    <Cell key={it.name} fill={eventTypeColor(it.name)} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "var(--color-card)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                  itemStyle={{ color: "var(--color-foreground)" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5">
            {items.map((it) => (
              <div key={it.name} className="flex items-center gap-2 text-xs">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: eventTypeColor(it.name), boxShadow: `0 0 6px ${eventTypeColor(it.name)}` }}
                />
                <span className="truncate text-muted-foreground">{it.name}</span>
                <span className="ml-auto font-mono-data font-semibold text-foreground">{it.value}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}