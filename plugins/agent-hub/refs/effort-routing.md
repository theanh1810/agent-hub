# Effort routing — each agent's model and each spawn's effort
<Owner: rules/core.md>
<Read when: spawning any agent (the `model` and `effort` of the Agent call); changing an agent's model>

---

Seven agent files exist, one per role, and no variant of any. Main thread passes `effort` (and `model` where § Per-spawn override says so) on the `Agent` call; the effort reaches the request as `output_config.effort`, the model comes from the agent's frontmatter unless the call overrides it (probe P-EFF, 2026-11-16).

## Model per agent

The one table of the ruleset that states a model; each agent file's frontmatter `model:` equals it (`tools/check-ruleset.sh` check 2, both directions).

| Agent | Model |
|---|---|
| brainstorm | opus |
| scout | sonnet |
| designer | sonnet |
| implement | sonnet |
| reviewer | opus |
| test | sonnet |
| devops | opus |

`devops` is opus and is never lowered, except the closed allowlist of § Simple devops.

## Tier

Brainstorm scores every request it takes and returns `tier`; before it returns, a spawn runs at L2 (§ Fallback). Eight factors, 0-5 each, one evidence line each (a value with none is an estimate and says so), recorded in the machine record as `task_score: {factors: {C: {value, evidence}, …}, score, tier}`.

| Value | C Complexity | S Scope | R Risk | U Uncertainty |
|---|---|---|---|---|
| 0 | text, rename, typo | one line | almost no consequence | exactly what to change is known |
| 1 | simple logic, one file | one file | a small UI fault | almost sure |
| 2 | one module, clear logic | one module | a feature fault | a few files to read |
| 3 | several modules, state or async | several modules | temporary user or data impact; a fleet rule that changes agent behaviour | needs investigation |
| 4 | distributed, concurrency, performance | several services or repos | security, data consistency, production | several hypotheses |
| 5 | architecture, many failure modes | the whole system, many repos | data loss, money, downtime | cause unknown |

| Value | I Integration | D Data / state | O Operational | V Verification |
|---|---|---|---|---|
| 0 | none | stateless | the local tree only, `~/.claude` included | visible by eye |
| 1 | one internal service | UI state | app code through the normal pipeline | lint, typecheck, `python3 tools/check.py ruleset` (agent-hub repo only) |
| 2 | DB or Redis | application state | build or staging config | unit test |
| 3 | DB + cache + queue | persistent DB | CI/CD, Dockerfile, deploy config | integration |
| 4 | several services + an external API | shared or distributed state | production infra, a customer host | concurrency or failure; or only a real agent run shows the behaviour |
| 5 | a distributed ecosystem | money, identity, permissions | DB failover, cluster, network | production-like or load |

Score = C + S + U + I + V + 1.5·R + 1.25·D + 1.25·O, at most 45. L0 [0, 8) · L1 [8, 19) · L2 [19, 28) · L3 [28, 36) · L4 [36, 45].

**Security override.** On when security is named in the request or a factor's evidence line (whole word: `token` in "design token" is not security) and R ≥ 3 or D ≥ 4; brainstorm returns `security_override: true`. It allows the Codex diff review (`refs/roles/reviewer/second-opinion.md`); R ≥ 4 also adds one `reviewer mode=security` spawn beside `independent`.

## Effort per spawn

Tier = the work tier L0-L4 of the request. The default is the effort a spawn carries when nothing below raises it.

| Agent | Default effort | Raised to, when |
|---|---|---|
| brainstorm | high | max at tier L4, or on `effort_rise_requested` |
| scout | low | never |
| designer | medium | never |
| implement | medium | high at tier L3 or above, or in a fix round |
| reviewer | high | never |
| test | medium | high on a retest after red |
| devops | high | never |

## Per-spawn override

- `implement` at tier L4: `model: opus`; every other tier runs the frontmatter model.
- `devops` on a simple step: `model: sonnet`, `effort: low` (§ Simple devops).
- No other spawn overrides `model`.

## Simple devops

User 2026-10-10. A `devops` spawn runs with `model: sonnet`, `effort: low` only when every step it carries is one of

1. a plain `git push` of a branch (never a force push), or opening a merge request;
2. start, stop, restart or status of an application service through pm2, systemd or docker, on a host listed in `docs/devops/SERVER-INFO.md`;
3. a read-only fetch of logs, health, process or disk state;

and none of the `needs_approval` rows of `agents/devops.md` § Gates holds, and no step changes a firewall, SSH, network, user or permission setting or restarts sshd or a firewall service. Any doubt: the frontmatter model, opus. Main thread decides it; devops never lowers itself, and returns `needs_revision` with `reason: devops_op_not_simple`, naming the step and running nothing, when a step is outside this list.

## Fallback

- No tier, or one outside L0-L4: L2, the default column above.
- Clamp to what the model supports: a model without the requested effort runs the highest it has; `xhigh` and `max` need thinking on. Say which in the handoff.
