# agent-hub maintainer rules

This repo builds the `agent-hub` Claude Code plugin. These rules are for maintainers; the shipped plugin does not carry this file.

## Before a release

1. Run `python3 tools/check.py ruleset`. It runs `tools/check-ruleset.sh` over `plugins/agent-hub`. Windows maintainers need bash for this mode (Git Bash or WSL).
2. Run `python3 tools/scrub_check.py --require-private`. It must report 0 findings: no personal paths, no decision citations, no non-English text left in shipped files. Never commit the private pattern file it reads.
3. Package with `python3 tools/package.py`. It validates the tree first; `--no-validate` is for debugging only, never for a release.

## Working rules

- Edit shipped rules under `plugins/agent-hub/`; `tools/` holds maintainer scripts and is not shipped.
- Rules, agents, skills and commands are written in English.
- `/retro` in `.claude/commands/` is repo-only: it is not part of the plugin.
- Stay on the `build` branch locally; no push without the maintainer's say-so.
