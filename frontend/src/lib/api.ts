const BASE_URL = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const NIGERIAN_STATES = [
  "Abia",
  "Adamawa",
  "Akwa Ibom",
  "Anambra",
  "Bauchi",
  "Bayelsa",
  "Benue",
  "Borno",
  "Cross River",
  "Delta",
  "Ebonyi",
  "Edo",
  "Ekiti",
  "Enugu",
  "FCT",
  "Gombe",
  "Imo",
  "Jigawa",
  "Kaduna",
  "Kano",
  "Katsina",
  "Kebbi",
  "Kogi",
  "Kwara",
  "Lagos",
  "Nasarawa",
  "Niger",
  "Ogun",
  "Ondo",
  "Osun",
  "Oyo",
  "Plateau",
  "Rivers",
  "Sokoto",
  "Taraba",
  "Yobe",
  "Zamfara",
] as const;

export const EVENT_TYPES = [
  "Kidnapping",
  "Banditry",
  "Terrorism",
  "Armed Robbery",
  "Communal Clash",
  "Cult Violence",
  "Protest",
  "Assassination",
  "Other",
] as const;

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
      else if (body?.message) detail = body.message;
      else if (typeof body === "string") detail = body;
      else if (typeof body === "object") {
        const vals = Object.values(body)
          .slice(0, 3)
          .map((v) => (typeof v === "string" ? v : JSON.stringify(v)));
        detail = vals.join(" — ").slice(0, 240);
      }
    } catch (e) {
      console.warn("apiFetch: failed to parse error body", e);
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

/* ---------- Types ---------- */
export interface State {
  id: number;
  name: string;
}
export interface Location {
  id: number;
  state_id: number;
  name: string;
  latitude: number | null;
  longitude: number | null;
  state: State;
}
export interface EventType {
  id: number;
  name: string;
}
export interface EventStatistics {
  id: number;
  event_id: number;
  killed: number;
  injured: number;
  abducted: number;
}
export interface SecurityEvent {
  id: number;
  event_type_id: number;
  location_id: number;
  event_date: string | null;
  confidence: number;
  summary: string | null;
  created_at: string;
  event_type: EventType;
  location: Location;
  statistics: EventStatistics | null;
}
export interface MapEvent {
  id: number;
  lat: number;
  lng: number;
  type: string;
  summary: string;
}
export interface NewsArticle {
  id: number;
  title: string;
  url: string;
  content_hash: string;
  source_id: number;
  body: string | null;
  published_at: string | null;
  processed: boolean;
  extraction_status: string;
  created_at: string;
}
export interface NationalRisk {
  score?: number;
  risk_score?: number;
  safety_index?: number;
  trend?: "up" | "down" | "stable";
  label?: string;
  [k: string]: unknown;
}
export interface EventTypeStat {
  name: string;
  count: number;
  [k: string]: unknown;
}
export interface StateRanking {
  state: string;
  risk_score: number;
  risk_label?: string;
  trend?: "up" | "down" | "stable";
  events?: number;
  [k: string]: unknown;
}
export interface TravelRiskResult {
  advisory?: string;
  route_summary?: {
    journey_risk_score?: number;
    states_passed?: string[];
    distance_km?: number;
    estimated_duration_mins?: number;
  };
  trip_details?: {
    distance_km: number;
    estimated_duration_mins?: number;
    hours?: number;
    minutes?: number;
  };
  state_breakdown?: Array<{
    name?: string;
    state?: string;
    risk_score?: number;
    risk_label?: string;
  }>;
  [k: string]: unknown;
}

/* ---------- Color mapping for event types ---------- */
export function eventTypeColor(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("kidnap")) return "oklch(0.78 0.18 75)"; // amber
  if (n.includes("bandit")) return "oklch(0.7 0.2 30)"; // orange
  if (n.includes("terror") || n.includes("bomb")) return "oklch(0.65 0.24 25)"; // red
  if (n.includes("robbery")) return "oklch(0.7 0.18 50)";
  if (n.includes("clash") || n.includes("communal")) return "oklch(0.65 0.2 300)"; // purple
  if (n.includes("cult")) return "oklch(0.6 0.22 340)";
  if (n.includes("protest")) return "oklch(0.78 0.16 200)"; // cyan
  if (n.includes("assassin")) return "oklch(0.55 0.24 15)";
  return "oklch(0.72 0.18 145)"; // green default
}
