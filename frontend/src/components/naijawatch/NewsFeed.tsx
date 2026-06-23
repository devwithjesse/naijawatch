import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiFetch, buildQuery, type NewsArticle } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Newspaper, ChevronLeft, ChevronRight, ExternalLink, Loader2 } from "lucide-react";

const PAGE_SIZE = 9;

export function NewsFeed() {
  const [page, setPage] = useState(0);
  const skip = page * PAGE_SIZE;

  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: ["news", skip],
    queryFn: () => apiFetch<NewsArticle[]>(`/api/news/feed${buildQuery({ skip, limit: PAGE_SIZE })}`),
    placeholderData: keepPreviousData,
  });

  const hasNext = (data?.length ?? 0) === PAGE_SIZE;

  return (
    <Card className="border-border bg-card p-0">
      <div className="flex items-center justify-between border-b border-border bg-secondary/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-primary" />
          <h2 className="font-mono-data text-xs font-semibold uppercase tracking-[0.2em]">
            Intelligence Feed
          </h2>
        </div>
        <span className="font-mono-data text-[11px] text-muted-foreground">
          PAGE {page + 1}
        </span>
      </div>

      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : isError ? (
          <div className="py-12 text-center text-sm text-destructive">Failed to load news.</div>
        ) : (data?.length ?? 0) === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">No articles found.</div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data!.map((a) => (
              <a
                key={a.id}
                href={a.url}
                target="_blank"
                rel="noreferrer"
                className="group flex flex-col rounded-lg border border-border bg-background/50 p-3 transition-all hover:border-primary/60 hover:bg-secondary/30"
              >
                <div className="flex items-center justify-between font-mono-data text-[10px] uppercase tracking-wider text-muted-foreground">
                  <span>Source #{a.source_id}</span>
                  <span>{formatDate(a.published_at ?? a.created_at)}</span>
                </div>
                <h3 className="mt-2 line-clamp-3 text-sm font-semibold text-foreground group-hover:text-primary">
                  {a.title}
                </h3>
                {a.body && (
                  <p className="mt-2 line-clamp-3 text-xs text-muted-foreground">{a.body}</p>
                )}
                <div className="mt-3 flex items-center gap-1 text-[11px] text-primary opacity-0 transition-opacity group-hover:opacity-100">
                  Read source <ExternalLink className="h-3 w-3" />
                </div>
              </a>
            ))}
          </div>
        )}

        <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0 || isFetching}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            <ChevronLeft className="h-4 w-4" /> Prev
          </Button>
          <span className="font-mono-data text-[11px] text-muted-foreground">
            {isFetching ? "Loading…" : `${data?.length ?? 0} items`}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasNext || isFetching}
            onClick={() => setPage((p) => p + 1)}
          >
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch { return "—"; }
}