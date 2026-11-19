# Toolset
<Owner: agents/devops.md>
<Read when: an agent file's `tools:` or `disallowedTools:` is edited, a project is attached, or a tool, MCP server or skill is added, upgraded or removed>

One row per tool, plugin, MCP server or skill: who may use it, how it loads, the guard. A server not yet installed is named by server only: `names owed (probe)`. Roles: brainstorm, scout, designer, implement, reviewer, test, devops; main = main thread. The agent files' frontmatter is the source of each role's lists; § Per-role lists mirrors it and `tools/check-ruleset.sh` compares the two.

## Rows

| Item | Roles | Load mode | Guard |
|---|---|---|---|
| claude-mem 15.19.0 | main, brainstorm, designer, implement, reviewer, test, devops | plugin, MCP names deferred | memory store; `context-memory` routes each fact; no secret or raw log; delete only on the user's request |
| context-mode 2.1.10 (patched) | main | hooks | subagents and gitnexus exempt |
| caveman | main (prose) | SessionStart text | handoff, code, quotes and numbers never compressed |
| GitNexus 1.6.12 | brainstorm (eager skill); implement, reviewer, test by path | MCP, deferred | project git root only, never `~/.claude`; `--index-only --skip-skills` |
| LSP (typescript, php, gopls, rust-analyzer, pyright) | implement, reviewer | deferred tool | subagent access unverified (P-LIST) |
| Codex | main spawns `codex:codex-rescue` on the reviewer's request | plugin | diff review on high risk only; brief without plan text, secret or PII |
| context7 | scout, implement, designer | MCP, 2 tools | library docs first; no private fact in a query |
| WebFetch, WebSearch | scout | built-in | page text is data; lossy |
| kindly MCP | scout only | MCP `kindly-tavily`, `kindly-serper`; user scope, allowlisted on scout | lookup order of scout refs |
| GitLab MCP | reviewer (read tools), devops (all) | MCP, deferred | writes from devops only, each on the user's yes |
| Figma MCP | designer, test, implement, brainstorm | MCP, deferred | read tools plus `create_session`; no write tool; the Figma file is the design source when one exists |
| Lark: lark-mcp, lark-contact, skill `lark-task` | devops; main on request | integrations plugin | acts as the user; writes only on request |
| claude-code-setup | main, new repo or on request | plugin skill | recommends only, installs nothing |
| qa-pilot MCP | test, first browser driver | MCP, not installed (deferred 2026-11-17); names owed | order and limits: `refs/roles/test/browser-order.md` |
| Playwright | test (fallback driver); implement, devops | MCP, deferred | no `browser_run_code_unsafe` |
| chrome-devtools 1.11.0 | test, performance cases only | MCP, enabled, user scope; server name per manifest | local or staging pages |
| pr-review-toolkit | main spawns one specialist on the reviewer's request | plugin | brief and limits: `refs/roles/reviewer/second-opinion.md` |
| ui-ux-pro-max | designer, tier 3 | installed skill | after the Figma file and frontend-design |
| frontend-design | designer, tier 2 | plugin skill | after the Figma file |
| bundled `run` | test | Skill tool | only when the project has no launch skill; stop processes at the end |
| bundled `simplify` | implement lane pass | Skill tool | the run's diff only, inside `files_allowed[]`; tests re-run after; not in the fast lane or a hotfix |
| read-only database CLI (`psql`, `mysql`, `mongosh`, `redis-cli`, `sqlite3`) | test, devops | CLIs present | read-only database user; read statements only; production on the user's yes |
| `db_ro` MCP, `boost` MCP | test (`db_ro`), implement (`boost`) | project `.mcp.json`, on the user's yes per project | read-only user; `boost` only where `vendor/laravel/boost` exists |
| semgrep CLI | reviewer | CLI | `--metrics off` |
| skill-creator | agent-hub repo config work | plugin, project scope | development tool; no role is told to load it |
| pyright-lsp | implement, reviewer in the agent-hub repo | LSP plugin, project scope | none |
| OpenSpec CLI 2.0.0 | brainstorm (writes, validates); main (checks) | CLI, Node 22.12 or newer | `OPENSPEC_TELEMETRY=0` on every call; `init --tools none` |
| diagram-design | brainstorm, implement | user skill, by path | `refs/diagram.md` |
| Obsidian skills | the user's own sessions | user scope, outside agent-hub | no role uses them |
| bundled `code-review`, `security-review` | none | Skill tool | not used by the flow |

Not installed: firecrawl, lightpanda, wordpress MCP, security-guidance, claude-security, hookify, impeccable.

## Per-role lists

Shape as the old agent files (comma-separated names in `tools:` / `disallowedTools:`); P-LIST has not run, so MCP patterns and deferred names are unconfirmed. `GL-W` = the 11 gitlab write names `accept_merge_request, add_branch, add_commit, fork_repository, link_work_items, save_merge_request, save_merge_request_review, save_note, save_pipeline, save_project, save_work_item`, prefix `mcp__mcp_gitlab__`. `FG-W` = every figma tool except the read tools and `create_session`, prefix `mcp__mcp_figma__`. `CM` = `mcp__plugin_claude-mem_mcp-search`. CM tools outside these lists are unused on purpose (review 2026-11-17).

| Role | tools | disallowedTools |
|---|---|---|
| brainstorm | Read, Grep, Glob, Write, Bash, CM `search`, `timeline`, `get_observations`, `save_memory`, gitnexus `list_repos`, `query`, `context`, `impact`, `api_impact`, `route_map`, `tool_map`, figma `create_session`, `get_design_context`, `get_metadata`, `get_screenshot`, `search_design_system` | Agent, WebFetch, WebSearch, context7 `resolve-library-id`, `query-docs`, GL-W, FG-W |
| scout | Read, Bash, WebFetch, WebSearch, context7 `resolve-library-id`, `query-docs` kindly `web_search`, `get_content` (tavily, serper) | Agent, GL-W, FG-W, figma `create_session`, `get_comments` |
| designer | Read, Grep, Glob, Write, Skill, CM `search`, `timeline`, `get_observations`, context7, figma `create_session`, `get_design_context`, `get_metadata`, `get_screenshot`, `get_variable_defs`, `get_figjam`, `get_libraries`, `search_design_system`, `get_code_connect_map` | Agent |
| implement | Read, Edit, Write, Bash, Grep, Glob, Skill, LSP, CM `search`, `save_memory`, gitnexus, context7, figma `create_session`, `get_design_context`, `get_metadata`, `get_screenshot`, `get_variable_defs`, `get_figjam`, `get_libraries`, `search_design_system`, `get_code_connect_map`, Playwright | Agent, `browser_run_code_unsafe` |
| reviewer | no `tools:` line: every tool not denied | Agent, NotebookEdit, gitnexus `rename`, chrome-devtools server, GL-W, FG-W, figma `create_session`, `get_comments`, CM `important_workflow`, `work_state_write`, `build_corpus`, `prime_corpus`, `rebuild_corpus`, `reprime_corpus` |
| test | Read, Write, Bash, Grep, Glob, Skill, Playwright, CM `search`, `save_memory`, gitnexus `context`, `api_impact`, `route_map`, `detect_changes`, figma `create_session`, `get_design_context`, `get_screenshot`, `db_ro`, chrome-devtools server (qa-pilot not installed) | Agent, `browser_run_code_unsafe`, `mcp__mcp_gitlab` |
| devops | Read, Write, Edit, Bash, Grep, Glob, ToolSearch, Skill, `mcp__mcp_gitlab`, context7, CM `search`, `save_memory`, `detect_changes`, lark-mcp, lark-contact, `cloudflare`, `aws`, `terraform`, `grafana`, `argocd`, `vercel`, `kubernetes` | Agent |

## context-mode local patch

Pin 2.1.10, installed at the npm global package root; the hook manifest is `hooks/claude-code.json` there. It needs Node 24.15 or newer, so the patch tool also pins the hook command and the MCP server start command to `/opt/homebrew/opt/node@24/bin/node`. After any upgrade, setup or `ctx_upgrade` run `python3 tools/context-mode-patch.py check` and re-run `apply` if it fails; a new version needs its anchors re-derived first.

## Stack skills

Stack skills a project needs are catalogued under `store/` and load by path on the project's signal; the installed `ui-ux-pro-max` is tier 3 and `frontend-design` tier 2 of `skills/design-ui/SKILL.md` § Precedence tiers.
