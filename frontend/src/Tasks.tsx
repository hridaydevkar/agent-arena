import { useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  FileCode2,
  FlaskConical,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useWorkspace } from "./context";
import { Badge, CategoryIcon, Empty, JsonBlock, PageHeading } from "./ui";
import { categories } from "./Leaderboard";
import { ago, pct } from "./api";
export default function Tasks() {
  const { tasks } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const category = params.get("category") || "All";
  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState("All");
  const filtered = tasks.filter(
    (t) =>
      (category === "All" || t.category === category) &&
      (difficulty === "All" || t.difficulty === difficulty) &&
      `${t.title} ${t.tags.join(" ")}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <div className="page">
      <PageHeading
        eyebrow="THE TASK LIBRARY"
        title="Real work. Repeatable challenges."
        description="Small, inspectable tasks that expose big differences in agent behavior."
        action={
          <Badge tone="green">
            <ShieldCheck size={13} /> 12 version-pinned tasks
          </Badge>
        }
      />
      <div className="task-library-intro">
        <span>
          <FlaskConical size={20} />
        </span>
        <div>
          <strong>A test suite you can actually understand.</strong>
          <p>
            Synthetic fixtures. Explicit rubrics. No live bookings, external
            side effects, or moving targets.
          </p>
        </div>
        <Link to="/docs" className="text-link">
          Create a task <ArrowUpRight size={15} />
        </Link>
      </div>
      <div className="category-tabs standalone">
        {categories.map((c) => (
          <button
            key={c}
            className={category === c ? "active" : ""}
            onClick={() => setParams(c === "All" ? {} : { category: c })}
          >
            {c === "All" ? "All tasks" : c}
            <span>
              {c === "All"
                ? tasks.length
                : tasks.filter((t) => t.category === c).length}
            </span>
          </button>
        ))}
      </div>
      <div className="filter-bar unboxed">
        <div className="search-field">
          <Search size={16} />
          <input
            placeholder="Search tasks, skills, or tools…"
            aria-label="Search tasks"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-right">
          <span className="small-text muted">{filtered.length} tasks</span>
          <select
            aria-label="Task difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="All">All difficulty levels</option>
            {["Easy", "Medium", "Hard"].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="tasks-grid">
        {filtered.map((t, i) => (
          <Link className="task-card" to={`/tasks/${t.id}`} key={t.id}>
            <div className="task-card-top">
              <span
                className={`task-icon ${t.category.toLowerCase().replace(" ", "-")}`}
              >
                <CategoryIcon name={t.category} size={22} />
              </span>
              <Badge tone={t.difficulty.toLowerCase()}>
                <span className="difficulty-dot" />
                {t.difficulty}
              </Badge>
            </div>
            <div className="task-category">
              {t.category} <span> / </span>{" "}
              {t.id.split("-").slice(0, 2).join("-")}
            </div>
            <h3>{t.title}</h3>
            <p>{t.description.split(". ")[0]}.</p>
            <div className="task-tags">
              {t.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
            <div className="task-card-bottom">
              <span>
                <CheckCircle2 size={13} /> {Object.keys(t.output_schema).length}{" "}
                objective checks
              </span>
              <ArrowUpRight size={17} />
            </div>
          </Link>
        ))}
      </div>
      {!filtered.length && (
        <Empty
          title="No tasks match"
          description="Try a different search or clear your filters."
          action={
            <button
              className="button"
              onClick={() => {
                setSearch("");
                setDifficulty("All");
                setParams({});
              }}
            >
              Clear filters
            </button>
          }
        />
      )}
      <div className="contribution-banner">
        <div>
          <span className="eyebrow">MAKE THE BENCHMARK BETTER</span>
          <h3>The next great task might be yours.</h3>
          <p>Contribute a fixture, define a rubric, and help raise the bar.</p>
        </div>
        <Link className="button" to="/docs">
          <FileCode2 size={16} /> Task creation guide <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
export function TaskDetail() {
  const { id } = useParams();
  const { tasks, runs, openBenchmark } = useWorkspace();
  const task = tasks.find((t) => t.id === id);
  const [tab, setTab] = useState("Overview");
  if (!task)
    return (
      <div className="page">
        <Empty
          title="Task not found"
          description="Choose a task from the library."
          action={
            <Link to="/tasks" className="button">
              Browse tasks
            </Link>
          }
        />
      </div>
    );
  const related = runs.filter((r) => r.task_id === task.id);
  return (
    <div className="page">
      <Link className="back-link" to="/tasks">
        <ArrowLeft size={15} /> Task library
      </Link>
      <PageHeading
        eyebrow={`${task.category.toUpperCase()} / ${task.id.toUpperCase()}`}
        title={task.title}
        description="A controlled challenge. A transparent score."
        action={
          <button
            className="button primary"
            onClick={() => openBenchmark({ taskId: task.id })}
          >
            <FlaskConical size={16} /> Run this task
          </button>
        }
      />
      <div className="detail-layout">
        <section className="card">
          <div className="category-tabs">
            {["Overview", "Fixtures", "Output schema"].map((t) => (
              <button
                className={tab === t ? "active" : ""}
                onClick={() => setTab(t)}
                key={t}
              >
                {t}
              </button>
            ))}
          </div>
          <div className="detail-content">
            {tab === "Overview" ? (
              <>
                <h3>The assignment</h3>
                <p className="task-description">{task.description}</p>
                <h3>How it’s evaluated</h3>
                <p>{task.rubric}</p>
                <div className="notice green">
                  <ShieldCheck size={18} />
                  <span>
                    The evaluator runs outside the agent and checks final
                    output. No model judge or subjective scoring is used.
                  </span>
                </div>
                <h3>Required output fields</h3>
                <div className="schema-list">
                  {Object.entries(task.output_schema).map(([key, type]) => (
                    <div key={key}>
                      <code>{key}</code>
                      <Badge>{type}</Badge>
                    </div>
                  ))}
                </div>
              </>
            ) : tab === "Fixtures" ? (
              <>
                <h3>Everything the agent can see</h3>
                <p>
                  These read-only fixtures are available through{" "}
                  <code>tools.read_file(name)</code>.
                </p>
                {Object.entries(task.inputs).map(([name, input]) => (
                  <div className="fixture-block" key={name}>
                    <h4>
                      <FileCode2 size={15} />
                      {name}
                    </h4>
                    <JsonBlock value={input} />
                  </div>
                ))}
              </>
            ) : (
              <>
                <h3>Return a JSON object</h3>
                <p>
                  Only the fields below are scored. Extra fields are ignored;
                  list order matters.
                </p>
                <JsonBlock value={task.output_schema} />
              </>
            )}
          </div>
        </section>
        <aside>
          <div className="card task-spec">
            <h3>Task specification</h3>
            {[
              ["Suite", "Workbench v1"],
              ["Task version", task.version],
              ["Difficulty", task.difficulty],
              ["Evaluation", "Deterministic"],
              ["Output checks", String(Object.keys(task.output_schema).length)],
              ["Recorded runs", String(related.length)],
            ].map(([k, v]) => (
              <div key={k}>
                <span>{k}</span>
                <strong>{v}</strong>
              </div>
            ))}
            <h4>Allowed tools</h4>
            {task.tools.map((t) => (
              <code className="tool-chip" key={t}>
                {t}
              </code>
            ))}
            <h4>Skills tested</h4>
            <div className="task-tags">
              {task.tags.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
          </div>
          <div className="card related-runs">
            <h3>Recent attempts</h3>
            {related.slice(0, 5).map((r) => (
              <Link to={`/runs/${r.id}`} key={r.id}>
                <div>
                  <strong>{r.agent_name}</strong>
                  <small>{ago(r.created_at)}</small>
                </div>
                <Badge tone={r.passed ? "green" : "amber"}>
                  {pct(r.score)}
                </Badge>
                <ChevronRight size={14} />
              </Link>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
