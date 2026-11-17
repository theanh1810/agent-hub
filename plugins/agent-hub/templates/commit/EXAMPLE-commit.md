# Commit message — worked example

Reference shape for `refs/roles/implement/close-task.md` § Close the task. Read it when unsure what a
good body looks like, take the shape from it and write your own words; do not copy its wording.

```
fix(support-ticket): mail threading, label rendering, orchid menu collisions

- Auto Message-ID on first send; persist to outbound_message_id + mail_thread_id
- ContactController accepts parent_ticket_id → child reply threaded via SupportTicketReply
- Resolve labels (content_type, appeal_reason, appeal_type, legal_checks) at submit
- Mail templates render form section headings with text labels (no raw indices)
- Fix policy_contact blade: add name/required to first_name, last_name, phone inputs
- Fix SupportTicketMail/Reply Reply-To header via ->replyTo()
- Fix Orchid menu Profile name collision with lang key (Array to string)
- SupportTicket model: add AsSource trait for Orchid TD compat
- TD::make('actions', ...) field name fix
- Add 'Personal profile' rename to avoid lang.profile array
- forwardToLegal mail goes to legal mailbox (internal-only, no appeal link)
- .gitignore: AI tooling artifacts (.claude, .gitnexus, .playwright-mcp, CLAUDE.md, AGENTS.md)

Refs: plan-2026-06-fix-support-ticket / T7-W2

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Properties this example demonstrates: subject names the area + 3 themes; bullets group by subsystem (mail → blade → orchid → ignore); each bullet names the exact class/method/blade/field; no paraphrase of code; no fluff.

The pull request that carries these commits uses `templates/pr/PR-template.md`.
