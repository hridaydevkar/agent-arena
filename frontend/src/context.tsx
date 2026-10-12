import { createContext, useContext } from "react";
import type { Agent, Health, Job, Overview, Ranking, Run, Task } from "./types";
export type BenchPreset = { agentId?: string; taskId?: string };
export type Workspace = {
  agents: Agent[];
  tasks: Task[];
  rankings: Ranking[];
  overview: Overview;
  runs: Run[];
  jobs: Job[];
  health: Health;
  refresh: () => Promise<void>;
  toast: (message: string, error?: boolean) => void;
  openBenchmark: (preset?: BenchPreset) => void;
  openAgent: () => void;
  openMethods: () => void;
};
export const WorkspaceContext = createContext<Workspace | null>(null);
export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("Workspace unavailable");
  return ctx;
}
