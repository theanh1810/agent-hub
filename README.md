# agentHub

A multi-agent workflow for Claude Code. The main thread routes each request by a lane table to seven specialist agents: brainstorm, scout, designer, implement, reviewer, test and devops. A short core of four principles governs every lane. Larger changes are planned as OpenSpec change folders written by brainstorm, with a detailed Vietnamese plan document, and checked by machine before any code is written. A run ends with one reviewer pass.

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
| `agent-hub-integrations` | the `lark-task` skill and MCP launcher scripts |
| `agent-hub-local-services` | the Docker preflight hook and the local-services reference |

Optional tools, and what happens without them:

| Tool | Without it |
|---|---|
| GitNexus (code graph) | agents fall back to grep and say so |
| claude-mem (the memory store) | no cross-project memory; the project memory file still works |
| Context7 | library questions are answered from the repository and its docs |
| Playwright plugin | the test agent cannot drive a browser; it reports which cases it could not run |
| context-mode (output filter; optional, user-installed, see `plugins/agent-hub/refs/toolset.md`) | terminal output is not shortened |

## Reply language

At install you choose the language the agents use to talk to you: replies and questions. The default is English (`en`); any ISO 639-1 code works, for example `vi` or `ja`. The files the agents read stay in English whatever you choose.

## Read guard

The guard is off by default. Set the plugin option `read_guard` to `on` and reading a whole file longer than 200 lines or larger than 16 KiB, with the Read tool or a plain `cat`, is refused, and the agent reads it in parts with `offset` and `limit`. Change the limits with `read_guard_lines` and `read_guard_bytes`.

## Research cache

What the agents learn from outside sources (docs, papers, vendor pages) is kept in `research-cache` inside your Claude config folder, one file per question with the source and the day each claim was checked, so the same research is not paid for twice. An agent reads the index before it searches the web. A new entry waits in `pending/` until the main thread has checked it with `agent-hub cache promote`; each promotion is listed for you at the end of the run, and `agent-hub cache promote --archive <slug>` retires one. Set the plugin option `research_cache_dir`, or the environment variable `AGENT_HUB_RESEARCH_CACHE`, to keep the cache elsewhere. The plugin option `moment_hooks` set to `off` stops the plugin from handing the index to agents.

## Rules at the moment of use

The plugin hands an agent a rule when it applies, once per agent run: the code-style file of a language on the first write of such a file (the shared `_discipline.md` is read at intake instead), the commit rules on the first commit, a reminder at 25 and at 40 tool calls. Two checks may refuse a call of the implement agent, each at most twice per run, after which the call goes through with a warning: an edit of code before a test run, and a commit whose message has no `Refs:` line. Only a test run opens the first gate. A test run is a runner started as the command of a shell step, not one named in text; the wrapper words `timeout`, `nice`, `ionice`, `stdbuf`, `env` and `sudo` and the shell keywords `if`, `do`, `while` and `!` are looked through. The families are pytest, `python -m unittest`, `manage.py test`, `coverage run -m pytest`, tox, nox, `hatch test`, npm/pnpm/yarn/bun scripts named `test` or `test:*`, jest, vitest, mocha, playwright, `node --test`, deno, go, cargo (test, nextest), gradle, maven, dotnet, rspec, `rails test`, rake, phpunit, pest, composer, swift, xcodebuild, flutter, dart, mix, `make test` or `make check`, `just test`, `task test`, turbo, nx, ctest, bazel, and a script named `test*.sh` or `run-tests*`. Lint, build and type-check calls (`npm run lint`, eslint, ruff, shellcheck, `tsc --noEmit`), `cargo check`, `cargo clippy`, `agent-hub check`, `tools/check.py`, a bare `make`, and any runner asked for `--version`, `--help` or `--collect-only` do not open it. A runner that never started (the shell's own `command not found` for it, a missing npm script, no Makefile target, no `Cargo.toml`, exit 126 or 127 with no test summary) does not count, and a red run does. Edits of `.css`, `.scss`, `.html` and `.sql` are not held to it. Two kinds of run are exempt and get the reminder once: one that continues after a turn ceiling (it read its `.cm-tmp/<task>/progress.yaml`, with the Read tool or with `cat`, `head`, `less` or `sed -n`) and one that runs the `simplify` skill. A call let through after two refusals says so to you and to the agent, which reports it under `Risks`. Writes made from the shell are seen from the command text only (a redirect, `tee`, `sed -i`, a python or node heredoc), and a commit message the shell builds (`-m "$MSG"`) is not read. Set the plugin option `hook_blocks` to `off` (or the environment variable `AGENT_HUB_BLOCKS=0`) and they only remind. `moment_hooks` set to `off` (or `AGENT_HUB_MOMENTS=0`) turns all of it off, and the agents then read craft and the language file themselves before writing code.

## Return check

When an agent finishes, the plugin checks its report: the header line, the six sections, the block of fields the main thread reads, and for the reviewer and test agents the verdict, the review file and the evidence (which it also scans for secrets). A report that fails is sent back to the agent with the list of what is missing, at most twice per agent run; after that it goes through and you see a note saying which problems remain. `hook_blocks` set to `off` keeps the note and drops the sending back; `moment_hooks` set to `off` turns the check off.

## Not managed

The plugin does not touch your permissions, model, environment variables, status line or auto mode. Those stay in your own Claude Code settings.

## Uninstall

```
/plugin uninstall agent-hub@agent-hub
/plugin marketplace remove agent-hub
```

Repeat the first command for each optional plugin you installed. Files the agents wrote into your projects (`docs/`, `openspec/`) are yours and stay.

## Licence

MIT with the Commons Clause: you may use and modify it, you may not sell it. The `LICENSE` file is the authority; this paragraph is only a summary. Third-party components keep their own licences, listed in `THIRD_PARTY_NOTICES.md`.

## Credits

Some texts from the projects below are carried verbatim with attribution, and other ideas were rewritten in this package's own words. Each carried passage, its pinned source and its licence are listed in `THIRD_PARTY_NOTICES.md` and `tools/upstream/manifest.yaml`.

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
