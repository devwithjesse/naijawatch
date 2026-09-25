import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { useQuery } from "@tanstack/react-query";
import { fetchEventDetail, eventTypeColor } from "./NigeriaMap";
import type { MapEvent } from "@/lib/api";

const NIGERIA_CENTER: [number, number] = [9.082, 8.6753];

function makeIcon(color: string) {
  return L.divIcon({
    className: "naija-marker",
    html: `<span style="display:block;width:18px;height:18px;border-radius:9999px;background:${color};box-shadow:0 0 0 3px ${color}33, 0 0 14px ${color};border:2px solid rgba(255,255,255,0.85);"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

export function LeafletInner({ events }: { events: MapEvent[] }) {
  return (
    <MapContainer
      center={NIGERIA_CENTER}
      zoom={6}
      minZoom={5}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap &copy; CARTO"
        url={`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${import.meta.env.VITE_CARTO_API_KEY}`}
      />
      {events
        .filter((e) => typeof e.lat === "number" && typeof e.lng === "number")
        .map((e) => (
          <EventMarker key={e.id} event={e} />
        ))}
    </MapContainer>
  );
}

function EventMarker({ event }: { event: MapEvent }) {
  const color = eventTypeColor(event.type ?? "");
  const icon = makeIcon(color);
  const map = useMap();

  return (
    <Marker
      position={[event.lat, event.lng]}
      icon={icon}
      eventHandlers={{
        click: () => map.flyTo([event.lat, event.lng], 10, { duration: 1.2 }),
      }}
    >
      <Popup>
        <PopupContent id={event.id} fallback={event} />
      </Popup>
    </Marker>
  );
}

function PopupContent({ id, fallback }: { id: number; fallback: MapEvent }) {
  const { data, isLoading } = useQuery({
    queryKey: ["event", id],
    queryFn: () => fetchEventDetail(id),
    staleTime: 60_000,
  });

  const color = eventTypeColor(data?.event_type?.name ?? fallback.type ?? "");

  return (
    <div style={{ minWidth: 220, maxWidth: 280 }}>
      <div
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          background: `${color}22`,
          color,
          border: `1px solid ${color}55`,
          marginBottom: 6,
        }}
      >
        {data?.event_type?.name ?? fallback.type}
      </div>
      {isLoading ? (
        <div style={{ fontSize: 12, opacity: 0.7 }}>Loading details…</div>
      ) : data ? (
        <>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
            {data.location?.name}, {data.location?.state?.name}
          </div>
          <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 6 }}>
            {data.event_date ?? new Date(data.created_at).toLocaleDateString()}
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.4 }}>
            {data.summary ?? fallback.summary ?? "No summary available."}
          </div>
          {data.statistics && (
            <div style={{ display: "flex", gap: 8, marginTop: 8, fontSize: 11 }}>
              <span>Killed: {data.statistics.killed}</span>
              <span>Injured: {data.statistics.injured}</span>
              <span>Abducted: {data.statistics.abducted}</span>
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 12 }}>{fallback.summary}</div>
      )}
    </div>
  );
}
