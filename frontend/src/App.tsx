import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  CircleHelp,
  Code2,
  Columns2,
  FlaskConical,
  FolderKanban,
  History,
  LayoutDashboard,
  Loader2,
  Menu,
  Plus,
  Radio,
  Search,
  Settings2,
  ShieldCheck,
  Terminal,
  Trophy,
  Users2,
  X,
} from "lucide-react";
import { api } from "./api";
import type { Agent, Health, Job, Overview, Ranking, Run, Task } from "./types";
import type { BenchPreset } from "./context";
import { WorkspaceContext } from "./context";
import { Empty, Loading, Mark, Modal } from "./ui";
import OverviewPage from "./Overview";
import Leaderboard from "./Leaderboard";
import Tasks, { TaskDetail } from "./Tasks";
import Agents, { AgentDetail } from "./Agents";
import Runs from "./Runs";
import Replay from "./Replay";
import Compare from "./Compare";
import Docs, { ScoringContent } from "./Docs";
import Settings from "./Settings";
import Experiments from "./Experiments";
import { AgentDialog, BenchmarkDialog, SearchDialog } from "./Dialogs";

type Data = {
  agents: Agent[];
  tasks: Task[];
  rankings: Ranking[];
  overview: Overview;
  runs: Run[];
  jobs: Job[];
  health: Health;
};
const navigation = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/experiments", label: "Experiments", icon: FlaskConical },
  { to: "/tasks", label: "Task library", icon: FlaskConical },
  { to: "/runs", label: "Run history", icon: History },
  { to: "/compare", label: "Compare", icon: Columns2 },
  { to: "/agents", label: "Agent registry", icon: Users2 },
];
export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [benchmark, setBenchmark] = useState<BenchPreset | null>(null);
  const [agentDialog, setAgentDialog] = useState(false);
  const [searchDialog, setSearchDialog] = useState(false);
  const [methods, setMethods] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [notification, setNotification] = useState<{
    message: string;
    error: boolean;
  } | null>(null);
  const location = useLocation();
  const refresh = useCallback(async () => {
    const [agents, tasks, rankings, overview, runs, jobs, health] =
      await Promise.all([
        api<Agent[]>("/agents"),
        api<Task[]>("/tasks"),
        api<Ranking[]>("/leaderboard"),
        api<Overview>("/overview"),
        api<{ items: Run[] }>("/runs?limit=1000"),
        api<Job[]>("/jobs"),
        api<Health>("/health"),
      ]);
    setData({
      agents,
      tasks,
      rankings,
      overview,
      runs: runs.items,
      jobs,
      health,
    });
    setError("");
  }, []);
  const toast = useCallback(
    (message: string, error = false) => setNotification({ message, error }),
    [],
  );
  const openBenchmark = useCallback(
    (preset: BenchPreset = {}) => {
      if (data?.health.read_only) {
        toast(
          "This is a read-only results site. Run the workbench locally with your own key; see Documentation.",
        );
        return;
      }
      setBenchmark(preset);
    },
    [data?.health.read_only, toast],
  );
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    const interval = setInterval(() => {
      if (document.visibilityState === "visible")
        refresh().catch((e) => setError(e.message));
    }, 6000);
    return () => clearInterval(interval);
  }, [refresh]);
  useEffect(() => {
    if (!notification) return;
    const timeout = setTimeout(() => setNotification(null), 5500);
    return () => clearTimeout(timeout);
  }, [notification]);
  useEffect(() => {
    setMobile(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchDialog((v) => !v);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const activePage =
    location.pathname === "/"
      ? "Overview"
      : [
          ...navigation,
          { to: "/docs", label: "Documentation" },
          { to: "/settings", label: "Settings" },
        ].find((n) => n.to !== "/" && location.pathname.startsWith(n.to))
          ?.label || "Workspace";
  const layout = (
    <>
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <Link to="/" className="brand">
          <Mark />
          <span>
            agent<span>arena</span>
            <small>THE OPEN WORKBENCH</small>
          </span>
        </Link>
        <Link className="workspace-switch" to="/settings">
          <span className="workspace-symbol">A</span>
          <span>
            <strong>
              {data?.health.read_only ? "Public results" : "Local workspace"}
            </strong>
            <small>
              {data?.health.read_only
                ? "Published measurements"
                : "Personal environment"}
            </small>
          </span>
          <ChevronsUpDown size={14} />
        </Link>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {navigation.map((n) => (
            <NavLink
              to={n.to}
              end={n.to === "/"}
              key={n.to}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              <n.icon size={18} strokeWidth={1.7} />
              <span>{n.label}</span>
              {n.to === "/tasks" ? (
                <span className="nav-count">12</span>
              ) : n.to === "/runs" && !!data?.overview.active_jobs ? (
                <span className="nav-count live">
                  {data.overview.active_jobs}
                </span>
              ) : null}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-callout">
            <span className="callout-mark">✳</span>
            <h4>Built something good?</h4>
            <p>
              Let the benchmark do
              <br />
              the talking.
            </p>
            <button
              onClick={() =>
                data?.health.read_only
                  ? toast(
                      "Agent registration is disabled on this public results site. Run the project locally.",
                    )
                  : setAgentDialog(true)
              }
            >
              Bring your agent <Plus size={14} />
            </button>
          </div>
          <NavLink to="/docs" className="nav-link">
            <BookOpen size={17} />
            <span>Documentation</span>
            <ArrowUpRight size={14} />
          </NavLink>
          <NavLink to="/settings" className="nav-link">
            <Settings2 size={17} />
            <span>Settings</span>
          </NavLink>
          <div className="sidebar-status">
            <span className={`status-dot ${error ? "offline" : ""}`} />
            <span>
              {error
                ? "Backend disconnected"
                : data?.health.read_only
                  ? "Read-only publication"
                  : "All systems local"}
            </span>
            <code>v0.2</code>
          </div>
          <Link className="workspace-user" to="/settings">
            <span className="user-avatar">Y</span>
            <span>
              <strong>Your workspace</strong>
              <small>Open-source edition</small>
            </span>
            <ChevronsUpDown size={14} />
          </Link>
        </div>
      </aside>
      {mobile && (
        <button
          className="sidebar-overlay"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb-root">
              <FolderKanban size={15} /> Workspace
            </span>
            <ChevronRight size={13} />
            <span>{activePage}</span>
          </div>
          <div className="topbar-right">
            <button
              className="global-search"
              onClick={() => setSearchDialog(true)}
            >
              <Search size={15} />
              <span>Find anything…</span>
              <kbd>⌘ K</kbd>
            </button>
            <div className="topbar-divider" />
            <Link
              className="icon-button help-button"
              title="Documentation"
              to="/docs"
            >
              <CircleHelp size={18} />
            </Link>
            <button
              className="button primary small"
              onClick={() => openBenchmark()}
            >
              <Plus size={16} />
              <span>Run benchmark</span>
            </button>
          </div>
        </header>
        {error && data && (
          <div className="connection-banner">
            Connection interrupted. Showing the last loaded data.{" "}
            <button
              onClick={() => refresh().catch((e) => toast(e.message, true))}
            >
              Retry
            </button>
          </div>
        )}
        {data?.health.read_only && (
          <div className="public-mode-banner">
            <ShieldCheck size={15} />
            <span>
              <strong>Public results · read only.</strong>{" "}
              {data.health.has_model_results
                ? "Maintainer-published model measurements, not independently attested."
                : "Reference-policy demo only. No real model results have been published yet."}{" "}
              No provider key or execution endpoint is available.
            </span>
            <Link to="/docs">
              Run locally <ArrowUpRight size={14} />
            </Link>
          </div>
        )}
        <main>
          {!data ? (
            error ? (
              <div className="page">
                <Empty
                  title="Let’s connect your workbench."
                  description={`${error}. Start the backend on port 8000, then try again.`}
                  action={
                    <button
                      className="button primary"
                      onClick={() => {
                        setError("");
                        refresh().catch((e) => setError(e.message));
                      }}
                    >
                      Retry connection
                    </button>
                  }
                />
              </div>
            ) : (
              <Loading text="Preparing your local workbench…" />
            )
          ) : (
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/tasks/:id" element={<TaskDetail />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/agents/:id" element={<AgentDetail />} />
              <Route path="/runs" element={<Runs />} />
              <Route path="/runs/:id" element={<Replay />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/docs" element={<Docs />} />
              <Route path="/settings" element={<Settings />} />
              <Route
                path="*"
                element={
                  <div className="page">
                    <Empty
                      title="Outside the arena."
                      description="That page doesn’t exist. Let’s get you back to the workbench."
                      action={
                        <Link className="button primary" to="/">
                          Back to overview
                        </Link>
                      }
                    />
                  </div>
                }
              />
            </Routes>
          )}
        </main>
      </div>
    </>
  );
  return data ? (
    <WorkspaceContext.Provider
      value={{
        ...data,
        refresh,
        toast,
        openBenchmark,
        openAgent: () =>
          data.health.read_only
            ? toast(
                "Registration is disabled here. Run the project locally with your own key.",
              )
            : setAgentDialog(true),
        openMethods: () => setMethods(true),
      }}
    >
      {layout}
      {benchmark && (
        <BenchmarkDialog
          preset={benchmark}
          onClose={() => setBenchmark(null)}
        />
      )}{" "}
      {agentDialog && <AgentDialog onClose={() => setAgentDialog(false)} />}{" "}
      {searchDialog && <SearchDialog onClose={() => setSearchDialog(false)} />}{" "}
      {methods && (
        <Modal
          title="How we measure."
          subtitle="Transparent metrics. Clear boundaries."
          onClose={() => setMethods(false)}
          wide
        >
          <div className="modal-body docs-article methods-content">
            <ScoringContent />
          </div>
        </Modal>
      )}
      {notification && (
        <div
          role="status"
          className={`toast ${notification.error ? "error" : ""}`}
        >
          <span>
            {notification.error ? <X size={15} /> : <Check size={15} />}
          </span>
          <p>{notification.message}</p>
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotification(null)}
          >
            <X size={14} />
          </button>
        </div>
      )}
    </WorkspaceContext.Provider>
  ) : (
    layout
  );
}
