# Local Postgres

<Read when: a task needs a database, a test run needs an isolated database, or a worktree or task starts or ends — every agent, once per run that names a database. Applies when agent-hub-local-services is installed.>

---

One shared Postgres serves every project on this machine; a worktree or task gets its own database on it. `<infra_dir>` is the `infra_dir` plugin option.

| Fact | Value |
|---|---|
| Service | image `postgres:16`, container `shared-postgres`, `127.0.0.1:5432` |
| Defined in | `<infra_dir>/postgres/compose.yaml` (start: `docker compose -f <infra_dir>/postgres/compose.yaml up -d --wait`) |
| Roles | one per project, from `<infra_dir>/postgres/projects.conf`; roles may create databases and are not superusers; any extra grant a project needs is listed in that file |
| Task database | `<infra_dir>/postgres/bin/task-db.sh create <project> <task>`; `url <project> <task>` prints the connection URL; the database is the isolated test database of `refs/roles/test/two-pass.md`; create refuses a database name the ledger already holds for another project and task (exit 2) |
| Drop | `task-db.sh drop <project> <task>` at closeout, only the task's own database; `sweep` drops databases whose worktree directory is gone |

Rules:

1. Never start, recreate or publish another Postgres container or service, in any project, for any reason; use the shared one. Redis, S3 and Mailpit follow the same rule in `refs/local-services.md`.
2. A database in the project's protected list of `projects.conf` is never dropped, reset or migrated without the user.
3. Never print a password; export `DATABASE_URL` per command. Call `task-db.sh url` only inside command substitution, `DATABASE_URL="$(task-db.sh url <project> <task>)" <cmd>`; a bare `url` call or echoing its result is forbidden.
4. A project's own `docker compose` files reach the shared Postgres and do not define one.
