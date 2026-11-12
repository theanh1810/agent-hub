# agentHub

A multi-agent workflow for Claude Code. An orchestrator routes each request to specialist agents (brainstorm, planner, implement, reviewer, test, designer, devops) with spec, plan and review gates between them.

## Install

```
/plugin marketplace add theanh1810/agent-hub#release
/plugin install agent-hub@agent-hub
```

Installing asks for one setting, the reply language (see Reply language).

## Prerequisites

- A Claude Code version that supports plugins with `userConfig`.
- Python 3.11 or newer, on the PATH as `python3` on every OS: every hook and command calls `python3`. On Windows the python.org installer provides only `python` and `py`, so install Python from the Microsoft Store (it provides `python3`) or add a `python3` alias on the PATH before installing. On macOS the python3 that ships with the Command Line Tools is 3.9, so install a newer one. A missing Python is reported, not skipped silently.
- git.

## Optional parts

Each optional plugin installs the same way: `/plugin install <name>@agent-hub`.

| Plugin | What it adds |
|---|---|
| `agent-hub-auditor` | `/audit`: scores what the agents did in a time window and writes a report under `docs/audits/` |
| `agent-hub-integrations` | the `lark-task` skill, MCP launcher scripts, Codex and ChatGPT templates. `agent-hub-codex convert` finds the core plugin installed beside it; otherwise set `AGENT_HUB_RULESET` to the core plugin folder |
| `agent-hub-local-services` | the Docker preflight hook and the local-services reference |

Optional tools, and what happens without them:

| Tool | Without it |
|---|---|
| GitNexus (code graph) | agents fall back to grep and say so |
| mem0 | no cross-project memory; the project memory file still works |
| Context7 | library questions are answered from the repository and its docs |
| Playwright plugin | the test agent cannot drive a browser; it reports which cases it could not run |
| RTK (output filter) | terminal output is not shortened |

## Reply language

At install you choose the language the agents use to talk to you: replies, questions, and the plan summary file. The default is English (`en`); any ISO 639-1 code works, for example `vi` or `ja`. With English the plan summary file is not written. The files the agents read stay in English whatever you choose.

## Read guard

Reading a whole file longer than 200 lines or larger than 16 KiB, with the Read tool or a plain `cat`, is refused, and the agent reads it in parts with `offset` and `limit`. This keeps long files from filling the context window. Change the limits with the plugin options `read_guard_lines` and `read_guard_bytes`, or set `read_guard` to `off` to switch the guard off.

## Not managed

The plugin does not touch your permissions, model, environment variables, status line or auto mode. Those stay in your own Claude Code settings.

## Uninstall

```
/plugin uninstall agent-hub@agent-hub
/plugin marketplace remove agent-hub
```

Repeat the first command for each optional plugin you installed. Files the agents wrote into your projects (`docs/`, `specs/`) are yours and stay.

## Licence

MIT with the Commons Clause: you may use and modify it, you may not sell it. The `LICENSE` file is the authority; this paragraph is only a summary. Third-party components keep their own licences, listed in `THIRD_PARTY_NOTICES.md`.

## Credits

Ideas adopted from the projects below were rewritten in this package's own words; no text was copied. Links are in `THIRD_PARTY_NOTICES.md`.

- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)
- [leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill)
- [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [dietrichgebert/ponytail](https://github.com/dietrichgebert/ponytail)
- [anthropics/skills](https://github.com/anthropics/skills)
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
- [mattpocock/skills](https://github.com/mattpocock/skills)
- [obra/superpowers](https://github.com/obra/superpowers)
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)
- [mksglu/context-mode](https://github.com/mksglu/context-mode)
