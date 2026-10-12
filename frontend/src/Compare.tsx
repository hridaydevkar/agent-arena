import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowUpRight,
  Check,
  Columns2,
  Equal,
  FlaskConical,
  Plus,
  ShieldCheck,
  X,
} from "lucide-react";
import { useWorkspace } from "./context";
import {
  AgentAvatar,
  Badge,
  Empty,
  JsonBlock,
  Loading,
  PageHeading,
} from "./ui";
import { api, download, duration, money, pct } from "./api";
import type { Run } from "./types";
import { eventIcon } from "./Replay";
export default function Compare() {
  const { tasks, agents, runs, openBenchmark } = useWorkspace();
  const [params] = useSearchParams();
  const [task, setTask] = useState(
    params.get("task") ||
      runs.find((r) => r.provenance === "managed-model")?.task_id ||
      "invoice-reconciliation",
  );
  const initialA =
    params.get("a") ||
    agents.find((a) => a.strategy === "model")?.id ||
    agents.find((a) => a.id === "atlas")?.id ||
    agents[0]?.id ||
    "";
  const [a, setA] = useState(initialA);
  const [b, setB] = useState(
    params.get("b") ||
      agents.find((ag) => ag.id !== initialA && ag.strategy === "model")?.id ||
      agents.find((ag) => ag.id !== initialA && ag.id === "meridian")?.id ||
      agents.find((ag) => ag.id !== initialA)?.id ||
      "",
  );
  const [pair, setPair] = useState<(Run | null)[]>([null, null]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("Output checks");
  const ids = [
    runs.find((r) => r.agent_id === a && r.task_id === task)?.id,
    runs.find((r) => r.agent_id === b && r.task_id === task)?.id,
  ];
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError("");
    Promise.all(
      ids.map((id) => (id ? api<Run>(`/runs/${id}`) : Promise.resolve(null))),
    )
      .then((r) => {
        if (live) setPair(r);
      })
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [ids[0], ids[1]]);
  const fields = [
    ...new Set(
      pair.flatMap((r) => r?.evaluation.checks.map((c) => c.field) || []),
    ),
  ];
  return (
    <div className="page">
      {pair.some((r) => r?.visibility === "summary-only") && (
        <div className="notice amber">
          <ShieldCheck size={18} />
          <span>
            Summary-only publication. Scores and timing are visible, but field
            outputs and execution traces were intentionally withheld. Empty
            details do not mean these agents made no model calls.
          </span>
        </div>
      )}
      <PageHeading
        eyebrow="SIDE BY SIDE"
        title="Same challenge. Different choices."
        description="Compare the latest recorded attempts on one shared task."
        action={
          <button
            className="button"
            disabled={!pair[0] || !pair[1]}
            onClick={() =>
              download(
                JSON.stringify({ task_id: task, runs: pair }, null, 2),
                "arena-comparison.json",
              )
            }
          >
            <ArrowDownToLine size={15} /> Export comparison
          </button>
        }
      />
      <section className="card comparison-picker">
        <div>
          <label htmlFor="compare-task">THE SHARED TASK</label>
          <select
            id="compare-task"
            value={task}
            onChange={(e) => setTask(e.target.value)}
          >
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="compare-a">AGENT A</label>
          <select
            id="compare-a"
            value={a}
            onChange={(e) => setA(e.target.value)}
          >
            {agents.map((ag) => (
              <option key={ag.id} value={ag.id} disabled={ag.id === b}>
                {ag.name}
              </option>
            ))}
          </select>
        </div>
        <button
          className="swap-button"
          aria-label="Swap compared agents"
          onClick={() => {
            setA(b);
            setB(a);
          }}
        >
          <ArrowLeftRight size={18} />
        </button>
        <div>
          <label htmlFor="compare-b">AGENT B</label>
          <select
            id="compare-b"
            value={b}
            onChange={(e) => setB(e.target.value)}
          >
            {agents.map((ag) => (
              <option key={ag.id} value={ag.id} disabled={ag.id === a}>
                {ag.name}
              </option>
            ))}
          </select>
        </div>
      </section>
      {error && <div className="notice red">{error}</div>}
      {loading ? (
        <Loading text="Aligning the evidence…" />
      ) : (
        <>
          <div className="compare-agent-grid">
            {[a, b].map((id, i) => {
              const ag = agents.find((a) => a.id === id);
              const r = pair[i];
              return (
                <div className="card compare-agent" key={i}>
                  <div className="compare-agent-header">
                    <span className="compare-letter">
                      {i === 0 ? "A" : "B"}
                    </span>
                    <AgentAvatar agent={ag} size="large" />
                    <div>
                      <h2>{ag?.name || "Select an agent"}</h2>
                      <span>
                        {ag?.model} · {ag?.strategy}
                      </span>
                    </div>
                    {r && (
                      <Link
                        to={`/runs/${r.id}`}
                        className="icon-button"
                        aria-label={`Open ${ag?.name} replay`}
                      >
                        <ArrowUpRight size={18} />
                      </Link>
                    )}
                  </div>
                  {r ? (
                    <>
                      <div className="compare-metrics">
                        <div>
                          <span>Quality</span>
                          <strong className={r.passed ? "text-green" : ""}>
                            {pct(r.score)}
                          </strong>
                        </div>
                        <div>
                          <span>Steps</span>
                          <strong>{r.steps}</strong>
                        </div>
                        <div>
                          <span>Duration</span>
                          <strong>{duration(r.duration_ms)}</strong>
                        </div>
                        <div>
                          <span>Cost</span>
                          <strong>{money(r.cost_usd)}</strong>
                        </div>
                      </div>
                      <div className="compare-result">
                        <Badge tone={r.passed ? "green" : "amber"}>
                          {r.passed
                            ? "All checks passed"
                            : `${r.evaluation.checks.filter((c) => c.passed).length} / ${r.evaluation.checks.length} checks passed`}
                        </Badge>
                        <span className="mono">{r.id.slice(0, 16)}</span>
                      </div>
                    </>
                  ) : (
                    <Empty
                      title="No matching run"
                      description="Run this agent on the selected task first."
                      action={
                        <button
                          className="button small"
                          onClick={() =>
                            openBenchmark({ agentId: id, taskId: task })
                          }
                        >
                          <FlaskConical size={14} /> Run this task
                        </button>
                      }
                    />
                  )}
                </div>
              );
            })}
          </div>
          {pair[0] && pair[1] && (
            <>
              <div className="comparison-insight">
                <span>
                  <Columns2 size={19} />
                </span>
                <div>
                  <strong>
                    {pair[0].score === pair[1].score
                      ? "Equal quality. Look closer at the execution."
                      : `${pair[0].score > pair[1].score ? pair[0].agent_name : pair[1].agent_name} returned more correct output fields.`}
                  </strong>
                  <p>
                    {pair[0].score === pair[1].score
                      ? "The final checks are tied. The traces reveal how each policy got there."
                      : "Mismatched checks are highlighted below. A quality gap is not, by itself, a causal explanation."}
                  </p>
                </div>
                <Badge>
                  {pair[0].suite_hash === pair[1].suite_hash
                    ? "Same suite version"
                    : "Different suite versions"}
                </Badge>
              </div>
              <section className="card">
                <div className="category-tabs">
                  {["Output checks", "Execution traces", "Final outputs"].map(
                    (t) => (
                      <button
                        key={t}
                        onClick={() => setTab(t)}
                        className={tab === t ? "active" : ""}
                      >
                        {t}
                      </button>
                    ),
                  )}
                </div>
                {pair.some((r) => r?.visibility === "summary-only") ? (
                  <div className="detail-content">
                    <h3>Detailed evidence was not published</h3>
                    <p>
                      The metrics above describe the original executions. Raw
                      output fields and model/tool traces are withheld from this
                      summary-only report.
                    </p>
                  </div>
                ) : tab === "Output checks" ? (
                  <div className="diff-table">
                    <div className="diff-header">
                      <span>OUTPUT FIELD</span>
                      <span>{pair[0].agent_name}</span>
                      <span>{pair[1].agent_name}</span>
                    </div>
                    {fields.map((field) => {
                      const checks = pair.map((r) =>
                        r?.evaluation.checks.find((c) => c.field === field),
                      );
                      const different =
                        JSON.stringify(checks[0]?.actual) !==
                        JSON.stringify(checks[1]?.actual);
                      return (
                        <div
                          className={`diff-row ${different ? "different" : ""}`}
                          key={field}
                        >
                          <div>
                            <code>{field}</code>
                            {different && <small>Outputs diverge</small>}
                          </div>
                          {checks.map((c, i) => (
                            <div key={i}>
                              <span
                                className={
                                  c?.passed ? "text-green" : "text-amber"
                                }
                              >
                                {c?.passed ? (
                                  <Check size={14} />
                                ) : (
                                  <X size={14} />
                                )}
                              </span>
                              <pre>
                                {JSON.stringify(c?.actual ?? null, null, 2)}
                              </pre>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                ) : tab === "Execution traces" ? (
                  <div className="compare-traces">
                    {pair.map((r, i) => (
                      <div key={i}>
                        <div className="compare-trace-title">
                          {r?.agent_name}
                          <span>{r?.events.length} steps</span>
                        </div>
                        {r?.events.map((e, index) => {
                          const Icon = eventIcon(e.kind);
                          return (
                            <details className="compare-event" key={index}>
                              <summary>
                                <span className={`trace-step-icon ${e.kind}`}>
                                  <Icon size={14} />
                                </span>
                                <span>
                                  {e.name}
                                  <small>{duration(e.duration_ms)}</small>
                                </span>
                                <Plus size={13} />
                              </summary>
                              <div>
                                <JsonBlock
                                  value={{ input: e.input, output: e.output }}
                                />
                              </div>
                            </details>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="compare-outputs">
                    {pair.map((r, i) => (
                      <div key={i}>
                        <h3>{r?.agent_name}</h3>
                        <JsonBlock value={r?.output} />
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
          <div className="notice">
            <ShieldCheck size={18} />
            <span>
              Comparisons use each agent’s latest run for this task. Traces are
              observational; this view does not infer private reasoning or prove
              why an agent failed.
              {pair[0] && pair[1] && pair[0].provenance !== pair[1].provenance
                ? " These runs are from different trust tracks; compare with caution."
                : ""}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
