import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Code2,
  Copy,
  FlaskConical,
  Loader2,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  X,
} from "lucide-react";
import { useWorkspace } from "./context";
import type { BenchPreset } from "./context";
import {
  AgentAvatar,
  Badge,
  CategoryIcon,
  CheckMark,
  Empty,
  Modal,
} from "./ui";
import { api, pct, post } from "./api";
import type { Agent, Job } from "./types";
import { CodeBlock } from "./Docs";

export function BenchmarkDialog({
  preset,
  onClose,
}: {
  preset: BenchPreset;
  onClose: () => void;
}) {
  const { agents, tasks, refresh, toast } = useWorkspace();
  const navigate = useNavigate();
  const [agentIds, setAgentIds] = useState<string[]>(
    preset.agentId
      ? [preset.agentId]
      : [agents.find((a) => a.id === "atlas")?.id || agents[0]?.id].filter(
          Boolean,
        ),
  );
  const [taskIds, setTaskIds] = useState<string[]>(
    preset.taskId ? [preset.taskId] : tasks.map((t) => t.id),
  );
  const [mode, setMode] = useState(preset.taskId ? "custom" : "full");
  const [job, setJob] = useState<Job | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [consent, setConsent] = useState(false);
  const billable = agents.some(
    (a) => agentIds.includes(a.id) && a.strategy === "model",
  );
  const maxRequests =
    taskIds.length *
    agents
      .filter((a) => agentIds.includes(a.id) && a.strategy === "model")
      .reduce(
        (total, a) =>
          total + (a.architecture === "direct" ? 1 : a.max_calls || 8),
        0,
      );
  const maxTokens = Math.max(
    0,
    ...agents
      .filter((a) => agentIds.includes(a.id) && a.strategy === "model")
      .map((a) => a.max_output_tokens || 1800),
  );
  const active = job && ["queued", "running"].includes(job.status);
  useEffect(() => {
    if (!job || !active) return;
    let alive = true;
    const interval = setInterval(async () => {
      try {
        const next = await api<Job>(`/jobs/${job.id}`);
        if (!alive) return;
        setJob(next);
        if (!["queued", "running"].includes(next.status)) await refresh();
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    }, 750);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [job?.id, Boolean(active)]);
  const toggleAgent = (id: string) =>
    setAgentIds((ids) =>
      ids.includes(id)
        ? ids.filter((x) => x !== id)
        : ids.length < 8
          ? [...ids, id]
          : ids,
    );
  const toggleTask = (id: string) =>
    setTaskIds((ids) =>
      ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id],
    );
  async function submit() {
    setSending(true);
    setError("");
    try {
      const created = await post<Job>("/benchmarks", {
        agent_ids: agentIds,
        task_ids: taskIds,
      });
      setJob(created);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }
  return (
    <Modal
      title={
        job
          ? active
            ? "Your benchmark is running."
            : "The evidence is in."
          : "Put an agent to the test."
      }
      subtitle={
        job
          ? "Every execution is recorded in your workspace."
          : "Choose your contenders and set the challenge."
      }
      onClose={onClose}
      wide
    >
      {job ? (
        <div className="job-result">
          <span className={`job-result-icon ${active ? "active" : ""}`}>
            {active ? (
              <Loader2 size={35} className="spin" />
            ) : job.status === "completed" && !job.failed ? (
              <CheckCircle2 size={35} />
            ) : (
              <CircleDashed size={35} />
            )}
          </span>
          <h3>
            {active
              ? `Running ${job.total} executions`
              : job.status === "completed"
                ? `${job.completed} executions recorded`
                : `Benchmark ${job.status}`}
          </h3>
          <p>
            {job.completed} / {job.total} completed
            {job.failed ? ` · ${job.failed} execution errors` : ""}
          </p>
          <div className="progress job-progress">
            <i style={{ width: pct(job.completed / job.total) }} />
          </div>
          <span className="mono small-text muted">{job.id}</span>
          {error && <div className="form-error">{error}</div>}
          <div className="job-result-actions">
            {active ? (
              <>
                <button
                  className="button"
                  onClick={() => {
                    onClose();
                    navigate("/runs");
                  }}
                >
                  Continue in background
                </button>
                <button
                  className="button"
                  disabled={job.cancel_requested}
                  onClick={async () => {
                    try {
                      setJob(await post<Job>(`/jobs/${job.id}/cancel`, {}));
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  {job.cancel_requested ? "Cancelling…" : "Cancel job"}
                </button>
              </>
            ) : (
              <>
                <button
                  className="button"
                  onClick={() => {
                    onClose();
                    navigate("/leaderboard");
                  }}
                >
                  View leaderboard
                </button>
                {job.run_ids.length > 0 && (
                  <button
                    className="button primary"
                    onClick={() => {
                      onClose();
                      navigate(`/runs/${job.run_ids[0]}`);
                    }}
                  >
                    Inspect first run <ArrowRight size={15} />
                  </button>
                )}
              </>
            )}
          </div>
          <p className="job-footnote">
            Closing this dialog does not cancel a running benchmark.
          </p>
        </div>
      ) : (
        <>
          <div className="modal-body">
            <div className="form-section-title">
              <span>01</span>
              <h3>Select agents</h3>
              <small>{agentIds.length} selected · max 8</small>
            </div>
            <div className="agent-selection">
              {agents.map((a) => (
                <button
                  className={`agent-option ${agentIds.includes(a.id) ? "selected" : ""}`}
                  key={a.id}
                  onClick={() => toggleAgent(a.id)}
                  aria-pressed={agentIds.includes(a.id)}
                >
                  <AgentAvatar agent={a} />
                  <span>
                    <strong>{a.name}</strong>
                    <small>
                      {a.reference ? `${a.strategy} reference` : a.model}
                    </small>
                  </span>
                  <CheckMark checked={agentIds.includes(a.id)} />
                </button>
              ))}
            </div>
            <div className="form-section-title">
              <span>02</span>
              <h3>Choose the tasks</h3>
              <small>{taskIds.length} selected</small>
            </div>
            <div className="suite-options">
              <button
                className={mode === "full" ? "selected" : ""}
                onClick={() => {
                  setMode("full");
                  setTaskIds(tasks.map((t) => t.id));
                }}
              >
                <LayersIcon />
                <span>
                  <strong>Full workbench</strong>
                  <small>All 12 tasks · 3 categories</small>
                </span>
                <CheckMark checked={mode === "full"} />
              </button>
              <button
                className={mode === "custom" ? "selected" : ""}
                onClick={() => {
                  setMode("custom");
                  setTaskIds(preset.taskId ? [preset.taskId] : [tasks[0].id]);
                }}
              >
                <FlaskConical size={20} />
                <span>
                  <strong>Custom selection</strong>
                  <small>Focus on a specific challenge</small>
                </span>
                <CheckMark checked={mode === "custom"} />
              </button>
            </div>
            {mode === "custom" && (
              <div className="task-selection">
                {tasks.map((t) => (
                  <label key={t.id}>
                    <input
                      type="checkbox"
                      checked={taskIds.includes(t.id)}
                      onChange={() => toggleTask(t.id)}
                    />
                    <CategoryIcon name={t.category} size={14} />
                    <span>{t.title}</span>
                    <Badge tone={t.difficulty.toLowerCase()}>
                      {t.difficulty}
                    </Badge>
                  </label>
                ))}
              </div>
            )}
            <div className={`notice ${billable ? "amber" : "green"}`}>
              <ShieldCheck size={18} />
              <span>
                {billable
                  ? `Model-backed runs call your configured provider. Maximum ${maxRequests} model requests in this job, up to ${maxTokens.toLocaleString()} output tokens per request. Provider usage may be billed.`
                  : "Reference agents run locally with read-only fixtures. No API keys, no model charges, no external actions."}
              </span>
            </div>
            {billable && (
              <label className="consent">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />{" "}
                I understand this job may incur provider charges.
              </label>
            )}
            {error && <div className="form-error">{error}</div>}
          </div>
          <div className="modal-footer">
            <div>
              <strong>{agentIds.length * taskIds.length} executions</strong>
              <span>Workbench v1 · independent output checks</span>
            </div>
            <button
              className="button primary"
              disabled={
                sending ||
                !agentIds.length ||
                !taskIds.length ||
                (billable && !consent)
              }
              onClick={submit}
            >
              {sending ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <FlaskConical size={16} />
              )}{" "}
              Start benchmark <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
function LayersIcon() {
  return <Code2 size={20} />;
}

export function AgentDialog({ onClose }: { onClose: () => void }) {
  const { health, refresh, toast, openBenchmark } = useWorkspace();
  const [tab, setTab] = useState("Managed agent");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategy, setStrategy] = useState("balanced");
  const [architecture, setArchitecture] = useState("tools");
  const [modelId, setModelId] = useState(health.model);
  const [color, setColor] = useState("#586b43");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const agent = await post<Agent>("/agents", {
        name: name.trim(),
        description,
        strategy,
        architecture,
        model_id: strategy === "model" ? modelId : null,
        color,
      });
      await refresh();
      toast(`${agent.name} is registered. Time to benchmark.`);
      onClose();
      openBenchmark({ agentId: agent.id });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal
      title="A new contender."
      subtitle="Give your agent a place in the workbench."
      onClose={onClose}
    >
      <div className="category-tabs">
        {["Managed agent", "Bring your own SDK"].map((t) => (
          <button
            key={t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Managed agent" ? (
        <form onSubmit={submit}>
          <div className="modal-body agent-form">
            <label htmlFor="agent-name">Agent name</label>
            <input
              id="agent-name"
              placeholder="e.g. Northstar"
              value={name}
              minLength={2}
              maxLength={40}
              required
              onChange={(e) => setName(e.target.value)}
            />
            <label htmlFor="agent-desc">
              Description <span>optional</span>
            </label>
            <textarea
              id="agent-desc"
              placeholder="What makes this agent different?"
              value={description}
              maxLength={300}
              onChange={(e) => setDescription(e.target.value)}
            />
            <label htmlFor="agent-strategy">Execution policy</label>
            <select
              id="agent-strategy"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
            >
              <optgroup label="Local reference policies · no LLM">
                <option value="methodical">
                  Methodical — full constraint handling
                </option>
                <option value="balanced">
                  Balanced — limited edge-case handling
                </option>
                <option value="greedy">
                  Greedy — naive aggregation baseline
                </option>
                <option value="minimal">
                  Minimal — incomplete output baseline
                </option>
              </optgroup>
              <optgroup label="Model-backed agent">
                <option value="model" disabled={!health.model_configured}>
                  {health.model_configured
                    ? health.model
                    : "Configure provider in server environment first"}
                </option>
              </optgroup>
            </select>
            <p className="field-help">
              {strategy === "model"
                ? "Uses the configured provider with a bounded tool loop. Running tasks may incur charges."
                : "Creates a new identity using an existing transparent policy. For your own logic, use the SDK tab."}
            </p>
            {strategy === "model" && (
              <>
                <label htmlFor="agent-model">Model ID</label>
                <input
                  id="agent-model"
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  required
                />
                <label htmlFor="agent-architecture">Agent architecture</label>
                <select
                  id="agent-architecture"
                  value={architecture}
                  onChange={(e) => setArchitecture(e.target.value)}
                >
                  <option value="direct">
                    Direct — all fixtures, one call
                  </option>
                  <option value="tools">
                    Tool user — retrieve fixtures and calculate
                  </option>
                  <option value="verify">
                    Verifier — tool solver plus independent review
                  </option>
                </select>
                <p className="field-help">
                  Maximum 6 requests per task (Direct uses 1), up to 1,800
                  output tokens per request. Use Experiments to compare all
                  three.
                </p>
              </>
            )}
            <label>Agent color</label>
            <div className="color-picker">
              {[
                "#586b43",
                "#6a74aa",
                "#c58245",
                "#8b6c97",
                "#448385",
                "#ab6464",
              ].map((c) => (
                <button
                  type="button"
                  key={c}
                  aria-label={`Choose color ${c}`}
                  aria-pressed={color === c}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                >
                  {color === c && <Check size={17} />}
                </button>
              ))}
            </div>
            {error && <div className="form-error">{error}</div>}
          </div>
          <div className="modal-footer">
            <span className="small-text muted">
              Version 1.0.0 · local workspace
            </span>
            <button
              className="button primary"
              disabled={saving || name.trim().length < 2}
            >
              {saving ? (
                <Loader2 size={15} className="spin" />
              ) : (
                <Plus size={15} />
              )}{" "}
              Register & benchmark
            </button>
          </div>
        </form>
      ) : (
        <div className="modal-body sdk-onboarding">
          <span className="sdk-icon">
            <Terminal size={25} />
          </span>
          <h3>Bring the implementation. Keep the control.</h3>
          <p>
            Implement the SDK’s <code>Agent</code> interface and run your code
            on your own computer. The arena imports the result and trace, not
            your source code.
          </p>
          <CodeBlock
            code={
              "pip install -e .\narena run examples/revenue_agent.py \\\n  --task revenue-by-region --submit"
            }
          />
          <div className="notice amber">
            <ShieldCheck size={18} />
            <span>
              SDK runs execute in your process, not a sandbox. Only run code you
              trust. Imports are self-reported and excluded from ranked tracks.
            </span>
          </div>
          <Link to="/docs" className="button full" onClick={onClose}>
            Read the SDK guide <ArrowRight size={15} />
          </Link>
        </div>
      )}
    </Modal>
  );
}

export function SearchDialog({ onClose }: { onClose: () => void }) {
  const { agents, tasks } = useWorkspace();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const items = [
    ...[
      { name: "Overview", path: "/" },
      { name: "Leaderboard", path: "/leaderboard" },
      { name: "Experiments — connect OpenRouter", path: "/experiments" },
      { name: "Run history", path: "/runs" },
      { name: "Compare agents", path: "/compare" },
      { name: "Documentation", path: "/docs" },
      { name: "Settings", path: "/settings" },
    ].map((i) => ({ ...i, type: "Page" })),
    ...agents.map((a) => ({
      name: a.name,
      path: `/agents/${a.id}`,
      type: "Agent",
    })),
    ...tasks.map((t) => ({
      name: t.title,
      path: `/tasks/${t.id}`,
      type: t.category,
      keywords: `${t.id} ${t.tags.join(" ")}`,
    })),
  ].filter((i) =>
    `${i.name} ${i.type} ${"keywords" in i ? i.keywords : ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <Modal title="Find your next step." onClose={onClose}>
      <div className="command-search">
        <Search size={20} />
        <input
          autoFocus
          aria-label="Search workspace"
          placeholder="Search tasks, agents, pages…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <kbd>ESC</kbd>
      </div>
      <div className="command-results">
        {items.slice(0, 15).map((i) => (
          <button
            key={i.path}
            onClick={() => {
              navigate(i.path);
              onClose();
            }}
          >
            <span>
              {i.type === "Agent" ? (
                <Code2 size={16} />
              ) : (
                <FlaskConical size={16} />
              )}
            </span>
            <strong>{i.name}</strong>
            <small>{i.type}</small>
            <ArrowRight size={14} />
          </button>
        ))}
        {!items.length && (
          <Empty
            title="Nothing matched"
            description="Try an agent name, task skill, or page title."
          />
        )}
      </div>
      <div className="command-footer">Navigate with Tab · Enter to open</div>
    </Modal>
  );
}
