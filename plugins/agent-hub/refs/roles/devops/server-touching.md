# Server-touching protocols

<Owner: agents/devops.md § References>
<Read when: a tester sends an `infra_escalation_request`; a project's SERVER-INFO file is missing or needs a new fact; a Docker image or container is involved; an infrastructure decision may owe an ADR; or a non-ephemeral file is about to be written.>

---

## Server info

Every project devops **deploys to, or fetches logs from** MUST have `{workspace_root}/docs/devops/SERVER-INFO.md` (a single-machine desktop build needs none). Template: `templates/SERVER-INFO.md`.

- **First action**: check it exists. Missing → **propose** the template copy and return `needs_user_input`, one question per fact (hostnames, SSH access, CI pipeline names, log paths, monitoring URLs, vault refs). **Devops never writes the file itself** (unapproved scope, `CLAUDE.md` §0.2); it is written as an approved step after the answers.
- **Before every deploy, log fetch or debug request** re-read it, every run; cite the section and line for every command run from it.
- **It contradicts the host's real state** → ask, never pick one.
- **Update** it when an environment is added, a host changes, a vault path moves or a rollback is refined. Vault references only, never a secret value. It also declares alert owners, channels and short runbooks (`skills/devops-deploy/references/observability.md`).
- Stack bring-up lives in §3; a first infra escalation on a project whose file has no §3 is an automatic `needs_user_input`.

## Infra escalation

On an `infra_escalation_request` from test (`agents/test.md § Infra escalation`, Contract C1 of plan `agent-workflow-fix-20260605`):

1. Re-read SERVER-INFO. Missing → `needs_user_input` for the stack bring-up commands.
2. Run `stack_check` per §3: probe each `urls_checked[]` URL again from the devops side and check process health for each tracked service.
3. Services down with a bring-up command available → start them, idempotently. A migration or config drift needed → `needs_approval`.
4. Re-probe the URLs and return:

   ```yaml
   status: <any value of the § Output enum>
   infra_ready: boolean
   stack_status: [{ service, state, last_log_lines: 5 }]
   ```

5. `target_env=local` and §3 has no local bring-up script → `needs_user_input`: "Add local dev stack script to SERVER-INFO §3?".

## Docker images and containers

Binds every Docker command, local or on a server (R-DOCKER-REUSE): no duplicate image pulls, reuse existing containers, never many identical containers; the app's own FE or BE, unlike redis or a database, need not be reused.

1. **Image.** `docker image inspect <image>:<tag>` first. Present → no pull. Pull only when absent or another tag or digest is needed; compose runs `--pull missing`, never `--pull always`.
2. **Look first.** `docker compose -p <project> ps -a` for a compose stack, otherwise `docker ps -a --filter name=<name>` and `docker ps -a --filter ancestor=<image>`.
3. **Backing service** (redis, kafka, a database: software the project runs but does not write). One exists → reuse it even when tag, port or env differ; stopped → `docker start <name>` or `docker compose -p <project> up -d --no-recreate <service>`. Never `--force-recreate` it. For Postgres the one existing service is `shared-postgres` (`refs/local-postgres.md`); for Redis, S3 and Mailpit it is `shared-redis`, `shared-s3` and `shared-mailpit` (`refs/local-services.md`; no MinIO, Q-S3). On this machine every published port binds 127.0.0.1 (`refs/local-services.md` rule 2); `deploy/` stacks keep their own (Q-W6). The app cannot use it as it is → `needs_user_input` (recreating can lose data, `CLAUDE.md` §0.2).
4. **App service** (FE, BE: the project's own code). May be rebuilt or re-pulled and recreated: `docker compose -p <project> up -d --no-deps [--build] <service>` (recreates only when config or image changed; both unchanged, as on a broken stack (5) → add `--force-recreate`).
5. **One container per service.** Never a second project or container name for a service that has one. A stack that will not start → recreate its app services per 4; still failing → `needs_user_input`; never `down` on a backing service.
6. A service fitting neither 3 nor 4 → `needs_user_input` with that one question.

## Spec layer

Infrastructure does **not** use Use Cases: it uses an ADR in the project's ADR folder (`<docs>/adr/`), and devops neither reads nor edits `specs/` (`rules/SDD.md`).
- An infrastructure decision with business consequences (billing from cron to pub/sub, a storage region, a cache TTL that changes what users see) gets an ADR linking the UC or BR it affects.
- After a hotfix deploy, the handoff `next_step` reminds that `specs/_debt.md` carries an entry due within 24 hours. Devops does not write it; implement does.
- A deploy that changes user-visible behaviour with no UC covering it does **not** block, but goes in the handoff `risks`.

## Artifact filenames

`CLAUDE.md` §19.1 owns which paths devops may write and §19.4 owns naming. Four devops artifacts:

| Writes | Path | Naming |
|---|---|---|
| ADR | `<docs>/adr/{YYYY-MM-DD}-{kebab-title}.md` | links the UC or BR it affects |
| Fetched logs | `{plan_dir}/logs/{task_id}-{YYYYMMDD-HHMMSS}.log` | full and verbatim; the handoff cites the path plus ≤50 lines |
| Failure record | `docs/devops/{agent}-{task_id}-{YYYYMMDD-HHMMSS}.yaml` | on `status=failed`; `docs/devops/` is registered to devops as a whole folder |
| Server info | `docs/devops/` — `SERVER-INFO.md` and what it references | from the template, only after the user answered; vault references only |

Everything else is ephemeral under `.cm-tmp/{task_id}/`, deleted before the task is done. Nothing at a sub-repo root or at `{workspace_root}` outside the §19.1 folders; nothing under `docs/changes/**` beyond the plan files and `logs/`.
