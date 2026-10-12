import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Check,
  Database,
  Download,
  KeyRound,
  Loader2,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useWorkspace } from "./context";
import { Badge, JsonBlock, PageHeading } from "./ui";
import { download, post } from "./api";
import { CodeBlock } from "./Docs";
export default function Settings() {
  const { health, overview, agents, tasks, rankings, jobs, toast, refresh } =
    useWorkspace();
  const [token, setToken] = useState(localStorage.getItem("arena-token") || "");
  const [checking, setChecking] = useState(false);
  const [providerBusy, setProviderBusy] = useState(false);
  const [checkResult, setCheckResult] = useState<unknown>(null);
  const [providerError, setProviderError] = useState("");
  return (
    <div className="page settings-page">
      <PageHeading
        eyebrow="WORKSPACE SETTINGS"
        title="Your arena. Your environment."
        description={
          health.read_only
            ? "Public results only. This server cannot execute agents or connect a provider."
            : "Connect a model once. Keep the key on your own computer."
        }
      />
      {!health.read_only && (
        <section className="card settings-section provider-setup">
          <div className="settings-section-title">
            <ShieldCheck size={21} />
            <div>
              <h2>OpenRouter setup</h2>
              <p>
                You do not need an OpenAI key. Your existing OpenRouter key
                works.
              </p>
            </div>
            <Badge tone={health.model_configured ? "green" : "amber"}>
              {health.model_configured
                ? "Configured · test below"
                : "Not configured yet"}
            </Badge>
          </div>
          <div className="provider-setup-body">
            <div className="setup-step">
              <span>01</span>
              <div>
                <strong>Stop the running server with Control + C</strong>
                <p>
                  In your own terminal, inside the extracted agent-arena folder:
                </p>
                <CodeBlock
                  code={".venv/bin/python scripts/setup_openrouter.py"}
                />
                <p>
                  macOS/Linux command above. On Windows use{" "}
                  <code>
                    .venv\Scripts\python.exe scripts/setup_openrouter.py
                  </code>
                  ; start with <code>py scripts/start.py --port 8002</code>.
                </p>
                <p>
                  Paste the key at the hidden terminal prompt. Setup checks your
                  key and lists current models advertising tool support. It
                  makes no inference calls. Pick a specific model ID;
                  free-priced entries are still quota-limited.
                </p>
              </div>
            </div>
            <div className="setup-step">
              <span>02</span>
              <div>
                <strong>Restart with your saved configuration</strong>
                <CodeBlock code={"python3 scripts/start.py --port 8002"} />
                <p>
                  The launcher automatically loads .env; local file settings
                  override older shell exports. The key is plaintext in that
                  git-ignored file—never share or commit it.
                </p>
              </div>
            </div>
            <div className="setup-step">
              <span>03</span>
              <div>
                <strong>Run one controlled comparison</strong>
                <p>
                  Go to Experiments. Select one task and compare Direct, Tool
                  user, and Verifier. Provider-side spending caps are your
                  spending protection; app limits cap requests, not dollars.
                </p>
                <Link to="/experiments" className="button primary">
                  Open experiments <ArrowRight size={15} />
                </Link>
              </div>
            </div>
          </div>
          <div className="settings-rows">
            <div>
              <span>Provider</span>
              <code>{health.provider}</code>
            </div>
            <div>
              <span>Configured model</span>
              <code>{health.model}</code>
            </div>
            <div>
              <span>Request pacing</span>
              <code>
                {health.provider_interval_seconds || 0} seconds between request
                starts
              </code>
            </div>
          </div>
          <div className="settings-actions">
            <span>
              Metadata check only: no paid model generation. Credentials never
              go to the browser.
            </span>
            <button
              className="button small"
              disabled={!health.model_configured || providerBusy}
              onClick={async () => {
                setProviderBusy(true);
                setProviderError("");
                try {
                  setCheckResult(await post("/provider/check", {}));
                } catch (e) {
                  setProviderError((e as Error).message);
                } finally {
                  setProviderBusy(false);
                }
              }}
            >
              {providerBusy ? (
                <Loader2 size={14} className="spin" />
              ) : (
                <RefreshCw size={14} />
              )}{" "}
              Check provider key
            </button>
          </div>
          {checkResult != null && (
            <div className="provider-check-result">
              <JsonBlock value={checkResult} />
            </div>
          )}
          {providerError && (
            <div className="form-error experiment-error">{providerError}</div>
          )}
        </section>
      )}
      <section className="card settings-section">
        <div className="settings-section-title">
          <Server size={20} />
          <div>
            <h2>Connection & runtime</h2>
            <p>The backend serving this browser.</p>
          </div>
          <Badge tone="green">
            <span className="live-dot" /> Online
          </Badge>
        </div>
        <div className="settings-rows">
          {[
            ["API endpoint", "/api · same origin"],
            [
              "Workspace mode",
              health.read_only
                ? "Public · read-only results"
                : "Local · single user",
            ],
            ["Server version", health.version],
            ["Suite fingerprint", health.suite_hash],
            ["Storage", "SQLite · server side"],
            [
              "Execution",
              health.read_only
                ? "Disabled by server boundary"
                : "Reference policies + three model architectures",
            ],
          ].map(([key, value]) => (
            <div key={key}>
              <span>{key}</span>
              <code>{value}</code>
            </div>
          ))}
        </div>
        <div className="settings-actions">
          <span>See the project README for port and storage settings.</span>
          <button
            className="button small"
            disabled={checking}
            onClick={async () => {
              setChecking(true);
              try {
                await refresh();
                toast("Backend connection is healthy.");
              } catch (e) {
                toast((e as Error).message, true);
              } finally {
                setChecking(false);
              }
            }}
          >
            <RefreshCw size={14} className={checking ? "spin" : ""} /> Check
            connection
          </button>
        </div>
      </section>
      {!health.read_only && (
        <section className="card settings-section">
          <div className="settings-section-title">
            <KeyRound size={20} />
            <div>
              <h2>Optional workspace write token</h2>
              <p>
                This is NOT your OpenRouter key. Leave it empty unless you set
                ARENA_API_TOKEN.
              </p>
            </div>
            <Badge tone={health.auth_enabled ? "green" : "amber"}>
              {health.auth_enabled
                ? "Write protection on"
                : "Local · no write token"}
            </Badge>
          </div>
          <div className="settings-form">
            <label htmlFor="api-token">
              Workspace token (not a provider key)
            </label>
            <div>
              <input
                id="api-token"
                type="password"
                autoComplete="off"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Only if ARENA_API_TOKEN was set"
              />
              <button
                className="button primary"
                onClick={() => {
                  if (token.trim())
                    localStorage.setItem("arena-token", token.trim());
                  else localStorage.removeItem("arena-token");
                  toast("Browser write-token preference saved.");
                }}
              >
                <Check size={15} /> Save token
              </button>
            </div>
            <p>
              Saved in this browser’s local storage. Use only a trusted device.
              Provider keys belong in the local setup wizard, never this field.
            </p>
          </div>
        </section>
      )}
      <section className="card settings-section">
        <div className="settings-section-title">
          <Database size={20} />
          <div>
            <h2>Workspace metadata snapshot</h2>
            <p>For private analysis, not the public-release workflow.</p>
          </div>
          <button
            className="button small"
            onClick={() =>
              download(
                JSON.stringify(
                  {
                    exported_at: new Date().toISOString(),
                    health,
                    overview,
                    agents,
                    tasks,
                    rankings,
                    jobs,
                  },
                  null,
                  2,
                ),
                "arena-workspace-snapshot.json",
              )
            }
          >
            <Download size={14} /> Export JSON
          </button>
        </div>
        <div className="settings-actions">
          <span>
            For publishing, use Experiments → Export public report. That export
            excludes raw prompts, outputs, traces and private errors. This
            snapshot is not a restorable database backup.
          </span>
        </div>
      </section>
    </div>
  );
}
