# agent-hub maintainer rules

This repo builds the `agent-hub` Claude Code plugin and its three optional plugins (`agent-hub-auditor`, `agent-hub-integrations`, `agent-hub-local-services`). These rules are for maintainers; the shipped plugins do not carry this file.

## Design in one paragraph

Seven agents: brainstorm, scout, designer, implement, reviewer, test, devops. The main thread routes by the lane table in `plugins/agent-hub/rules/core.md § Routing` (lanes in `plugins/agent-hub/refs/lanes.md`); no agent routes, plans or varies by effort; effort is set per spawn (`refs/effort-routing.md`). The first section of the core states the four principles. A plan is an OpenSpec change folder written by brainstorm plus a detailed Vietnamese plan document, checked by machine only (`agent-hub check plan`). A run ends with one reviewer pass; second opinions follow `refs/roles/reviewer/second-opinion.md`. A vetted text-only skill store lives in `plugins/agent-hub/store/` (`agent-hub store match`). The memory store is claude-mem. Third-party text is carried verbatim with attribution: `THIRD_PARTY_NOTICES.md`, `tools/upstream/manifest.yaml`, check `quoted_passages_attributed`.

## Before a release

1. Run `python3 tools/check.py ruleset` (or `bash tools/check-ruleset.sh`). It checks the tree under `plugins/agent-hub`. Windows maintainers need bash for this mode (Git Bash or WSL).
2. Run the unit tests, one directory at a time: `python3 -B -I -m unittest discover -s tests/<dir> -p 'test_*.py'` for `auditor`, `hooks`, `local-services`, `scripts` and `tools`.
3. Run `python3 tools/scrub_check.py --require-private`. It must report 0 findings: no personal paths, no decision citations, no non-English text left in shipped files. Never commit the private pattern file it reads.
4. Package with `python3 tools/package.py`. It validates the tree first; `--no-validate` is for debugging only, never for a release.

## Working rules

- Edit shipped rules under `plugins/`; `tools/` and `tests/` hold maintainer scripts and are not shipped.
- `tools/v2-manifest.tsv` lists every tracked path; the check `tree_matches_manifest` keeps the tree and the manifest equal.
- Rules, agents, skills and commands are written in English.
- Quoted third-party text changes only through `tools/upstream/` (pinned copy and manifest entry), never by hand.
- No push, no marketplace update and no install of a third-party tool (OpenSpec, qa-pilot, kindly, pr-review-toolkit) without the maintainer's say-so.
