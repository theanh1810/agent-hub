# Manual how-to runbooks

Load when a step only a person can do is needed: granting permissions, CI secrets, a cut-over.

User decision 50: these runbooks live in devops. A runbook is a guide script, not an automation.

1. Read the repo first to know, per value, where it comes from, where it goes, and whether it is a secret.
2. Open the exact URL, then ask for the value. Take secrets as hidden input.
3. Ask for `confirm` before any irreversible step.
4. Never run the whole script yourself; check it statically only (syntax, the values it names, the URLs it opens).
5. Ask for approval again at each step: an approval for one step never carries to the next (`needs_approval`, `CLAUDE.md` §2.1A).
