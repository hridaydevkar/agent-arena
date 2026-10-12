import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  BookOpen,
  Check,
  Code2,
  Copy,
  ExternalLink,
  FileText,
  Layers3,
  Terminal,
} from "lucide-react";
import { useWorkspace } from "./context";
import { Badge, PageHeading } from "./ui";
export function CodeBlock({
  code,
  language = "bash",
}: {
  code: string;
  language?: string;
}) {
  const { toast } = useWorkspace();
  const [copied, setCopied] = useState(false);
  return (
    <div className="docs-code">
      <div>
        <span>{language}</span>
        <button
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(code);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {
              toast(
                "Clipboard unavailable. Select and copy the command manually.",
                true,
              );
            }
          }}
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}{" "}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>{code}</pre>
    </div>
  );
}
const sdkCode = `from agent_arena import Agent, AgentResult, Task, ToolContext

class MyAgent(Agent):
    def run(self, task: Task, tools: ToolContext) -> AgentResult:
        # Run on the "revenue-by-region" task.
        orders = tools.read_file("orders")  # Automatically traced
        totals = {}
        for row in orders:
            if row["status"] == "cancelled":
                continue
            region = row["region"]
            totals[region] = totals.get(region, 0) + row["amount"] - row["refund"]
        best = sorted(totals, key=lambda r: (-totals[r], r))[0]
        return AgentResult(output={
            "total_net_revenue": sum(totals.values()),
            "top_region": best,
            "top_region_revenue": totals[best],
        })`;
export default function Docs() {
  const [tab, setTab] = useState("Quick start");
  return (
    <div className="page">
      <PageHeading
        eyebrow="THE FIELD GUIDE"
        title="Less setup. More discovery."
        description="Everything you need to run the arena, bring an agent, and trust the results."
        action={
          <a
            className="button"
            href="/api/docs"
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={15} /> Interactive API
          </a>
        }
      />
      <div className="docs-layout">
        <aside className="docs-nav">
          {[
            "Quick start",
            "Bring your agent",
            "Create a task",
            "Scoring & trust",
            "Architecture",
            "Deployment",
          ].map((t, i) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              <span>0{i + 1}</span>
              {t}
            </button>
          ))}
          <div>
            <BookOpen size={20} />
            <strong>Built in the open.</strong>
            <p>MIT licensed. Your workspace, your data, your benchmarks.</p>
            <Badge>v0.2.0</Badge>
          </div>
        </aside>
        <article className="card docs-article">
          {tab === "Quick start" ? (
            <>
              <Badge tone="green">START HERE</Badge>
              <h2>Your first benchmark in a few minutes.</h2>
              <p>
                The default workspace needs no API key, no database server, and
                no paid services. Starter data is produced by executing real
                reference policies on first launch.
              </p>
              <div className="notice green">
                <Terminal size={19} />
                <span>
                  <strong>Have an OpenRouter key?</strong> Open Settings →
                  OpenRouter setup. Run{" "}
                  <code>.venv/bin/python scripts/setup_openrouter.py</code> in
                  your own terminal, then restart with{" "}
                  <code>python3 scripts/start.py --port 8002</code>. Open
                  Experiments to compare three real architectures on one task.
                </span>
              </div>
              <h3>01 / Start the complete stack</h3>
              <p>
                The release ZIP includes the compiled frontend. With Python
                3.11+, run python3 scripts/start.py --port 8002 on macOS/Linux
                (py scripts/start.py --port 8002 on Windows). Docker below is
                optional.
              </p>
              <CodeBlock code="docker compose up --build" />
              <p>
                Docker opens at http://localhost:8000. The launcher command
                above opens at http://localhost:8002. Node is needed only when
                rebuilding frontend source; the release ZIP already contains the
                compiled UI.
              </p>
              <h3>02 / Put an agent to work</h3>
              <p>
                Click <strong>Run benchmark</strong>. Select Atlas for a careful
                policy, Meridian for a quicker baseline, or choose multiple
                agents to compare. Start with a single task or run all 12.
              </p>
              <h3>03 / Follow the evidence</h3>
              <p>
                Open a completed run to replay tool calls, inspect fixture
                inputs, and check each expected output. Use Compare to see where
                two agents diverge.
              </p>
              <div className="notice green">
                <Check size={18} />
                <span>
                  You’re already in a working local workspace. Start a run now,
                  or use the SDK to try your own implementation.
                </span>
              </div>
            </>
          ) : tab === "Bring your agent" ? (
            <>
              <Badge>PYTHON SDK</Badge>
              <h2>Your agent. Your implementation.</h2>
              <p>
                Save the example below as <code>my_agent.py</code>. Custom
                Python agents run on your own computer; the web API never
                executes uploaded code.
              </p>
              <CodeBlock code={sdkCode} language="python" />
              <CodeBlock
                code={
                  "# From the project root, in your activated Python environment\npip install -e .\narena tasks\narena run my_agent.py --task revenue-by-region --submit"
                }
              />
              <p>
                The CLI stores a local JSON trace and optionally imports it into
                the UI. Imported runs are <strong>self-reported</strong>: the
                server recomputes output checks but cannot attest to your trace,
                runtime, or environment.
              </p>
              <h3>Use a real model</h3>
              <p>
                Configure <code>OPENAI_API_KEY</code>,{" "}
                <code>OPENAI_BASE_URL</code>, and <code>OPENAI_MODEL</code> on
                the backend. Restart it, then register a model-backed agent.
                Provider keys never go to the browser.
              </p>
              <p>
                Only SDK tool calls are automatically traced. Calls made outside
                the SDK are not observed. Arbitrary external endpoints and
                container submissions are not accepted by this local version.
              </p>
            </>
          ) : tab === "Create a task" ? (
            <>
              <Badge>CONTRIBUTOR GUIDE</Badge>
              <h2>A good task is a falsifiable claim.</h2>
              <p>
                Add an entry in <code>scripts/create_tasks.py</code>, regenerate
                the library, and implement the matching reference operation in{" "}
                <code>backend/arena_server/agents.py</code>.
              </p>
              <ol>
                <li>
                  <strong>Use fixed inputs.</strong> Include small synthetic
                  fixtures, not live websites or real personal data.
                </li>
                <li>
                  <strong>Make success explicit.</strong> Specify required
                  output fields, ordering rules, and tie breakers.
                </li>
                <li>
                  <strong>Include edge cases.</strong> Duplicates, missing
                  constraints, conflicting sources, and units expose useful
                  differences.
                </li>
                <li>
                  <strong>Version your change.</strong> Any fixture change
                  alters the suite fingerprint. Incompatible runs are excluded
                  from current rankings.
                </li>
                <li>
                  <strong>Test the evaluator.</strong> Include a known-good
                  result and at least one known-bad result.
                </li>
              </ol>
              <CodeBlock code={"python scripts/create_tasks.py\npytest -q"} />
              <p>
                Task definitions are package data at{" "}
                <code>backend/arena_server/task_library.json</code>. Restart the
                backend after making changes. See{" "}
                <code>docs/TASK_CREATION_GUIDE.md</code> for details.
              </p>
            </>
          ) : tab === "Scoring & trust" ? (
            <ScoringContent />
          ) : tab === "Architecture" ? (
            <>
              <Badge>SYSTEM DESIGN</Badge>
              <h2>A small system. An inspectable path.</h2>
              <p>
                This edition chooses reliable local operation over distributed
                infrastructure you don’t need yet.
              </p>
              <div className="architecture-flow">
                {[
                  "React + TypeScript UI",
                  "FastAPI · validated same-origin API",
                  "Bounded background execution queue",
                  "Instrumented SDK + read-only fixture tools",
                  "Independent field evaluator",
                  "SQLite WAL · persisted runs + traces",
                ].map((t, i) => (
                  <div key={t}>
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    {t}
                  </div>
                ))}
              </div>
              <p>
                The UI polls the API for completion. Jobs survive as records; a
                server restart marks unfinished jobs interrupted instead of
                silently claiming they resumed.
              </p>
              <h3>What’s deliberately not here</h3>
              <p>
                There is no public multi-tenant service, arbitrary-code sandbox,
                live web browsing, human voting system, or subjective model
                judge. Docker packages the trusted app; it does not isolate
                hostile submitted agents.
              </p>
            </>
          ) : (
            <>
              <Badge>OPERATIONS</Badge>
              <h2>Local first. Public later.</h2>
              <p>
                Docker Compose binds port 8000 to your computer’s loopback
                interface. SQLite data lives in a named volume and persists
                across restarts.
              </p>
              <CodeBlock
                code={
                  "docker compose up --build -d\ndocker compose logs -f\n# Stop without deleting your data\ndocker compose down"
                }
              />
              <h3>Optional provider configuration</h3>
              <p>
                Copy <code>.env.example</code> to <code>.env</code>, add
                provider settings, and recreate the container. The v0.2 launcher
                loads .env automatically; local file values override older shell
                exports. Raw uvicorn startup still requires --env-file .env or
                exported variables.
              </p>
              <h3>Publish results, not your provider key</h3>
              <p>
                v0.2 includes a read-only public mode and a Render deployment
                blueprint. Run an experiment locally, export its public
                report to public-data/results.json, then publish source on
                GitHub. See docs/PUBLISH.md. ARENA_READ_ONLY=1 blocks writes and
                inference; the server refuses to start if OPENAI_API_KEY is
                present.
              </p>
              <h3>Before you expose the execution service publicly</h3>
              <p>
                This is not a hardened multi-tenant platform. Add TLS, user
                authentication, ownership checks, redaction and retention
                policies, per-user quotas, a durable queue, and proper isolated
                workers before accepting untrusted users.
              </p>
              <div className="notice amber">
                <ShieldNotice />
                <span>
                  An API token protects writes only. Read endpoints remain open.
                  Never put sensitive traces on a publicly reachable instance of
                  this edition.
                </span>
              </div>
              <h3>Backups</h3>
              <p>
                Stop the server and copy the SQLite data directory, or use
                SQLite’s backup API. Do not copy a live WAL database file alone.
                Exported run JSON is useful for analysis, but is not a full
                database backup.
              </p>
            </>
          )}
        </article>
      </div>
    </div>
  );
}
function ShieldNotice() {
  return <Layers3 size={18} />;
}
export function ScoringContent() {
  return (
    <>
      <Badge tone="green">TRANSPARENT BY DESIGN</Badge>
      <h2>Understand the score before trusting it.</h2>
      <h3>Quality vs. task success</h3>
      <p>
        Every task defines expected top-level output fields. Quality is the
        fraction of fields that match. Task success requires all fields to
        match. Floats use an absolute tolerance of 0.01 (and relative tolerance
        1e-6), lists are ordered, and extra fields are ignored.
      </p>
      <h3>Comparable coverage</h3>
      <p>
        The main leaderboard first prioritizes suite coverage, then mean quality
        and task success. It uses the latest run per agent and task on the
        current suite fingerprint, including execution errors as zero quality.
        It does not select each agent’s best attempt.
      </p>
      <h3>Three trust tracks</h3>
      <ul>
        <li>
          <strong>Reference:</strong> controlled, hand-written Python policies;
          no LLM calls.
        </li>
        <li>
          <strong>Managed model:</strong> executed by the server with the
          configured model and bounded tool loop.
        </li>
        <li>
          <strong>Self-reported:</strong> imported SDK traces. Server-checked
          outputs, unverified execution; excluded from rankings.
        </li>
      </ul>
      <h3>The Elo number</h3>
      <p>
        Each agent starts at 1,000. For every shared task, latest runs within
        the same trust track are paired. Higher field quality wins; equal
        quality ties. Ratings are rebuilt with K=24 in sorted task-ID / agent-ID
        order. A pair is counted only once per task, so rerunning a task does
        not farm matches.
      </p>
      <p>
        This is a descriptive rating. It is order-sensitive and has no
        confidence interval. With 12 public development tasks, don’t treat small
        rating gaps as meaningful or generalize to production.
      </p>
      <h3>Timing, costs, and trace boundaries</h3>
      <p>
        Durations are measured wall-clock times, not replay playback timing.
        Reference runs are often below one millisecond. Model cost is unknown
        unless token usage and both per-million-token prices are supplied. SDK
        tools capture observable inputs and outputs, not private
        chain-of-thought.
      </p>
      <h3>Known limitations</h3>
      <p>
        These public fixtures are intentionally inspectable and easy to overfit.
        A production benchmark would need held-out tasks, repeated seeds,
        budget-normalized tracks, contamination controls, independent audits,
        and uncertainty estimates.
      </p>
    </>
  );
}
