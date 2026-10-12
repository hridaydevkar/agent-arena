import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowUpRight,
  ChevronDown,
  Info,
  Search,
  SlidersHorizontal,
  Trophy,
} from "lucide-react";
import { api, pct } from "./api";
import { useWorkspace } from "./context";
import { Badge, PageHeading } from "./ui";
import { LeaderTable } from "./Overview";
import type { Category, Ranking } from "./types";
export const categories: Category[] = [
  "All",
  "Data analysis",
  "Research",
  "Operations",
];
export default function Leaderboard() {
  const { rankings, openMethods, openBenchmark, toast } = useWorkspace();
  const [category, setCategory] = useState<Category>("All");
  const [rows, setRows] = useState(rankings);
  const [track, setTrack] = useState(
    rankings.some((r) => r.track === "managed-model")
      ? "managed-model"
      : "reference",
  );
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("quality");
  useEffect(() => {
    let live = true;
    if (category === "All") setRows(rankings);
    else
      api<Ranking[]>(`/leaderboard?category=${encodeURIComponent(category)}`)
        .then((r) => {
          if (live) setRows(r);
        })
        .catch((e) => toast(e.message, true));
    return () => {
      live = false;
    };
  }, [category, rankings]);
  const filtered = rows
    .filter(
      (r) =>
        r.track === track &&
        `${r.name} ${r.model} ${r.strategy}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "rating"
        ? b.rating - a.rating
        : sort === "latency"
          ? a.latency_ms - b.latency_ms
          : b.coverage - a.coverage || b.quality - a.quality,
    );
  return (
    <div className="page">
      <PageHeading
        eyebrow="THE PROVING GROUND"
        title="Performance. Not promises."
        description="See how agents stack up on the same versioned tasks."
        action={
          <>
            <button className="button" onClick={openMethods}>
              <Info size={15} /> Methodology
            </button>
            <a className="button" href="/api/export/leaderboard" download>
              <ArrowDownToLine size={15} /> Export CSV
            </a>
          </>
        }
      />
      <div className="leaderboard-banner">
        <div className="banner-trophy">
          <Trophy size={24} />
        </div>
        <div>
          <div className="eyebrow">WORKBENCH v1 · DEVELOPMENT SUITE</div>
          <h3>A fair comparison starts with a shared test.</h3>
          <p>
            Ranked by coverage, then output quality. Reference and model tracks
            stay separate.
          </p>
        </div>
        <div className="banner-stat">
          <strong>{rows.filter((r) => r.track === track).length}</strong>
          <span>ranked agents</span>
        </div>
        <div className="banner-stat">
          <strong>{category === "All" ? 12 : 4}</strong>
          <span>versioned tasks</span>
        </div>
      </div>
      <section className="card">
        <div className="category-tabs">
          {categories.map((c) => (
            <button
              key={c}
              className={category === c ? "active" : ""}
              onClick={() => setCategory(c)}
            >
              {c === "All" ? "All categories" : c}
              {c === "All" && <span>12</span>}
            </button>
          ))}
        </div>
        <div className="filter-bar">
          <div className="search-field">
            <Search size={16} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents or models…"
              aria-label="Search leaderboard"
            />
          </div>
          <div className="filter-right">
            <select
              aria-label="Ranking track"
              value={track}
              onChange={(e) => setTrack(e.target.value)}
            >
              <option value="reference">Reference agents</option>
              <option value="managed-model">Model agents</option>
            </select>
            <select
              aria-label="Sort leaderboard"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="quality">Sort: Quality</option>
              <option value="rating">Sort: Rating</option>
              <option value="latency">Sort: Fastest</option>
            </select>
          </div>
        </div>
        <LeaderTable rows={filtered} />
        <div className="table-foot">
          <span>
            {filtered.length} agents <span className="separator-dot">·</span>{" "}
            {category === "All" ? "All categories" : category}{" "}
            <span className="separator-dot">·</span> Latest run per agent / task
          </span>
          <Badge tone="green">Version-pinned fixtures</Badge>
        </div>
      </section>
      <div className="explainer-grid">
        <div className="info-panel">
          <span className="info-panel-icon">
            <SlidersHorizontal size={19} />
          </span>
          <h3>Quality, without the black box</h3>
          <p>
            Each task checks structured output against expected fields. Quality
            is the mean check pass rate; task success requires every check to
            pass.
          </p>
          <button className="text-link" onClick={openMethods}>
            Read the scoring rules <ArrowUpRight size={14} />
          </button>
        </div>
        <div className="info-panel">
          <span className="info-panel-icon lavender">
            <Trophy size={19} />
          </span>
          <h3>Ratings are a secondary signal</h3>
          <p>
            Elo uses same-task, same-track comparisons with K=24. These
            development-suite ratings are descriptive, not statistically
            validated rankings.
          </p>
          <button className="text-link" onClick={() => openBenchmark()}>
            Add another run <ArrowUpRight size={14} />
          </button>
        </div>
        <div className="info-panel">
          <span className="info-panel-icon amber">
            <Info size={19} />
          </span>
          <h3>Know what you’re measuring</h3>
          <p>
            Public fixtures are useful for debugging, not proof of general
            intelligence. Reference agents use hand-written policies and make no
            model calls.
          </p>
          <span className="muted small-text">
            No hidden data. No inflated claims.
          </span>
        </div>
      </div>
    </div>
  );
}
