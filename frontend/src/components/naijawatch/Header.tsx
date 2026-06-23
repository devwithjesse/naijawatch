// Logo image is served from /logo.png in public/
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { NIGERIAN_STATES, EVENT_TYPES } from "@/lib/api";
import type { GlobalFilters } from "./types";

interface Props {
  filters: GlobalFilters;
  onChange: (f: GlobalFilters) => void;
}

export function Header({ filters, onChange }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-400 flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:py-3">
        <div className="flex items-center gap-3">
          <div className="relative grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-primary/40 bg-primary/10 glow-cyan overflow-hidden">
            <img src="/logo.png" alt="NaijaWatch logo" className="h-7 w-7 object-contain" />
            <span
              className="absolute inset-0 rounded-lg border border-primary/30 animate-radar"
              style={{ borderTopColor: "transparent", borderLeftColor: "transparent" }}
            />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-base font-bold tracking-wide text-foreground sm:text-lg">
              NAIJAWATCH<span className="text-primary text-glow-cyan"> INTELLIGENCE</span>
            </h1>
            <p className="font-mono-data text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              Nigerian Security Operations Console
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <Select
            value={filters.days === 0 ? "__all" : String(filters.days)}
            onValueChange={(v) => onChange({ ...filters, days: v === "__all" ? 0 : Number(v) })}
          >
            <SelectTrigger className="h-9 w-35 font-mono-data text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all">All events</SelectItem>
              {[30, 20, 10, 7, 3, 1].map((d) => (
                <SelectItem key={d} value={String(d)}>
                  Last {d} day{d > 1 ? "s" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={filters.state ?? "__all"}
            onValueChange={(v) => onChange({ ...filters, state: v === "__all" ? null : v })}
          >
            <SelectTrigger className="h-9 w-40 font-mono-data text-xs">
              <SelectValue placeholder="All States" />
            </SelectTrigger>
            <SelectContent className="max-h-75">
              <SelectItem value="__all">All States</SelectItem>
              {NIGERIAN_STATES.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={filters.eventType ?? "__all"}
            onValueChange={(v) => onChange({ ...filters, eventType: v === "__all" ? null : v })}
          >
            <SelectTrigger className="h-9 w-42.5 font-mono-data text-xs">
              <SelectValue placeholder="All Event Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all">All Event Types</SelectItem>
              {EVENT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </header>
  );
}
