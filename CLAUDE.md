# CLAUDE.md

**This project uses [`AGENTS.md`](./AGENTS.md) as the single source of truth for all AI agents — read it fully before acting.** It defines the project, the non-negotiable guardrails, multi-agent coordination, current state, and the agent fleet.

Critical reminders (full detail in AGENTS.md):
- Research & education only, **not advice**, 21+. **LLMs never produce recommendation numbers** — those are deterministic engine functions.
- **Model integrity:** never let news/external signal contaminate the walk-forward-validated Dixon-Coles model. News views stay separate + flagged.
- **Security:** external/user content is untrusted (LLM01); LLM endpoints stay hardened (LLM10); secrets gitignored, never committed.
- **Coordination:** commit prefixed `claude:`; non-Claude agents work on branches → PRs; **Claude is the single review/merge gate**; never redeploy without Stav's say-so; verify before claiming done.
