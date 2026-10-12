import {
  isStaticDemo,
  getStaticData,
  getStaticRun,
  getStaticLeaderboard,
  getStaticJob,
  getStaticTask,
  getStaticAgent,
  getStaticRuns,
} from "./staticDemoData";

let staticFallbackActive = isStaticDemo();

export function setStaticFallback(active: boolean) {
  staticFallbackActive = active;
}

export function handleStaticApi<T>(path: string, options: RequestInit = {}): T {
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    throw new Error(
      "This is a static read-only showcase on GitHub Pages. To run live model experiments or execute benchmarks with your own API key, download AgentArena and launch locally.",
    );
  }

  const [cleanPath, queryString] = path.split("?");
  const params = new URLSearchParams(queryString || "");

  if (cleanPath === "/health") {
    return getStaticData().health as T;
  }
  if (cleanPath === "/overview") {
    return getStaticData().overview as T;
  }
  if (cleanPath === "/agents") {
    return getStaticData().agents as T;
  }
  if (cleanPath.startsWith("/agents/")) {
    const id = cleanPath.slice("/agents/".length);
    const agent = getStaticAgent(id);
    if (!agent) throw new Error("Agent not found");
    return agent as T;
  }
  if (cleanPath === "/tasks") {
    return getStaticData().tasks as T;
  }
  if (cleanPath.startsWith("/tasks/")) {
    const id = cleanPath.slice("/tasks/".length);
    const task = getStaticTask(id);
    if (!task) throw new Error("Task not found");
    return task as T;
  }
  if (cleanPath === "/leaderboard") {
    const cat = params.get("category") || undefined;
    return getStaticLeaderboard(cat) as T;
  }
  if (cleanPath === "/runs") {
    return getStaticRuns(params) as T;
  }
  if (cleanPath.startsWith("/runs/")) {
    const id = cleanPath.slice("/runs/".length);
    const run = getStaticRun(id);
    if (!run) throw new Error("Run not found");
    return run as T;
  }
  if (cleanPath === "/jobs") {
    return getStaticData().jobs as T;
  }
  if (cleanPath.startsWith("/jobs/") && cleanPath.endsWith("/report")) {
    return {
      format: "agent-arena-public-v1",
      generated_at: new Date().toISOString(),
      notice: "Static demo export.",
      agents: getStaticData().agents,
      runs: getStaticData().runs,
    } as T;
  }
  if (cleanPath.startsWith("/jobs/")) {
    const id = cleanPath.slice("/jobs/".length);
    const job = getStaticJob(id);
    if (!job) throw new Error("Job not found");
    return job as T;
  }
  if (cleanPath === "/models") {
    return { items: [] } as T;
  }
  if (cleanPath === "/provider/check") {
    return { ok: true, status: "Static demo mode" } as T;
  }

  throw new Error(`Endpoint ${path} not available in static demo`);
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (staticFallbackActive || isStaticDemo()) {
    return handleStaticApi<T>(path, options);
  }

  const token = localStorage.getItem("arena-token");
  try {
    const response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map((d: { msg: string }) => d.msg).join("; ")
            : `Request failed (${response.status})`;
      throw new Error(detail);
    }
    return response.json() as Promise<T>;
  } catch (err) {
    const msg = (err as Error)?.message || "";
    if (
      msg.includes("Failed to fetch") ||
      msg.includes("NetworkError") ||
      msg.includes("Load failed") ||
      msg.includes("Connection refused")
    ) {
      staticFallbackActive = true;
      return handleStaticApi<T>(path, options);
    }
    throw err;
  }
}
export const post = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });
export const pct = (n: number) => `${Math.round(n * 100)}%`;
export const duration = (n: number) =>
  n < 1
    ? "<1 ms"
    : n < 1000
      ? `${Math.round(n)} ms`
      : `${(n / 1000).toFixed(1)} s`;
export const money = (n: number | null) =>
  n === null ? "Unknown" : n === 0 ? "$0.00" : `$${n.toFixed(4)}`;
export function ago(s: string) {
  const n = Math.max(
    0,
    Math.floor((Date.now() - new Date(s).getTime()) / 1000),
  );
  return n < 60
    ? "just now"
    : n < 3600
      ? `${Math.floor(n / 60)}m ago`
      : n < 86400
        ? `${Math.floor(n / 3600)}h ago`
        : `${Math.floor(n / 86400)}d ago`;
}
export function download(
  content: string,
  filename: string,
  type = "application/json",
) {
  const a = document.createElement("a");
  const u = URL.createObjectURL(new Blob([content], { type }));
  a.href = u;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}
