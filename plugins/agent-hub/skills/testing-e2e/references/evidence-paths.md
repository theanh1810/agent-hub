# Evidence paths (HARD)

`agents/test.md` § Evidence storage is the only tree: the `.cm-tmp/{task_id}/` layout, file-name shapes, the closed `{viewport}` list, the baseline path. Read it before writing a file; a second variant is a defect.

- Everything a run produces is ephemeral under `{workspace_root}/.cm-tmp/{task_id}/` (`CLAUDE.md` §19.0): nothing under `docs/changes/**`, nothing at a sub-repo root. The `docs/qa/` tree is retired; `CLAUDE.md` §19.1 lists every writable path.

Playwright invoked directly is pointed at the same place, never its defaults; run it with cwd at `{workspace_root}`:

```js
// playwright.config.ts
outputDir: `.cm-tmp/${process.env.TASK_ID}/playwright`,
reporter: [["html", { outputFolder: `.cm-tmp/${process.env.TASK_ID}/playwright/report`, open: "never" }]],
use: {
  screenshot: "only-on-failure",   // never "on"
  video: "retain-on-failure",
  trace: "retain-on-failure",
}
```

# Cleanup (HARD — every invocation)

Rules: `agents/test.md` § Evidence storage; this is the order and the field each step fills.

1. Copy out at most 3 artefacts a finding cites → `evidence_kept[]`.
2. Promote a baseline only from a green run, and say so → `baselines_promoted[]`.
3. Delete `{workspace_root}/.cm-tmp/{task_id}` → `cleanup_done`, only once every case has a result; on `in_progress` skip steps 1-3 and 5-6 and keep the tree (`refs/roles/test/resume.md`).
4. `git status --short` in **each repo the run executed in** (a non-git workspace root checks nothing). Remove or ignore each `??` this run created; first check every filename for `$`, `{` or `}`: delete, fix the command, write again.
5. Scan for earlier orphans at the repo root and in `fe/` `be/` `src/`: `*.png` matching `screenshot*|test-*|snapshot-*`, `network-requests*`, `console-messages*`, `all-requests.txt`, `playwright-report/`, `test-results/`. Report in `orphan_artifacts[]`; **delete only what this run created**.
6. `.gitignore` gets the single `.cm-tmp/` line, only in a repo whose working tree would show the directory (`CLAUDE.md` §19.2). `playwright-report/` and `test-results/` need no entry: the config redirects them. Missing → append and note it in `Risk`.
7. Close pages, shut down simulators, clear `flow_context`, drop temp fixtures → `session_closed`.
8. Report `cleanup: deleted N temp files, kept M at <path>`.

# Closeout

Scan secrets in the evidence before deleting it (`agents/test.md` § Evidence storage, Scan row). Save only flake patterns, environment quirks and API-shape drift to mem0, nothing visual; a baseline is a file, and its path and promote-on-green rule are owned by § Evidence storage.
