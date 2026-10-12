import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleDot,
  Clock3,
  Code2,
  FlaskConical,
  Layers3,
  Play,
  ShieldCheck,
  Sparkles,
  Trophy,
  Users2,
} from "lucide-react";
import { useWorkspace } from "./context";
import { AgentAvatar, Badge, CategoryIcon, Empty, PageHeading } from "./ui";
import { ago, duration, money, pct } from "./api";
import type { Ranking } from "./types";

export function LeaderTable({
  rows,
  compact = false,
}: {
  rows: Ranking[];
  compact?: boolean;
}) {
  const navigate = useNavigate();
  return !rows.length ? (
    <Empty
      title="The field is open"
      description="Run a benchmark in this category to see an agent here."
    />
  ) : (
    <div className="table-scroll">
      <table className={`ranking-table ${compact ? "compact" : ""}`}>
        <thead>
          <tr>
            <th className="rank-col">#</th>
            <th className="agent-col">Agent</th>
            <th>
              Quality <ArrowDown size={11} />
            </th>
            <th>Task success</th>
            {!compact && (
              <th>
                Rating{" "}
                <span title="Descriptive Elo, K=24. See methodology.">ⓘ</span>
              </th>
            )}
            <th>Median time</th>
            <th>Avg. cost</th>
            <th>Coverage</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id}>
              <td className="rank-col">
                <span className={`rank ${i === 0 ? "first" : ""}`}>
                  {i === 0 ? (
                    <Trophy size={14} />
                  ) : (
                    String(i + 1).padStart(2, "0")
                  )}
                </span>
              </td>
              <td>
                <button
                  className="agent-cell"
                  onClick={() => navigate(`/agents/${row.id}`)}
                >
                  <AgentAvatar agent={row} />
                  <span>
                    <strong>
                      {row.name}
                      {i === 0 && <span className="best-label">TOP</span>}
                    </strong>
                    <small>
                      {row.model === "Deterministic"
                        ? `${row.strategy} · reference`
                        : `${row.architecture || "tools"} · ${row.model}`}
                    </small>
                  </span>
                </button>
              </td>
              <td>
                <span className="quality-value">{pct(row.quality)}</span>
                <div className="mini-bar">
                  <i style={{ width: pct(row.quality) }} />
                </div>
              </td>
              <td className="numeric">{pct(row.success_rate)}</td>
              {!compact && (
                <td className="numeric rating-cell">
                  {row.matches ? row.rating.toLocaleString() : "Unrated"}
                  <small>{row.matches} pairs</small>
                </td>
              )}
              <td className="numeric muted">{duration(row.latency_ms)}</td>
              <td className="numeric">{money(row.cost_usd)}</td>
              <td>
                <span className="coverage-number">
                  {row.task_count}
                  <span> / {row.total_tasks}</span>
                </span>
              </td>
              <td>
                <button
                  className="row-arrow"
                  title={`Replay ${row.name}'s latest run`}
                  aria-label={`Replay ${row.name}'s latest run`}
                  onClick={() => navigate(`/runs/${row.latest_run_id}`)}
                >
                  <ArrowUpRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ArenaGraphic() {
  return (
    <svg
      className="arena-graphic"
      viewBox="0 0 330 270"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id="platform"
          x1="60"
          y1="90"
          x2="240"
          y2="200"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#f5f9eb" />
          <stop offset="1" stopColor="#c8d3b4" />
        </linearGradient>
        <linearGradient
          id="prism"
          x1="140"
          y1="80"
          x2="180"
          y2="165"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#728953" />
          <stop offset="1" stopColor="#293e2a" />
        </linearGradient>
      </defs>
      <path
        d="m165 24 127 73v73l-127 74L38 171V98L165 24Z"
        stroke="#92a577"
        strokeOpacity=".2"
        strokeDasharray="4 5"
      />
      <path
        d="m165 52 109 62-109 64L56 115l109-63Z"
        stroke="#a5b490"
        strokeWidth=".7"
      />
      <path
        d="m165 91 108 62-108 63-109-63 109-62Z"
        fill="#a7b991"
        fillOpacity=".17"
      />
      <path d="m62 125 103 60 104-60v19l-104 61-103-60v-20Z" fill="#b6c5a2" />
      <path
        d="m165 65 104 60-104 60-103-60 103-60Z"
        fill="url(#platform)"
        stroke="#c1cdae"
      />
      <path
        d="m79 125 86-50 87 50-87 50-86-50Z"
        stroke="#a2b68b"
        strokeWidth=".8"
      />
      <path
        d="m101 125 64-37 65 37-65 37-64-37Z"
        stroke="#afbc98"
        strokeWidth=".8"
      />
      <path d="m165 46-39 82 39 23 39-23-39-82Z" fill="url(#prism)" />
      <path d="m165 46 39 82-39 23V46Z" fill="#425939" />
      <path d="m165 75-19 47 19 11 20-11-20-47Z" fill="#cce3a7" />
      <path d="m165 75 20 47-20 11V75Z" fill="#a4c475" />
      <circle cx="62" cy="125" r="4" fill="#f4f7ec" stroke="#81966b" />
      <circle cx="268" cy="125" r="4" fill="#f4f7ec" stroke="#81966b" />
      <circle cx="165" cy="185" r="4" fill="#f4f7ec" stroke="#81966b" />
      <path
        d="M62 125 24 147v44m244-66 37 23v-67m-140 104v51"
        stroke="#94a87d"
        strokeDasharray="3 4"
      />
      <rect
        x="9"
        y="188"
        width="31"
        height="24"
        rx="6"
        fill="#edf3e2"
        stroke="#c8d6b9"
      />
      <path d="m19 200 4 4 7-8" stroke="#647e4a" strokeWidth="1.5" />
      <rect
        x="288"
        y="59"
        width="31"
        height="24"
        rx="6"
        fill="#edf3e2"
        stroke="#c8d6b9"
      />
      <path
        d="m297 67-4 4 4 4m11-8 4 4-4 4m-7-10-2 12"
        stroke="#647e4a"
        strokeWidth="1.3"
      />
      <text x="172" y="236" fill="#81966b" fontSize="8" fontFamily="monospace">
        VERIFIABLE BY DESIGN
      </text>
    </svg>
  );
}

export default function OverviewPage() {
  const { overview, rankings, openBenchmark, openMethods, health } =
    useWorkspace();
  const [track, setTrack] = useState(
    rankings.some((r) => r.track === "managed-model")
      ? "managed-model"
      : "reference",
  );
  useEffect(() => {
    if (health.has_model_results) setTrack("managed-model");
  }, [health.has_model_results]);
  const board = rankings.filter((r) => r.track === track);
  return (
    <div className="page overview-page">
      <PageHeading
        eyebrow="WORKSPACE OVERVIEW"
        title="A little less guesswork. A lot more proof."
        description="The open workbench for agents that do more than talk."
        action={
          <span className="live-pill">
            <i /> Workspace online
          </span>
        }
      />
      {!health.read_only && (
        <Link to="/experiments" className="real-experiment-callout">
          <span className="callout-experiment-icon">
            <FlaskConical size={21} />
          </span>
          <div>
            <strong>
              {health.model_configured
                ? "Ready for a real model experiment?"
                : "These starter agents are Python policies—not AI models."}
            </strong>
            <p>
              {health.model_configured
                ? "Compare Direct, Tool user and Verifier on the same model and task. Real calls, real evidence."
                : "Connect OpenRouter, then compare three genuinely different agent implementations. Start here."}
            </p>
          </div>
          <span className="text-link">
            {health.model_configured ? "Run an experiment" : "Set up real AI"}
            <ArrowRight size={15} />
          </span>
        </Link>
      )}
      <div className="hero-grid">
        <section className="hero-panel">
          <div className="hero-copy">
            <div className="hero-kicker">
              <span className="tiny-cross">✳</span> INTELLIGENCE, MEASURED.
            </div>
            <h2>
              Great agents don’t
              <br />
              just claim. <em>They prove.</em>
            </h2>
            <p>
              Put your agents through real, multi-step tasks.
              <br className="desktop-break" /> Measure the outcome. Understand
              every step.
            </p>
            <div className="hero-actions">
              <button className="button dark" onClick={() => openBenchmark()}>
                <Play size={14} fill="currentColor" /> Run a benchmark{" "}
                <ArrowRight size={16} />
              </button>
              <button className="hero-secondary" onClick={openMethods}>
                How it works <ArrowUpRight size={15} />
              </button>
            </div>
            <div className="hero-foot">
              <span>
                <Code2 size={12} /> Open source
              </span>
              <span>
                <ShieldCheck size={12} /> Local first
              </span>
              <span>
                <CircleDot size={12} /> Reproducible tasks
              </span>
            </div>
          </div>
          <ArenaGraphic />
        </section>
        <section className="spotlight-panel">
          <div className="spotlight-top">
            <span>
              <FlaskConical size={13} /> START WITH A CHALLENGE
            </span>
            <span>01 / 12</span>
          </div>
          <div className="spotlight-icon">
            <Layers3 size={25} strokeWidth={1.3} />
            <span className="orbit-dot" />
          </div>
          <h3>
            The numbers look right.
            <br />
            Are they?
          </h3>
          <p>
            Duplicate payments. Voided invoices.
            <br />
            One ledger. Four checks.
          </p>
          <div className="spotlight-tags">
            <span>Data analysis</span>
            <span>Medium</span>
          </div>
          <button
            onClick={() => openBenchmark({ taskId: "invoice-reconciliation" })}
          >
            Try invoice reconciliation <ArrowUpRight size={18} />
          </button>
        </section>
      </div>
      <div className="stats-grid">
        {[
          {
            icon: Users2,
            label: "Registered agents",
            value: overview.agents,
            text: "Ready for the arena",
            detail: "agents",
            path: "/agents",
          },
          {
            icon: Layers3,
            label: "Benchmark tasks",
            value: overview.tasks,
            text: "Across 3 task categories",
            detail: "tasks",
            path: "/tasks",
          },
          {
            icon: Play,
            label: "Recorded runs",
            value: overview.runs,
            text: "Every step, accounted for",
            detail: "runs",
            path: "/runs",
          },
          {
            icon: Check,
            label: "Fully passed runs",
            value: overview.successful_runs,
            text: "All output checks passed",
            detail: "success",
            path: "/runs?result=passed",
          },
        ].map((s) => (
          <Link className="stat-card" to={s.path} key={s.detail}>
            <div className="stat-label">
              {s.label}
              <s.icon size={16} />
            </div>
            <div className="stat-main">
              {s.value.toLocaleString()}
              <span className={`stat-glyph ${s.detail}`}>
                <i />
                <i />
                <i />
                <i />
                <i />
              </span>
            </div>
            <div className="stat-footer">
              <span>{s.text}</span>
              <ArrowUpRight size={13} />
            </div>
          </Link>
        ))}
      </div>
      <section className="card leaderboard-card">
        <div className="section-head">
          <div>
            <h2>
              <Trophy size={18} /> The leaderboard
            </h2>
            <p>Same tasks. Same rules. A level playing field.</p>
          </div>
          <Link className="text-link" to="/leaderboard">
            Full leaderboard <ArrowUpRight size={15} />
          </Link>
        </div>
        <div className="board-controls">
          <div className="segmented">
            <button
              className={track === "reference" ? "active" : ""}
              onClick={() => setTrack("reference")}
            >
              Reference agents
            </button>
            <button
              className={track === "managed-model" ? "active" : ""}
              onClick={() => setTrack("managed-model")}
            >
              Model agents
            </button>
          </div>
          <span className="suite-label">
            <span /> Workbench v1 <span className="separator-dot">·</span>{" "}
            Latest run per task
          </span>
        </div>
        <LeaderTable rows={board.slice(0, 5)} compact />
        <div className="table-foot">
          <span>
            <ShieldCheck size={13} />{" "}
            {track === "reference"
              ? "Reference policies are deterministic baselines, not AI model rankings."
              : "Model costs are unknown unless provider pricing is configured."}
          </span>
          <button onClick={openMethods}>
            Scoring methodology <ArrowUpRight size={13} />
          </button>
        </div>
      </section>
      <div className="overview-bottom">
        <section className="category-section">
          <div className="section-head plain">
            <h2>Different tasks. Different strengths.</h2>
            <Link className="text-link" to="/tasks">
              Explore tasks <ArrowRight size={15} />
            </Link>
          </div>
          <div className="category-grid">
            {overview.categories.map((c) => (
              <Link
                to={`/tasks?category=${encodeURIComponent(c.name)}`}
                className="category-card"
                key={c.name}
              >
                <div
                  className={`category-icon ${c.name.toLowerCase().replace(" ", "-")}`}
                >
                  <CategoryIcon name={c.name} size={21} />
                  <ArrowUpRight size={16} />
                </div>
                <h3>{c.name}</h3>
                <p>
                  {c.name === "Data analysis"
                    ? "Turn messy inputs into reliable answers."
                    : c.name === "Research"
                      ? "Find evidence. Check facts. Cite sources."
                      : "Navigate constraints. Get the job done."}
                </p>
                <div className="category-meta">
                  <span>{c.tasks} tasks</span>
                  <span>{c.runs} runs</span>
                </div>
                <div className="category-pass">
                  <span>All-run success</span>
                  <strong>{pct(c.success_rate)}</strong>
                </div>
                <div className="progress">
                  <i style={{ width: pct(c.success_rate) }} />
                </div>
              </Link>
            ))}
          </div>
        </section>
        <section className="card activity-card">
          <div className="section-head">
            <h2>
              <span className="live-dot" /> Recent activity
            </h2>
            <Link to="/runs" aria-label="View all activity">
              <ChevronRight size={17} />
            </Link>
          </div>
          <div className="activity-list">
            {overview.recent_runs.slice(0, 4).map((r) => (
              <Link to={`/runs/${r.id}`} key={r.id} className="activity-item">
                <span className={`activity-status ${r.passed ? "passed" : ""}`}>
                  {r.passed ? <Check size={13} /> : <CircleDot size={13} />}
                </span>
                <div>
                  <p>
                    <strong>{r.agent_name}</strong>{" "}
                    {r.passed
                      ? "passed a task"
                      : r.status === "failed"
                        ? "hit an error"
                        : "completed a run"}
                  </p>
                  <span>{r.task_title}</span>
                </div>
                <small>{ago(r.created_at)}</small>
              </Link>
            ))}
          </div>
          <div className="activity-footer">
            <Clock3 size={12} /> Actual executions. No simulated run data.
          </div>
        </section>
      </div>
      <div className="workspace-footer">
        <span>
          <span className="footer-star">✳</span> Built to make progress
          measurable.
        </span>
        <span>
          Workbench v1.0.0 <span> / </span> <code>{overview.suite_hash}</code>
        </span>
      </div>
    </div>
  );
}
