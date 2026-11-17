# The devops boundary — brainstorm never reaches a host
<Owner: agents/brainstorm.md § References>
<Read when: the evidence an investigation needs lives on a host — a server log, a health check, process or disk state — so the Devops row of `agents/brainstorm.md` § Gates has fired>

---

## Brainstorm never reaches a host (HARD)

Brainstorm opens no SSH session, reads no host log and runs no command against a deployed service, read-only included (`ssh host "pm2 list"` is a devops spawn). An investigation that cannot reach its evidence stops and asks for it; it never reasons from code alone.

`devops` owns everything leaving the local working tree: SSH/SCP/rsync · deploy, rollback, restart (`pm2`, `systemd`, `nginx`) · `docker`/`kubectl` on a host · server logs, health checks, process or disk inspection · DNS, certificates, host env or secrets · migration, backup, restore against a deployed database.

## What to emit

- `needs_devops: true` with a `log_fetch_request` (host, path or service, time window, what to look for). Main spawns one `agent-hub:devops` for that fetch and re-spawns brainstorm with its output verbatim.
- A step that ships goes in a `devops` wave of `tasks.md`, after the wave of the implement task producing what ships; its rollback goes in `design.md`.
- The rest stays with its owner: a bug is still a bug.
