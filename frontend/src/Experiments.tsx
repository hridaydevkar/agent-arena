import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Download,
  FlaskConical,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useWorkspace } from "./context";
import { api, download, duration, money, pct, post } from "./api";
import { AgentAvatar, Badge, PageHeading } from "./ui";
import { CodeBlock } from "./Docs";
import type { Job, ModelOption, Run } from "./types";

const designs = [
  {
    id: "direct",
    icon: Sparkles,
    name: "Direct",
    color: "lavender",
    label: "THE BASELINE",
    text: "All fixtures in one prompt. One model call. No tools or review.",
    path: ["All data", "Model", "Answer"],
  },
  {
    id: "tools",
    icon: Wrench,
    name: "Tool user",
    color: "green",
    label: "THE OPERATOR",
    text: "The model retrieves named fixtures and can use arithmetic tools before answering.",
    path: ["Task", "Tools ↔ model", "Answer"],
  },
  {
    id: "verify",
    icon: ShieldCheck,
    name: "Verifier",
    color: "amber",
    label: "THE REVIEWER",
    text: "A tool-using solver, then a separate review call with the original fixtures and draft—not the expected answers.",
    path: ["Tools ↔ model", "Review", "Answer"],
  },
];

export default function Experiments() {
  const { health, tasks, agents, jobs, refresh, toast } = useWorkspace();
  const [model, setModel] = useState(health.model);
  const [catalog, setCatalog] = useState<ModelOption[]>([]);
  const [catalogBusy, setCatalogBusy] = useState(false);
  const [catalogError, setCatalogError] = useState("");
  const [taskIds, setTaskIds] = useState(["invoice-reconciliation"]);
  const [showAll, setShowAll] = useState(false);
  const [budget, setBudget] = useState(6);
  const [tokens, setTokens] = useState(1800);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState(
    () => localStorage.getItem("arena-experiment-job") || "",
  );
  const [job, setJob] = useState<Job | null>(null);
  const [jobError, setJobError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [selectedRuns, setSelectedRuns] = useState<Run[]>([]);
  const selectedModel = catalog.find((m) => m.id === model);
  const active = !!job && ["queued", "running"].includes(job.status);
  const core = [
    "invoice-reconciliation",
    "conflicting-sources",
    "inventory-restock",
  ];
  const shownTasks = showAll ? tasks : tasks.filter((t) => core.includes(t.id));
  const maximum = taskIds.length * (1 + budget * 2);
  const recentModelJobs = jobs.filter((j) =>
    j.agent_ids.every(
      (id) => agents.find((a) => a.id === id)?.strategy === "model",
    ),
  );

  useEffect(() => {
    if (!jobId || health.read_only) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await api<Job>(`/jobs/${jobId}`);
        if (!live) return;
        const records = await api<{ items: Run[] }>(
          `/runs?job_id=${encodeURIComponent(next.id)}&limit=100`,
        );
        if (!live) return;
        setSelectedRuns(records.items);
        setJob(next);
        setJobError("");
        if (["queued", "running"].includes(next.status))
          timer = setTimeout(poll, 1500);
        else await refresh();
      } catch (e) {
        if (live) setJobError((e as Error).message);
      }
    };
    setJob(null);
    setSelectedRuns([]);
    poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [jobId, health.read_only]);

  async function loadModels() {
    setCatalogBusy(true);
    setCatalogError("");
    try {
      const result = await api<{ items: ModelOption[] }>("/models");
      setCatalog(result.items);
    } catch (e) {
      setCatalogError((e as Error).message);
    } finally {
      setCatalogBusy(false);
    }
  }
  async function start() {
    setBusy(true);
    setError("");
    try {
      const result = await post<Job>("/experiments", {
        model_id: model.trim(),
        task_ids: taskIds,
        max_calls: budget,
        max_output_tokens: tokens,
        acknowledge_provider_usage: consent,
      });
      setJob(result);
      setJobId(result.id);
      localStorage.setItem("arena-experiment-job", result.id);
      await refresh();
      toast("Three distinct agent implementations are now queued.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function exportReport() {
    if (!job) return;
    setExporting(true);
    try {
      const report = await api<unknown>(`/jobs/${job.id}/report`);
      download(JSON.stringify(report, null, 2), "results.json");
      toast(
        "Summary-only report downloaded. Review it before publishing. Raw prompts and outputs are excluded.",
      );
    } catch (e) {
      toast((e as Error).message, true);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="page experiments-page">
      <PageHeading
        eyebrow="REAL MODEL EXPERIMENTS"
        title="Same model. Three ways to solve."
        description="Does tool use or a verification pass actually improve the result? Run the comparison and find out."
        action={
          <Badge tone={health.model_configured ? "green" : ""}>
            {health.read_only
              ? "Public results · execution disabled"
              : health.model_configured
                ? `${health.provider} configured`
                : "Connect a provider to begin"}
          </Badge>
        }
      />
      <div className="architecture-cards">
        {designs.map((d) => (
          <article className={`card architecture-card ${d.color}`} key={d.id}>
            <div className="architecture-title">
              <span className={`info-panel-icon ${d.color}`}>
                <d.icon size={20} />
              </span>
              <span className="eyebrow">{d.label}</span>
              <Badge>
                {d.id === "direct"
                  ? "1 call"
                  : d.id === "verify"
                    ? `Up to ${budget} calls incl. review`
                    : `Up to ${budget} calls`}
              </Badge>
            </div>
            <h2>{d.name}</h2>
            <p>{d.text}</p>
            <div className="protocol-path">
              {d.path.map((part, i) => (
                <span key={part}>
                  {i > 0 && <ArrowRight size={11} />}
                  <code>{part}</code>
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
      {health.read_only ? (
        <section className="card experiment-public">
          <ShieldCheck size={28} />
          <h2>This is a results gallery, not a shared API key.</h2>
          <p>
            Browse published metrics and comparisons. To run your own agents,
            download the open-source workbench and connect your own provider
            locally.
          </p>
          <Link className="button primary" to="/docs">
            Local setup guide <ArrowRight size={15} />
          </Link>
        </section>
      ) : (
        <>
          {!health.model_configured && (
            <div className="card experiment-setup">
              <div>
                <span className="eyebrow">FIRST, CONNECT OPENROUTER</span>
                <h2>Your computer hosts the app. The cloud runs the model.</h2>
                <p>
                  Stop the server, run the setup command in your project folder,
                  and restart. Enter your key only in your own terminal. Setup
                  checks metadata; it does not request model generation.
                </p>
                <CodeBlock
                  code={
                    ".venv/bin/python scripts/setup_openrouter.py\npython3 scripts/start.py --port 8002"
                  }
                />
                <p className="small-text">
                  The key is stored in a git-ignored local .env file. The
                  launcher now loads this file automatically. Your computer does
                  not need to load model weights.
                </p>
              </div>
              <div className="setup-checklist">
                <strong>Your first real result</strong>
                <span>
                  <CheckCircle2 size={15} /> Use a specific model with tool
                  support
                </span>
                <span>
                  <CheckCircle2 size={15} /> Start with just one task
                </span>
                <span>
                  <CheckCircle2 size={15} /> Inspect model calls, not just a
                  score
                </span>
                <span>
                  <CheckCircle2 size={15} /> Publish measured results, not
                  promises
                </span>
                <Link className="text-link" to="/settings">
                  Connection settings <ArrowUpRight size={14} />
                </Link>
              </div>
            </div>
          )}
          <section className="card experiment-config">
            <div className="section-head">
              <div>
                <h2>
                  <FlaskConical size={18} /> Design the comparison
                </h2>
                <p>
                  One attempt per architecture and task. Same model ID; not a
                  confidence estimate or a guarantee of reproducibility.
                </p>
              </div>
              <Badge>Workbench v1</Badge>
            </div>
            <div className="experiment-config-grid">
              <div className="experiment-controls">
                <label htmlFor="experiment-model">01 / Model ID</label>
                <div className="model-input-row">
                  <input
                    id="experiment-model"
                    list="model-catalog"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="provider/model-name"
                    disabled={!health.model_configured}
                  />
                  <button
                    className="button small"
                    onClick={loadModels}
                    disabled={catalogBusy || !health.model_configured}
                  >
                    {catalogBusy ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      <RefreshCw size={14} />
                    )}{" "}
                    Browse models
                  </button>
                </div>
                <datalist id="model-catalog">
                  {catalog
                    .filter(
                      (m) =>
                        m.supports_tools !== false &&
                        !["openrouter/free", "openrouter/auto"].includes(m.id),
                    )
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.free
                          ? "Free token pricing · quota-limited"
                          : `$${m.input_per_million ?? "?"} in / $${m.output_per_million ?? "?"} out per M tokens`}
                      </option>
                    ))}
                </datalist>
                {catalog.length > 0 && (
                  <div className="catalog-picks">
                    <span>
                      Tool-capable, free-priced entries from the live catalogue:
                    </span>
                    {catalog
                      .filter(
                        (m) =>
                          m.free &&
                          m.supports_tools &&
                          !["openrouter/free", "openrouter/auto"].includes(
                            m.id,
                          ),
                      )
                      .slice(0, 5)
                      .map((m) => (
                        <button key={m.id} onClick={() => setModel(m.id)}>
                          {m.id}
                        </button>
                      ))}
                    <small>
                      Catalogue metadata is not a guarantee of capacity or
                      successful tool calling.
                    </small>
                  </div>
                )}
                {catalogError && (
                  <div className="form-error">{catalogError}</div>
                )}
                {selectedModel?.supports_tools === false && (
                  <div className="notice amber">
                    This model does not advertise tool support. Select a
                    different model for this comparison.
                  </div>
                )}
                <p className="field-help">
                  Use a specific model ID, not openrouter/free or
                  openrouter/auto. Actual returned model IDs are recorded in
                  each trace. Credentials stay on the server.
                </p>
                <label>02 / Execution budgets</label>
                <div className="budget-grid">
                  <div>
                    <label htmlFor="experiment-budget">
                      Calls per tool-based agent
                    </label>
                    <select
                      id="experiment-budget"
                      value={budget}
                      onChange={(e) => setBudget(Number(e.target.value))}
                    >
                      {[4, 6, 8].map((n) => (
                        <option key={n} value={n}>
                          {n} calls maximum
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="experiment-tokens">
                      Output tokens per call
                    </label>
                    <select
                      id="experiment-tokens"
                      value={tokens}
                      onChange={(e) => setTokens(Number(e.target.value))}
                    >
                      {[1024, 1800, 3072, 4096].map((n) => (
                        <option key={n} value={n}>
                          {n.toLocaleString()} tokens
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <p className="field-help">
                  Direct always makes one call. Verifier reserves one call
                  within its budget for review. Input tokens also cost money. No
                  automatic retries or model fallback.
                </p>
              </div>
              <div className="experiment-task-picker">
                <label>03 / Choose a challenge</label>
                <p>
                  Start with one. You can expand after the connection works.
                </p>
                {shownTasks.map((t) => (
                  <label className="experiment-task" key={t.id}>
                    <input
                      type="checkbox"
                      checked={taskIds.includes(t.id)}
                      onChange={() =>
                        setTaskIds((ids) =>
                          ids.includes(t.id)
                            ? ids.filter((id) => id !== t.id)
                            : [...ids, t.id],
                        )
                      }
                    />
                    <span>
                      <strong>{t.title}</strong>
                      <small>
                        {t.category} · {t.difficulty}
                      </small>
                    </span>
                  </label>
                ))}
                <button
                  className="text-link"
                  onClick={() => setShowAll(!showAll)}
                >
                  {showAll ? "Show starter challenges" : "Show all 12 tasks"}{" "}
                  <ArrowRight size={13} />
                </button>
              </div>
            </div>
            <div className="experiment-launch">
              <div>
                <strong>
                  {taskIds.length * 3} executions · up to {maximum} model
                  requests
                </strong>
                <p>
                  Provider charges and rate limits may apply—even successful
                  authentication does not guarantee availability.
                </p>
                <label className="consent">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                  />{" "}
                  I understand the request limit is not a dollar-spend cap. I
                  have checked my provider limits.
                </label>
              </div>
              <button
                className="button primary"
                disabled={
                  !health.model_configured ||
                  !taskIds.length ||
                  !consent ||
                  busy ||
                  active ||
                  !model.trim() ||
                  selectedModel?.supports_tools === false
                }
                onClick={start}
              >
                {busy ? (
                  <Loader2 size={16} className="spin" />
                ) : (
                  <FlaskConical size={16} />
                )}{" "}
                Run three-agent comparison <ArrowRight size={16} />
              </button>
            </div>
            {error && (
              <div className="form-error experiment-error" role="alert">
                {error}
              </div>
            )}
          </section>
          {(job || recentModelJobs.length > 0 || jobError) && (
            <section className="card experiment-results">
              <div className="section-head">
                <div>
                  <h2>
                    {active && <Loader2 size={17} className="spin" />}{" "}
                    Experiment evidence
                  </h2>
                  <p>
                    {job
                      ? `${job.completed} / ${job.total} executions recorded · ${job.failed} execution errors · ${job.status}`
                      : "Choose a recorded job to inspect."}
                  </p>
                </div>
                <select
                  aria-label="Select experiment job"
                  value={jobId}
                  onChange={(e) => {
                    setJobId(e.target.value);
                    localStorage.setItem(
                      "arena-experiment-job",
                      e.target.value,
                    );
                  }}
                >
                  <option value="">Choose a job</option>
                  {recentModelJobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.id} · {j.status}
                    </option>
                  ))}
                </select>
              </div>
              {jobError && (
                <div className="notice amber">
                  {jobError}. This may be a different workspace; choose an
                  available job above.
                </div>
              )}
              {job && (
                <>
                  <div className="experiment-job-meta">
                    <code>{job.id}</code>
                    <div className="progress">
                      <i style={{ width: pct(job.completed / job.total) }} />
                    </div>
                    {active ? (
                      <button
                        className="button small"
                        disabled={job.cancel_requested}
                        onClick={async () => {
                          try {
                            setJob(
                              await post<Job>(`/jobs/${job.id}/cancel`, {}),
                            );
                          } catch (e) {
                            toast((e as Error).message, true);
                          }
                        }}
                      >
                        {job.cancel_requested
                          ? "Cancellation requested"
                          : "Cancel after current task"}
                      </button>
                    ) : (
                      <button
                        className="button small"
                        disabled={
                          exporting ||
                          job.status !== "completed" ||
                          !selectedRuns.some((r) => r.status === "completed")
                        }
                        onClick={exportReport}
                      >
                        <Download size={14} /> Export public report
                      </button>
                    )}
                  </div>
                  <div className="table-scroll">
                    <table className="runs-table">
                      <thead>
                        <tr>
                          <th>Architecture / agent</th>
                          <th>Task</th>
                          <th>Quality</th>
                          <th>Calls</th>
                          <th>Duration</th>
                          <th>Cost</th>
                          <th>Evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...selectedRuns]
                          .sort(
                            (a, b) =>
                              job.agent_ids.indexOf(a.agent_id) -
                              job.agent_ids.indexOf(b.agent_id),
                          )
                          .map((r) => (
                            <tr key={r.id}>
                              <td>
                                <div className="agent-cell">
                                  <AgentAvatar
                                    agent={agents.find(
                                      (a) => a.id === r.agent_id,
                                    )}
                                  />
                                  <span>
                                    <strong>{r.architecture || "tools"}</strong>
                                    <small>{r.agent_name}</small>
                                  </span>
                                </div>
                              </td>
                              <td className="run-task">
                                <strong>{r.task_title}</strong>
                                <small>
                                  {r.status === "failed"
                                    ? r.error || "Execution error"
                                    : r.passed
                                      ? "All output checks passed"
                                      : "Some output checks failed"}
                                </small>
                              </td>
                              <td>
                                <Badge
                                  tone={
                                    r.status === "failed"
                                      ? "red"
                                      : r.passed
                                        ? "green"
                                        : "amber"
                                  }
                                >
                                  {r.status === "failed"
                                    ? "Error"
                                    : pct(r.score)}
                                </Badge>
                              </td>
                              <td>{r.model_calls ?? "—"}</td>
                              <td>{duration(r.duration_ms)}</td>
                              <td title={r.cost_source || "Unknown source"}>
                                {money(r.cost_usd)}
                              </td>
                              <td>
                                <Link
                                  className="text-link"
                                  to={`/runs/${r.id}`}
                                >
                                  Replay <ArrowUpRight size={14} />
                                </Link>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                  {!selectedRuns.length && (
                    <p className="experiment-await">
                      {active
                        ? "Waiting for the first model execution. Cloud models can take a minute or more; keep this page open or return later."
                        : "No execution records are available for this job."}
                    </p>
                  )}
                  {job.run_ids.length >= 2 && (
                    <div className="table-foot">
                      <span>
                        Compare identical tasks. Review the traces before
                        drawing conclusions.
                      </span>
                      <Link
                        className="text-link"
                        to={`/compare?task=${job.task_ids[0]}&a=${job.agent_ids[0]}&b=${job.agent_ids[1]}`}
                      >
                        Direct vs. tool user <ArrowRight size={13} />
                      </Link>
                    </div>
                  )}
                </>
              )}
            </section>
          )}
        </>
      )}
      <div className="notice">
        <ShieldCheck size={19} />
        <span>
          This tests three real implementations on public synthetic fixtures.
          Verification is a model review, not an oracle, and can make answers
          worse. One attempt per task is exploratory evidence—not proof that an
          architecture is better. Publish limitations alongside results.
        </span>
      </div>
    </div>
  );
}
