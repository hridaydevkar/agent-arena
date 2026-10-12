import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  Braces,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Clock3,
  Code2,
  Columns2,
  FileCheck2,
  FileOutput,
  FlaskConical,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Wrench,
  X,
} from "lucide-react";
import { api, download, duration, money, pct } from "./api";
import { useWorkspace } from "./context";
import {
  AgentAvatar,
  Badge,
  Empty,
  JsonBlock,
  Loading,
  PageHeading,
} from "./ui";
import type { Run, TraceEvent } from "./types";
export const eventIcon = (kind: string) =>
  kind === "llm"
    ? Sparkles
    : kind === "tool"
      ? Wrench
      : kind === "output"
        ? FileOutput
        : kind === "check"
          ? ShieldCheck
          : CircleDot;
export default function Replay() {
  const { id } = useParams();
  const { agents, openBenchmark } = useWorkspace();
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [tab, setTab] = useState("Execution trace");
  useEffect(() => {
    let live = true;
    setRun(null);
    setError("");
    setActive(0);
    setPlaying(false);
    api<Run>(`/runs/${id}`)
      .then((r) => {
        if (live) setRun(r);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [id]);
  useEffect(() => {
    if (!playing || !run) return;
    const timer = setInterval(() => {
      setActive((i) => {
        if (i >= run.events.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, 1000 / speed);
    return () => clearInterval(timer);
  }, [playing, run, speed]);
  if (error)
    return (
      <div className="page">
        <Empty
          title="We couldn’t load this run"
          description={error}
          action={
            <Link to="/runs" className="button">
              Back to runs
            </Link>
          }
        />
      </div>
    );
  if (!run) return <Loading text="Loading execution trace…" />;
  const agent = agents.find((a) => a.id === run.agent_id);
  const event = run.events[active];
  const EventIcon = eventIcon(event?.kind || "note");
  return (
    <div className="page replay-page">
      {run.visibility === "summary-only" && (
        <div className="notice amber">
          <ShieldCheck size={18} />
          <span>
            This is a published summary, not a full trace. Raw prompts, outputs
            and per-field checks are withheld. The counts below describe the
            original private execution.
          </span>
        </div>
      )}
      <div className="replay-breadcrumb">
        <Link className="back-link" to="/runs">
          <ArrowLeft size={15} /> Run history
        </Link>
        <ChevronRight size={13} />
        <code>{run.id}</code>
      </div>
      <PageHeading
        eyebrow="THE EVIDENCE ROOM"
        title={run.task_title}
        description={`Recorded ${new Date(run.created_at).toLocaleString()} · Task v${run.task_version}`}
        action={
          <>
            <a href={`/api/runs/${run.id}/export`} className="button" download>
              <ArrowDownToLine size={15} /> Export trace
            </a>
            <button
              className="button primary"
              disabled={!agent}
              onClick={() =>
                openBenchmark({ agentId: run.agent_id, taskId: run.task_id })
              }
            >
              <RotateCcw size={14} /> Run again
            </button>
          </>
        }
      />
      <div className="run-summary-strip">
        <div className="run-agent">
          <AgentAvatar agent={agent || { name: run.agent_name }} />
          <div>
            <strong>{run.agent_name}</strong>
            <small>
              {run.model} · v{run.agent_version}
            </small>
          </div>
        </div>
        <div className="run-summary-metric">
          <span>Outcome</span>
          <Badge
            tone={
              run.passed ? "green" : run.status === "failed" ? "red" : "amber"
            }
          >
            {run.passed ? <Check size={11} /> : <CircleDot size={11} />}{" "}
            {run.passed
              ? "Passed"
              : run.status === "failed"
                ? "Error"
                : "Checks failed"}
          </Badge>
        </div>
        <div className="run-summary-metric">
          <span>Quality</span>
          <strong>{pct(run.score)}</strong>
        </div>
        <div className="run-summary-metric">
          <span>Duration</span>
          <strong>{duration(run.duration_ms)}</strong>
        </div>
        <div className="run-summary-metric">
          <span>Steps</span>
          <strong>{run.steps}</strong>
        </div>
        <div className="run-summary-metric">
          <span>Model cost</span>
          <strong>{money(run.cost_usd)}</strong>
        </div>
      </div>
      {run.provenance === "managed-model" && (
        <div className="model-run-metadata">
          <span>
            Architecture <strong>{run.architecture || "tools"}</strong>
          </span>
          <span>
            Model requests <strong>{run.model_calls ?? "not recorded"}</strong>
          </span>
          <span>
            Tokens{" "}
            <strong>
              {run.input_tokens} in / {run.output_tokens} out
            </strong>
          </span>
          <span>
            Cost source <strong>{run.cost_source || "unknown"}</strong>
          </span>
          {!!run.resolved_models?.length && (
            <span>
              Returned model <strong>{run.resolved_models.join(", ")}</strong>
            </span>
          )}
        </div>
      )}
      {run.error && (
        <div className="notice red">
          <X size={18} />
          <span>{run.error}</span>
        </div>
      )}
      {run.provenance === "self-reported" && (
        <div className="notice amber">
          <ShieldCheck size={18} />
          <span>
            Self-reported SDK execution. Output checks were rerun by the server,
            but traces and timing are not verified. This run is excluded from
            rankings.
          </span>
        </div>
      )}
      <section className="card replay-card">
        <div className="replay-tabs">
          <div className="category-tabs">
            {["Execution trace", "Evaluation", "Final output"].map((t) => (
              <button
                className={tab === t ? "active" : ""}
                key={t}
                onClick={() => setTab(t)}
              >
                {t}
                {t === "Execution trace" && <span>{run.events.length}</span>}
                {t === "Evaluation" && (
                  <span>{run.evaluation.checks.length}</span>
                )}
              </button>
            ))}
          </div>
          {agent && (
            <Link
              to={`/compare?task=${run.task_id}&a=${run.agent_id}`}
              className="text-link"
            >
              <Columns2 size={14} /> Compare run <ArrowRight size={14} />
            </Link>
          )}
        </div>
        {run.visibility === "summary-only" ? (
          <div className="detail-content">
            <h3>
              {tab === "Evaluation"
                ? "Field-level evaluation withheld"
                : tab === "Final output"
                  ? "Final artifact withheld"
                  : "Execution trace withheld"}
            </h3>
            <p>
              This report contains aggregate metrics only. Recorded quality:{" "}
              {pct(run.score)}. Raw prompts, outputs, and individual checks were
              intentionally not published; an empty public artifact is not the
              model's answer.
            </p>
          </div>
        ) : tab === "Execution trace" ? (
          <>
            <div className="player-bar">
              <button
                className="player-play"
                aria-label={playing ? "Pause replay" : "Play replay"}
                disabled={!run.events.length}
                onClick={() => {
                  if (active === run.events.length - 1) setActive(0);
                  setPlaying(!playing);
                }}
              >
                {playing ? (
                  <Pause size={14} fill="currentColor" />
                ) : (
                  <Play size={14} fill="currentColor" />
                )}
              </button>
              <button
                className="icon-button"
                aria-label="Previous step"
                disabled={active === 0}
                onClick={() => {
                  setPlaying(false);
                  setActive(Math.max(0, active - 1));
                }}
              >
                <ChevronLeft size={16} />
              </button>
              <button
                className="icon-button"
                aria-label="Next step"
                disabled={active >= run.events.length - 1}
                onClick={() => {
                  setPlaying(false);
                  setActive(Math.min(run.events.length - 1, active + 1));
                }}
              >
                <ChevronRight size={16} />
              </button>
              <span className="player-step">
                Step <strong>{run.events.length ? active + 1 : 0}</strong> /{" "}
                {run.events.length}
              </span>
              <input
                type="range"
                aria-label="Replay position"
                min={0}
                max={Math.max(0, run.events.length - 1)}
                value={active}
                onChange={(e) => {
                  setPlaying(false);
                  setActive(Number(e.target.value));
                }}
              />
              <span className="player-caption">Step playback</span>
              <select
                aria-label="Replay speed"
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
              >
                <option value={0.5}>0.5×</option>
                <option value={1}>1×</option>
                <option value={2}>2×</option>
              </select>
            </div>
            {!run.events.length ? (
              <Empty
                title="No trace events"
                description="This execution did not record any instrumented steps."
              />
            ) : (
              <div className="trace-workspace">
                <aside className="trace-sidebar">
                  <div className="trace-sidebar-head">
                    EXECUTION TIMELINE<span>{run.events.length} events</span>
                  </div>
                  {run.events.map((e, i) => {
                    const Icon = eventIcon(e.kind);
                    return (
                      <button
                        className={`trace-step ${active === i ? "active" : ""} ${i < active ? "visited" : ""}`}
                        key={i}
                        onClick={() => {
                          setActive(i);
                          setPlaying(false);
                        }}
                      >
                        <span className={`trace-step-icon ${e.kind}`}>
                          <Icon size={15} />
                        </span>
                        <span>
                          <strong>{e.name}</strong>
                          <small>
                            {e.kind === "note"
                              ? "Action summary"
                              : e.kind === "llm"
                                ? "Model call"
                                : e.kind === "check"
                                  ? "Validation"
                                  : e.kind === "output"
                                    ? "Final output"
                                    : "Tool call"}{" "}
                            <span>·</span> {duration(e.duration_ms)}
                          </small>
                        </span>
                        <span className="trace-step-num">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                      </button>
                    );
                  })}
                  <div className="trace-end">
                    <CheckCircle2 size={12} /> Execution {run.status}
                  </div>
                </aside>
                <div className="trace-detail">
                  <div className="trace-detail-head">
                    <div>
                      <span className={`trace-step-icon ${event.kind}`}>
                        <EventIcon size={18} />
                      </span>
                      <div>
                        <div className="eyebrow">
                          STEP {String(active + 1).padStart(2, "0")} /{" "}
                          {event.kind.toUpperCase()}
                        </div>
                        <h3>{event.name}</h3>
                      </div>
                    </div>
                    <Badge tone={event.status === "error" ? "red" : "green"}>
                      {event.status === "error" ? "Error" : "Completed"}
                    </Badge>
                  </div>
                  <div className="event-metadata">
                    <span>
                      <Clock3 size={13} /> {event.duration_ms.toFixed(3)} ms
                    </span>
                    <span>Offset +{event.offset_ms.toFixed(3)} ms</span>
                    <span>
                      <Braces size={13} /> JSON trace
                    </span>
                  </div>
                  <div className="event-payload">
                    <div className="payload-title">
                      <span>
                        <Code2 size={14} /> INPUT
                      </span>
                      <span>Recorded arguments</span>
                    </div>
                    <JsonBlock value={event.input} />
                    <div className="payload-title">
                      <span>
                        <FileOutput size={14} />{" "}
                        {event.kind === "note" ? "ACTION SUMMARY" : "OUTPUT"}
                      </span>
                      <span>Recorded result</span>
                    </div>
                    <JsonBlock value={event.output} />
                  </div>
                </div>
              </div>
            )}
          </>
        ) : tab === "Evaluation" ? (
          <div className="evaluation-content">
            <div className="evaluation-intro">
              <span className="evaluation-icon">
                <FileCheck2 size={28} />
              </span>
              <div>
                <h3>
                  {run.evaluation.checks.filter((c) => c.passed).length} of{" "}
                  {run.evaluation.checks.length} output checks passed
                </h3>
                <p>
                  Equal weight per required field. Numeric tolerance: 0.01.
                  Ordered lists.
                </p>
              </div>
              <strong>{pct(run.score)}</strong>
            </div>
            {run.evaluation.checks.map((c) => (
              <div
                className={`evaluation-check ${c.passed ? "passed" : ""}`}
                key={c.field}
              >
                <div className="check-label">
                  {c.passed ? <CheckCircle2 size={17} /> : <X size={17} />}
                  <code>{c.field}</code>
                  <Badge tone={c.passed ? "green" : "amber"}>
                    {c.passed ? "Pass" : "Mismatch"}
                  </Badge>
                </div>
                <div className="check-values">
                  <div>
                    <span>EXPECTED</span>
                    <JsonBlock value={c.expected} />
                  </div>
                  <div>
                    <span>ACTUAL</span>
                    <JsonBlock value={c.actual} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="detail-content">
            <div className="section-head plain">
              <h3>The final artifact</h3>
              <button
                className="button small"
                onClick={() =>
                  download(
                    JSON.stringify(run.output, null, 2),
                    `${run.id}-output.json`,
                  )
                }
              >
                <ArrowDownToLine size={14} /> Download JSON
              </button>
            </div>
            <p>{run.summary}</p>
            <JsonBlock value={run.output} />
          </div>
        )}
      </section>
      <div className="replay-footer">
        <span>
          <ShieldCheck size={13} /> Observable actions only. No private
          chain-of-thought.
        </span>
        <span>
          Suite fingerprint <code>{run.suite_hash}</code>
        </span>
      </div>
    </div>
  );
}
