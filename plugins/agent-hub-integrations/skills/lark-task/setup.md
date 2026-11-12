# lark-task setup (one time)

Single user, stdio, this machine, larksuite.com. Placeholders only: never paste a real App Secret
into this file.

## Steps

1. Create a custom app at https://open.larksuite.com/app (a personal org: you approve your own app).
2. Add the redirect URL exactly `http://localhost:47123/callback`. It must equal the login
   `--host` / `-p` below. The default port is avoided because local apps already use it.
3. Enable scopes (read + write, full names): `task:task:read`, `task:task:write`, `task:tasklist:read`,
   `task:tasklist:write`, `task:section:read`, `task:section:write`, `task:custom_field:read`,
   `task:custom_field:write`, `contact:user.id:readonly`, `offline_access`. Use the full names exactly as listed: bare task scope names such as `task:task` (without `:read`/`:write`) are rejected by Lark (error 20043).
4. Create and publish an app version (self-approve if you own the org).
5. Store the app secret in the Keychain first (`security add-generic-password -U -s agent-hub-lark -a "$USER" -w`; the prompt takes the value), then register the two MCP servers (user scope) through the launch script:

In the commands below `${CLAUDE_PLUGIN_ROOT}` is this plugin's install folder; type its absolute path in your shell.

```
claude mcp add --transport stdio --scope user lark-mcp -- ${CLAUDE_PLUGIN_ROOT}/scripts/mcp/lark.sh agent-hub-lark mcp -a <APP_ID> -d https://open.larksuite.com --oauth --token-mode user_access_token --host localhost -p 47123 --scope offline_access,task:task:read,task:task:write,task:tasklist:read,task:tasklist:write,task:section:read,task:section:write,task:custom_field:read,task:custom_field:write,contact:user.id:readonly -t task.v2.tasklist.create,task.v2.tasklist.list,task.v2.tasklist.get,task.v2.tasklist.addMembers,task.v2.tasklist.tasks,task.v2.section.create,task.v2.section.list,task.v2.section.patch,task.v2.section.tasks,task.v2.customField.create,task.v2.customField.add,task.v2.customField.list,task.v2.customField.get,task.v2.customFieldOption.create,task.v2.task.create,task.v2.task.get,task.v2.task.patch,task.v2.task.addMembers,task.v2.task.addTasklist,task.v2.task.addReminders,task.v2.taskSubtask.create,task.v2.taskSubtask.list,contact.v3.user.batchGetId
```

The `--scope` value is the step 6 login `--scope` value, byte for byte: lark-mcp refreshes through the same token provider that issued the token only when both commands carry it; without it every refresh fails with Lark error 20038 and you must log in again every ~2 h. The `-t` value is one comma-joined token (23 tools, dot case, no spaces). `task.v2.tasklist.addMembers` and
`task.v2.task.addReminders` are granted on purpose although no procedure in `SKILL.md` calls them
yet, so a later procedure needs no re-registration.

Then, in the same shell, register the lookup server. It serves only `contact.v3.user.batchGetId`,
which lark-mcp lists above but drops in `user_access_token` mode (that API accepts only the app
token). It runs as the app (`tenant_access_token`), read-only, with no `--oauth` and no port; every
task call stays on lark-mcp:

```
claude mcp add --transport stdio --scope user lark-contact -- ${CLAUDE_PLUGIN_ROOT}/scripts/mcp/lark.sh agent-hub-lark mcp -a <APP_ID> -d https://open.larksuite.com --token-mode tenant_access_token -t contact.v3.user.batchGetId
```

The two `-t` values are the only lists of granted tools.

6. Log in as yourself (browser consent opens); the script reads the secret from the Keychain:

```
${CLAUDE_PLUGIN_ROOT}/scripts/mcp/lark.sh agent-hub-lark login -a <APP_ID> -d https://open.larksuite.com --host localhost -p 47123 --scope offline_access,task:task:read,task:task:write,task:tasklist:read,task:tasklist:write,task:section:read,task:section:write,task:custom_field:read,task:custom_field:write,contact:user.id:readonly
```

Pass the scope as one comma-joined value with no spaces.

The secret sits in the macOS Keychain (item `agent-hub-lark`) and reaches lark-mcp and lark-contact only as the `APP_SECRET` environment variable of the process the launch script starts; it is on no command line and not in `~/.claude.json`.

7. Restart Claude Code so the lark-mcp and lark-contact tools load.
8. Run `/lark-task` to init the template tasklist and the first project.
9. Open the `[PRJ]` tasklist in Lark and switch it to Board view grouped by section (no API).

## Troubleshooting

- Auth errors after token expiry: in a terminal run the step 6 login command (same `-p 47123`); `lark.sh` reads the secret from the Keychain. Worst case run `npx -y @larksuiteoapi/lark-mcp logout -a <APP_ID>` first, then the step 6 login command.
- Consent window: the browser consent must be completed within 60 s, otherwise login times out; re-run it.
- Port in use: pick another free port and change the console redirect URL and `-p` together.
- Rotate the secret: change it in the Lark developer console, run `security add-generic-password -U -s agent-hub-lark -a "$USER" -w` (the prompt takes the value), then
  `claude mcp remove lark-mcp --scope user` and `claude mcp remove lark-contact --scope user`, then re-run step 5 (both
  `claude mcp add` commands through `lark.sh`), then run the step 6 login again; the secret is in the Keychain only.
- Tools missing in the session: restart Claude Code; check the server names and status with `claude mcp list` piped through a filter that prints only name and status (never paste raw output).
- `contact.v3.user.batchGetId` missing: it never appears under lark-mcp (`user_access_token` mode drops
  tenant-only tools); it is served by `lark-contact`. Check `claude mcp get lark-contact`, then restart
  Claude Code. A lookup that returns no open_id for a colleague's email: check that the app's contact
  data range in the Lark developer console covers that person.
- Auth or permission error from `lark-contact`: the step 6 login does not fix it, because that server
  runs on the app token. A wrong or rotated secret: Rotate the secret above. A permission error: check
  that the published app version (step 4) includes `contact:user.id:readonly` (step 3).
