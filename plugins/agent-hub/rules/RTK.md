# RTK - Rust Token Killer

Token-optimized CLI proxy (60-90% savings). A hook rewrites verbose commands automatically (`git status` → `rtk git status`).

## Meta Commands (always use rtk directly)

```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze Claude Code history for missed opportunities
rtk run -c '<cmd>'    # Raw, no filtering; rtk proxy is denied (settings.json:43)
```

## Installation Verification

`rtk --version`, `rtk gain` (must not say "command not found"), `which rtk`. **Name collision**: if `rtk gain` fails, `reachingforthejack/rtk` (Rust Type Kit) may be installed instead.

## Hook-Based Usage

### What is NOT rewritten, and why (config: `~/Library/Application Support/rtk/config.toml`)

`[hooks] exclude_commands` holds `grep`, `rg`, `cat`, `head`, `tail`, `find`, `ls`. Unexcluded they become `rtk grep` / `rtk read`, which **summarise**, and a summary changes conclusions (measured 2026-08-30: `grep '^## '` returned 25 of 37 matches with a `+12 more` footer; `head -40` on a JSON file looked malformed and was reported as a syntax error that did not exist). `[limits]` raised: `grep_max_results` 200 → 1000, `grep_max_per_file` 25 → 200, `passthrough_max_chars` 2000 → 8000.

**`head` and `tail` are still rewritten** (a rule ignoring `exclude_commands`; observed on `rtk 0.37.2`, 2026-09-01, the version claim unverified). For a faithful read use `sed -n '1,40p' <file>`, which the hook leaves alone.

Verbose build/test/log commands (`git`, `npm`, `tsc`, `jest`, `vitest`, `eslint`, `docker`, `kubectl`, `curl`) are still rewritten; their error does **not** reliably survive (§ Diagnosing a failure).

## Commands that exit 0 with a wrong result (HARD)

The hook's most dangerous failure is **exit 0 and a plausible wrong answer** (a count, a size, a diff nobody questions). Every case below was reproduced; one that was not is marked.

### `git diff` is unreliable under this hook (HARD — measured 2026-09-01)

Two failures, **only one of which looks like a failure**:

| Command shape | What happens | Real content |
|---|---|---|
| `git diff <A>..<B>` — no pathspec | **empty output, exit 0** | 4663 bytes, 127 lines, 3 files |
| `git diff --cached <A>` | renders, but **silently drops lines** | 18 lines of a 9429-char diff cut |
| `git diff <A>..<B> -- path/file` | correct | correct |

It fails only on the broad call, the one `reviewer mode=merge` depends on. **Before judging any diff, confirm you see all of it**: compare a byte count taken outside the hook with what you were shown, or read with `sed -n '1,200p'`.

```bash
node -e 'console.log(require("child_process").execFileSync("git",["diff","<A>..<B>"],{encoding:"utf8"}).length)'
```

Read the whole diff before passing it: a reviewer that passes a diff it never fully read has not reviewed it.

### Other shapes measured to exit 0 with a wrong result (measured 2026-09-07, `implement` W6-T15)

| Command shape | Wrong result | Real value | Replacement, run once |
|---|---|---|---|
| `diff a.txt b.txt` | `[ok] Files are identical`, exit 0 | the two files differ by 1 line / 8 bytes | `python3` + `difflib.unified_diff` |
| `wc -c < file` · `wc -l < file` | `0`, exit 0 | whatever the file really is at read time; measure it, never trust a figure written here | `wc -l <file>` (filename form), or `python3` + `os.path.getsize(p)` and `len(open(p).read().splitlines())` |
| `LC_ALL=C grep -c '[^[:print:][:space:]]' file` | `0` | 2 non-ASCII chars in a 37-byte fixture; 88 in `skills/review-checklist/SKILL.md` | `python3` + `sum(1 for c in t if ord(c)>127)` |
| `grep -c <pat> <file>` meant for one section | `5`, plausible but a different question | `4` inside the section | `sed -n '/^## A/,/^## B/p' file \| grep -c <pat>` |

**`wc` fails only on the `<` redirect** (re-confirmed 2026-09-08/09): `wc -l <file>` and `cat <file> | wc -c` are right; the redirect returns `0`. **The mechanism is nesting**: the hook sees only the top-level command string, so a command inside `$( )`, a loop or a `{ }` block runs unwrapped and can answer correctly while the same bare command returns `0`. Measure bare, one command per tool call. The tell: the redirect's `0` carries no padding, `cat file | wc -c` keeps BSD `wc`'s leading spaces. Never pass a file to `wc` through `<`.

**`grep` cannot count non-ASCII here**: both the POSIX class and `[\x80-\xff]` return `0` on a file where `grep -c 'review'` returns `29`; count in Python. **A whole-file `grep -c` gives no hint it answered the wrong question**: scope with `sed -n '/start/,/end/p'` first (twelve `verification` commands in one plan were wrong this way).

**Not reproduced (2026-09-07)**: a glob from the wrong cwd plus `2>/dev/null` returning 0 results silently (zsh `nomatch` prints and exits 1; `grep -c <pat> missing-file 2>/dev/null` prints nothing but exits **2**).

## Search commands (HARD)

- **Quote every glob** given to `grep` and `find` (`--include='*.md'`, `-name '*.md'`): unquoted, zsh expands it first, prints `no matches found`, and `grep` never runs.
- **An exit 1 is not proof of "no match"** when the command could have errored: zsh `nomatch` also exits 1 before `grep` runs. Read stderr first.
- **Prefer the Grep and Glob tools** where the session provides them; this harness's agent tool set does not (2026-09-24), so Bash search follows these rules.
- **Scope every recursive search.** Never search recursively from `~/.claude` or a repo root without a path or glob; exclude transcripts, `node_modules` and `.git` in the command (`--exclude='*.jsonl'`). A path glob such as `--exclude='projects/**/*.jsonl'` excludes nothing, and filtering output afterwards still reads them. `--exclude-dir=projects` also hides `projects/*/memory/`; use it only when memory is out of scope.
- **Quote any word that starts with `=`; never start one unquoted** under zsh: `=cmd` expands to the path of `cmd`, so `echo ====` fails with `(eval):1: === not found`. Write `echo '===='`.

## Diagnosing a failure (HARD)

- **Output you will diagnose (first error, exit code, traceback) is read raw.** Run `RTK_DISABLED=1 <cmd> > .cm-tmp/{task_id}/<name>.log 2>&1` or `rtk run -c '<cmd>' > .cm-tmp/{task_id}/<name>.log 2>&1`: both were byte-identical to the unfiltered run and passed the exit through (measured: 2; 3, 3, 128, 1). Not measured: a signal exit, a command rtk fails to spawn. Take the first error line with `grep -n` or `sed -n`, and the exit from the same call.
- **These do not escape the filter**: `> file 2>&1` stores the cut output, footer included, and `| tail` receives the already-cut head. `rtk proxy` would, but `settings.json:43` denies it. A footer's tee file holds stdout only.
- **A filter can change the error without a footer**: `rtk npm` moves stderr after all stdout, and `python3 -m pytest` becomes `rtk pytest`, which printed `rtk: Failed to run pytest: Failed to spawn process…` instead of `No module named pytest`.
- **Unmeasured is not safe**: jest, vitest, tsc, cargo, a real pytest failure, docker, kubectl, curl were not tested; read their failures raw.
- **`[N characters truncated]` is the Bash tool's own cap, not rtk**, and no rtk setting reaches it: write the output to a file and read it in chunks with `sed -n`.

| Rationalization | Reality |
|---|---|
| "The diff came back empty, so nothing changed" | Empty with exit 0 is a known failure of `git diff <A>..<B>`; compare byte counts first |
| "The count is 0, so none exist" | `wc` through `<` and `grep` over non-ASCII answer `0` wrongly; measure another way |
| "The filtered log shows no error" | The filter may have cut it; read the raw file |
