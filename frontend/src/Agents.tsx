import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bot,
  Check,
  Code2,
  FlaskConical,
  Plus,
  Search,
  Sparkles,
} from "lucide-react";
import { useWorkspace } from "./context";
import { AgentAvatar, Badge, Empty, PageHeading } from "./ui";
import { duration, money, pct } from "./api";
export default function Agents() {
  const { agents, rankings, openAgent, openBenchmark } = useWorkspace();
  const [search, setSearch] = useState("");
  const filtered = agents.filter((a) =>
    `${a.name} ${a.model}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="page">
      <PageHeading
        eyebrow="THE AGENT REGISTRY"
        title="Meet the contenders."
        description="Every agent has a strategy. Find out where yours stands."
        action={
          <button className="button primary" onClick={openAgent}>
            <Plus size={16} /> Register an agent
          </button>
        }
      />
      <div className="filter-bar unboxed">
        <div className="search-field">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Find an agent…"
            aria-label="Search agents"
          />
        </div>
        <span className="small-text muted">
          {agents.length} registered agents
        </span>
      </div>
      <div className="agents-grid">
        {filtered.map((a) => {
          const rank = rankings.find((r) => r.id === a.id);
          return (
            <article className="agent-card" key={a.id}>
              <div className="agent-card-top">
                <AgentAvatar agent={a} size="large" />
                <Badge tone={a.reference ? "" : "green"}>
                  {a.reference ? "Reference policy" : "Model-backed"}
                </Badge>
              </div>
              <Link to={`/agents/${a.id}`}>
                <h2>
                  {a.name} <ArrowUpRight size={17} />
                </h2>
              </Link>
              <span className="agent-version">
                v{a.version} <span>·</span> {a.framework}
              </span>
              <p>
                {a.description || "A custom agent, ready to be benchmarked."}
              </p>
              <div className="agent-model">
                <Code2 size={14} />
                {a.model}
              </div>
              <div className="agent-card-stats">
                <div>
                  <span>Quality</span>
                  <strong>{rank ? pct(rank.quality) : "—"}</strong>
                </div>
                <div>
                  <span>Task success</span>
                  <strong>{rank ? pct(rank.success_rate) : "—"}</strong>
                </div>
                <div>
                  <span>Runs</span>
                  <strong>{rank?.run_count || 0}</strong>
                </div>
              </div>
              <div className="agent-card-actions">
                <Link className="text-link" to={`/agents/${a.id}`}>
                  View profile <ArrowRight size={14} />
                </Link>
                <button
                  className="button small"
                  onClick={() => openBenchmark({ agentId: a.id })}
                >
                  <FlaskConical size={14} /> Benchmark
                </button>
              </div>
            </article>
          );
        })}
        <button className="agent-add-card" onClick={openAgent}>
          <span>
            <Plus size={24} />
          </span>
          <h3>Your agent goes here.</h3>
          <p>Create a managed agent or bring your own Python implementation.</p>
          <strong>
            Join the arena <ArrowRight size={15} />
          </strong>
        </button>
      </div>
      <div className="notice">
        <Bot size={19} />
        <span>
          The four starter agents are deliberately simple Python policies. They
          demonstrate the benchmarking workflow—not the capabilities of real AI
          models.
        </span>
      </div>
    </div>
  );
}
export function AgentDetail() {
  const { id } = useParams();
  const { agents, rankings, tasks, runs, openBenchmark } = useWorkspace();
  const agent = agents.find((a) => a.id === id);
  if (!agent)
    return (
      <div className="page">
        <Empty
          title="Agent not found"
          description="This agent isn’t in the local registry."
          action={
            <Link to="/agents" className="button">
              View agents
            </Link>
          }
        />
      </div>
    );
  const rank = rankings.find((r) => r.id === id);
  const recent = runs.filter((r) => r.agent_id === id);
  return (
    <div className="page">
      <Link className="back-link" to="/agents">
        <ArrowLeft size={15} /> All agents
      </Link>
      <section className="agent-profile-hero">
        <AgentAvatar agent={agent} size="xl" />
        <div>
          <div className="eyebrow">
            {agent.reference ? "REFERENCE AGENT" : "MANAGED MODEL AGENT"}{" "}
            <span> / </span> v{agent.version}
          </div>
          <h1>{agent.name}</h1>
          <p>{agent.description}</p>
          <div className="profile-badges">
            <Badge>{agent.framework}</Badge>
            <Badge>{agent.model}</Badge>
            <Badge>{agent.strategy}</Badge>
          </div>
        </div>
        <button
          className="button primary"
          onClick={() => openBenchmark({ agentId: agent.id })}
        >
          <FlaskConical size={16} /> Run benchmark
        </button>
      </section>
      <div className="profile-stats">
        {[
          ["Output quality", rank ? pct(rank.quality) : "—"],
          ["Task success", rank ? pct(rank.success_rate) : "—"],
          ["Median latency", rank ? duration(rank.latency_ms) : "—"],
          ["Average run cost", rank ? money(rank.cost_usd) : "—"],
          ["Task coverage", `${rank?.task_count || 0} / 12`],
        ].map(([k, v]) => (
          <div key={k}>
            <span>{k}</span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>
      <section className="card">
        <div className="section-head">
          <div>
            <h2>Task-by-task performance</h2>
            <p>
              Latest recorded attempt. Click a task to inspect the evidence.
            </p>
          </div>
          <Badge>Workbench v1</Badge>
        </div>
        <div className="task-performance-grid">
          {tasks.map((t) => {
            const run = recent.find((r) => r.task_id === t.id);
            return (
              <Link
                key={t.id}
                to={run ? `/runs/${run.id}` : `/tasks/${t.id}`}
                className={`performance-tile ${run?.passed ? "success" : run ? "partial" : ""}`}
              >
                <span className="small-text muted">{t.category}</span>
                <h4>{t.title}</h4>
                <div>
                  {run ? (
                    <>
                      <strong>{pct(run.score)}</strong>
                      {run.passed ? (
                        <Check size={16} />
                      ) : (
                        <ArrowUpRight size={16} />
                      )}
                    </>
                  ) : (
                    <>
                      <span>Not run yet</span>
                      <Plus size={14} />
                    </>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      </section>
      <div className="notice">
        <Sparkles size={18} />
        <span>
          {agent.reference
            ? "This agent uses a hand-written policy and no LLM. Zero model cost is expected, and its performance only reflects this public development suite."
            : "This agent calls the server-configured provider. Token pricing, when configured, is an estimate; latency includes network time."}
        </span>
      </div>
    </div>
  );
}
