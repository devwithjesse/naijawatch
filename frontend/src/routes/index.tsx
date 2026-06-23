import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/naijawatch/Header";
import { NigeriaMap } from "@/components/naijawatch/NigeriaMap";
import { NewsFeed } from "@/components/naijawatch/NewsFeed";
import { RiskGauge } from "@/components/naijawatch/RiskGauge";
import { EventTypesPie } from "@/components/naijawatch/EventTypesPie";
import { StateRankings } from "@/components/naijawatch/StateRankings";
import { TravelRisk } from "@/components/naijawatch/TravelRisk";
import { NewsletterFooter } from "@/components/naijawatch/NewsletterFooter";
import type { GlobalFilters } from "@/components/naijawatch/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "NaijaWatch Intelligence — Live Security Console" },
      {
        name: "description",
        content: "Real-time Nigerian security intelligence: events map, national risk score, travel advisories, and analytics.",
      },
      { property: "og:title", content: "NaijaWatch Intelligence" },
      { property: "og:description", content: "Real-time Nigerian security intelligence command center." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const [filters, setFilters] = useState<GlobalFilters>({
    days: 30,
    state: null,
    eventType: null,
  });

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header filters={filters} onChange={setFilters} />

      <main className="mx-auto w-full max-w-400 flex-1 px-4 py-5 sm:px-6">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.85fr_1fr]">
          <div className="flex min-w-0 flex-col gap-5">
            <NigeriaMap filters={filters} />
            <NewsFeed />
          </div>
          <aside className="flex min-w-0 flex-col gap-5">
            <RiskGauge />
            <EventTypesPie filters={filters} />
            <StateRankings />
            <TravelRisk />
          </aside>
        </div>
      </main>

      <NewsletterFooter />
    </div>
  );
}
