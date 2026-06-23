import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, buildQuery, eventTypeColor, type MapEvent, type SecurityEvent } from "@/lib/api";
import type { GlobalFilters } from "./types";
import { Card } from "@/components/ui/card";
import { Loader2, MapPin } from "lucide-react";

interface Props { filters: GlobalFilters }

export function NigeriaMap({ filters }: Props) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["map", filters.days, filters.state],
    queryFn: () => apiFetch<MapEvent[]>(`/api/events/map${buildQuery({ days: filters.days, state: filters.state })}`),
  });

  return (
    <Card className="relative overflow-hidden border-border bg-card p-0">
      <div className="flex items-center justify-between border-b border-border bg-secondary/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4 text-primary" />
          <h2 className="font-mono-data text-xs font-semibold uppercase tracking-[0.2em] text-foreground">
            Tactical Map
          </h2>
          <span className="ml-2 inline-flex h-2 w-2 animate-pulse rounded-full bg-primary glow-cyan" />
        </div>
        <span className="font-mono-data text-[11px] text-muted-foreground">
          {data?.length ?? 0} events tracked
        </span>
      </div>
      <div className="relative h-[480px] w-full">
        {isLoading && (
          <div className="absolute inset-0 z-[400] grid place-items-center bg-background/40 backdrop-blur-sm">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}
        {isError && (
          <div className="absolute inset-0 z-[400] grid place-items-center bg-background/60 text-sm text-destructive">
            Failed to load map events
          </div>
        )}
        {mounted && <LeafletMap events={data ?? []} />}
      </div>
    </Card>
  );
}

function LeafletMap({ events }: { events: MapEvent[] }) {
  const [mod, setMod] = useState<null | typeof import("./LeafletInner")>(null);
  useEffect(() => {
    let active = true;
    import("./LeafletInner").then((m) => { if (active) setMod(m); });
    return () => { active = false; };
  }, []);
  if (!mod) return null;
  const { LeafletInner } = mod;
  return <LeafletInner events={events} />;
}

export async function fetchEventDetail(id: number): Promise<SecurityEvent> {
  return apiFetch<SecurityEvent>(`/api/events/${id}`);
}

export { eventTypeColor };