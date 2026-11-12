# Local shared services

<Read when: a task needs a backing service (redis, S3, mail), a docker command starts one, or a worktree or task starts or ends — every agent, once per run that names a service. Applies when agent-hub-local-services is installed.>

---

One instance each of Postgres, Redis, S3 and Mailpit serves every project on this machine.

The `infra_dir` plugin option names the directory that holds the compose files and helper scripts of these services. With `infra_dir` unset, the hook's shared-service rules (1 and 3 below) are off and only the publish rules (2) apply.

| Service | Image | Host ports (127.0.0.1 only) | Defined in | Isolation per project and task |
|---|---|---|---|---|
| Postgres | `postgres:16` | 5432 | `<infra_dir>/postgres/compose.yaml`; detail in `refs/local-postgres.md` | one database per task from `task-db.sh` |
| Redis | `redis:7-alpine` | 6379, no password | `<infra_dir>/redis/compose.yaml` | key prefix `<project>:<task>:` |
| S3 | SeaweedFS, container `shared-s3` | 9000 (container port 8333) | the stack that first created it, outside `<infra_dir>` | one bucket `<project>-<task>` |
| Mail | Mailpit | 1025 SMTP, 8025 UI | `<infra_dir>/mailpit/compose.yaml` | one shared inbox |

The hook accepts exactly these container names: `shared-postgres`, `shared-redis`, `shared-mailpit`, `shared-s3`.

Rules:

1. Never start another instance of these four services in any project, for any reason; any second S3-compatible container (minio, or a second seaweedfs) counts as a duplicate. Use the shared one.
2. Every published port, of any container, binds `127.0.0.1` only, as `127.0.0.1:host:container`; never `0.0.0.0`, a bare `host:container` pair, `-P`/`--publish-all` or host networking.
3. A project's own compose files define none of the four.
4. `deploy/` stacks are exempt.
5. Keep secret and credential values out of every log and reply; never print one.
6. Leave the shared S3 container and its volume in place; never remove or recreate either: it holds data with no dump.
7. The plugin's `docker_preflight.py` hook enforces 1 and 2 on every agent's Bash command; `CLAUDE_DOCKER_PREFLIGHT=off` is the kill switch and paths under `<infra_dir>` are always allowed. A blocked command prints a message pointing to this file.
