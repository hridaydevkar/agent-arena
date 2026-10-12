import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDashed,
  FlaskConical,
  History,
  Search,
} from "lucide-react";
import { useWorkspace } from "./context";
import { AgentAvatar, Badge, Empty, PageHeading } from "./ui";
import { ago, download, duration, money, pct, post } from "./api";
export default function Runs() {
  const { agents, runs, jobs, openBenchmark, refresh, toast } = useWorkspace();
  const [params] = useSearchParams();
  const [search, setSearch] = useState("");
  const [result, setResult] = useState(params.get("result") || "all");
  const [agent, setAgent] = useState("all");
  const [page, setPage] = useState(0);
  const filtered = runs.filter(
    (r) =>
      `${r.agent_name} ${r.task_title} ${r.id}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (agent === "all" || r.agent_id === agent) &&
      (result === "all" ||
        (result === "passed"
          ? r.passed
          : result === "failed"
            ? r.status === "failed"
            : !r.passed && r.status !== "failed")),
  );
  const active = jobs.filter((j) => ["queued", "running"].includes(j.status));
  const count = 12;
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(filtered.length / count) - 1),
  );
  return (
    <div className="page">
      <PageHeading
        eyebrow="THE EXECUTION LOG"
        title="Every run tells a story."
        description="Explore outcomes, inspect traces, and see what actually happened."
        action={
          <>
            <button
              className="button"
              onClick={() =>
                download(
                  JSON.stringify(filtered, null, 2),
                  "arena-run-summaries.json",
                )
              }
            >
              <ArrowDownToLine size={15} /> Export summaries
            </button>
            <button className="button primary" onClick={() => openBenchmark()}>
              <FlaskConical size={15} /> New run
            </button>
          </>
        }
      />
      {active.map((j) => (
        <div className="active-job" key={j.id}>
          <CircleDashed size={20} className="spin" />
          <div>
            <strong>Benchmark {j.status}</strong>
            <p>
              {j.completed} of {j.total} executions completed · {j.failed}{" "}
              errors
            </p>
            <div className="progress">
              <i style={{ width: pct(j.completed / j.total) }} />
            </div>
          </div>
          <button
            className="button small"
            disabled={j.cancel_requested}
            onClick={async () => {
              try {
                await post(`/jobs/${j.id}/cancel`, {});
                toast(
                  "Cancellation requested. The current task will finish first.",
                );
                await refresh();
              } catch (e) {
                toast((e as Error).message, true);
              }
            }}
          >
            {j.cancel_requested ? "Cancelling…" : "Cancel job"}
          </button>
        </div>
      ))}
      <section className="card">
        <div className="filter-bar">
          <div className="search-field">
            <Search size={16} />
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              placeholder="Search agents, tasks, or run IDs…"
              aria-label="Search runs"
            />
          </div>
          <div className="filter-right">
            <select
              aria-label="Filter runs by agent"
              value={agent}
              onChange={(e) => {
                setAgent(e.target.value);
                setPage(0);
              }}
            >
              <option value="all">All agents</option>
              {agents.map((a) => (
                <option value={a.id} key={a.id}>
                  {a.name}
                </option>
              ))}
              <option value="sdk-external">SDK imports</option>
            </select>
            <select
              aria-label="Filter runs by result"
              value={result}
              onChange={(e) => {
                setResult(e.target.value);
                setPage(0);
              }}
            >
              <option value="all">All results</option>
              <option value="passed">Passed</option>
              <option value="partial">Checks failed</option>
              <option value="failed">Execution error</option>
            </select>
          </div>
        </div>
        {filtered.length ? (
          <div className="table-scroll">
            <table className="runs-table">
              <thead>
                <tr>
                  <th>Agent / run</th>
                  <th>Task</th>
                  <th>Outcome</th>
                  <th>Quality</th>
                  <th>Duration</th>
                  <th>Cost</th>
                  <th>Recorded</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered
                  .slice(currentPage * count, currentPage * count + count)
                  .map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link className="agent-cell" to={`/runs/${r.id}`}>
                          <AgentAvatar
                            agent={
                              agents.find((a) => a.id === r.agent_id) || {
                                name: r.agent_name,
                              }
                            }
                          />
                          <span>
                            <strong>{r.agent_name}</strong>
                            <small className="mono">{r.id.slice(0, 12)}</small>
                          </span>
                        </Link>
                      </td>
                      <td className="run-task">
                        <Link to={`/tasks/${r.task_id}`}>{r.task_title}</Link>
                        <small>
                          {r.category}
                          {r.provenance === "self-reported" &&
                            " · Self-reported"}
                        </small>
                      </td>
                      <td>
                        <Badge
                          tone={
                            r.passed
                              ? "green"
                              : r.status === "failed"
                                ? "red"
                                : "amber"
                          }
                        >
                          {r.passed ? (
                            <CheckCircle2 size={11} />
                          ) : (
                            <CircleDashed size={11} />
                          )}{" "}
                          {r.passed
                            ? "Passed"
                            : r.status === "failed"
                              ? "Error"
                              : "Checks failed"}
                        </Badge>
                      </td>
                      <td className="numeric">{pct(r.score)}</td>
                      <td className="numeric muted">
                        {duration(r.duration_ms)}
                      </td>
                      <td className="numeric">{money(r.cost_usd)}</td>
                      <td
                        className="muted small-text"
                        title={new Date(r.created_at).toLocaleString()}
                      >
                        {ago(r.created_at)}
                      </td>
                      <td>
                        <Link
                          to={`/runs/${r.id}`}
                          className="row-arrow"
                          aria-label={`Replay ${r.id}`}
                        >
                          <ArrowUpRight size={17} />
                        </Link>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No runs here yet"
            description="Try another filter or start a benchmark to record your first trace."
            action={
              <button className="button" onClick={() => openBenchmark()}>
                Run a benchmark
              </button>
            }
          />
        )}
        <div className="table-foot">
          <span>
            {filtered.length
              ? `${currentPage * count + 1}–${Math.min((currentPage + 1) * count, filtered.length)}`
              : "0"}{" "}
            of {filtered.length} matching runs{" "}
            <span className="separator-dot">·</span> Latest 1,000 loaded
          </span>
          <div className="pagination">
            <button
              className="icon-button"
              aria-label="Previous page"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
            >
              <ChevronLeft size={16} />
            </button>
            <span>
              {currentPage + 1} /{" "}
              {Math.max(1, Math.ceil(filtered.length / count))}
            </span>
            <button
              className="icon-button"
              aria-label="Next page"
              disabled={(currentPage + 1) * count >= filtered.length}
              onClick={() => setPage(currentPage + 1)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>
      <div className="notice">
        <History size={18} />
        <span>
          Starter runs are executed on first launch, not fabricated. SDK imports
          carry a self-reported label and never affect the managed leaderboards.
        </span>
      </div>
      {jobs.length > 0 && (
        <section className="card jobs-section">
          <div className="section-head">
            <h2>Benchmark jobs</h2>
            <span className="muted small-text">Latest 50 jobs</span>
          </div>
          {jobs
            .filter((j) => !["queued", "running"].includes(j.status))
            .slice(0, 6)
            .map((j) => (
              <div className="job-row" key={j.id}>
                <span className="mono muted">{j.id.slice(0, 16)}</span>
                <span>
                  {j.completed} / {j.total} runs
                </span>
                <Badge
                  tone={
                    j.status === "completed" && !j.failed ? "green" : "amber"
                  }
                >
                  {j.status}
                  {j.failed ? ` · ${j.failed} errors` : ""}
                </Badge>
                <span className="muted small-text">{ago(j.created_at)}</span>
                {j.run_ids.length > 0 && (
                  <Link
                    className="text-link"
                    to={`/runs/${j.run_ids[j.run_ids.length - 1]}`}
                  >
                    Last run <ArrowRight size={14} />
                  </Link>
                )}
              </div>
            ))}
        </section>
      )}
    </div>
  );
}
