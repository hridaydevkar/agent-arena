# Published results go here

This directory intentionally starts without results.json. No live model results have been generated for you.

After running a real experiment locally, use the Experiments page's **Export public report** button or:

```
python3 scripts/publish_results.py --url http://localhost:8002 --latest --confirm-public
```

The export includes agent/model/architecture identities and result metrics, but NOT prompts, fixtures, raw traces, outputs, API keys or private error details. Review results.json before committing it. If you name an agent/model something private, the name can still appear: this is a field allowlist, not a general PII detector.

The public server reads this file at startup with ARENA_READ_ONLY=1. Without it, the public app shows explicitly labelled reference-policy demos, not invented model results.
