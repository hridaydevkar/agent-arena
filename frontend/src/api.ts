export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("arena-token");
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
