#!/usr/bin/env bash
# gate.sh: the one command that says "done" for this repo. Copy to scripts/gate.sh and fill the EDIT lines.
# It runs the commands CI runs, in CI's order, with the tool versions CI pins; a step CI has and this file lacks is a bug here.
# Usage: bash scripts/gate.sh        (log: $GATE_LOG, default .cm-tmp/gate.log)
# Exit codes: 0 every step passed · 1 a step failed or no step is defined (the last FAIL line says which)
#             · 2 a local tool version differs from the CI pin.
set -u
cd "$(dirname "$0")/.." || exit 1
LOG="${GATE_LOG:-.cm-tmp/gate.log}"
mkdir -p "$(dirname "$LOG")" && : > "$LOG"
STEPS=0

pin() {   # pin <label> <version CI pins> <command printing the local version>
  # The first dotted number of the output is compared part by part from the major on:
  # pin 20 accepts v20.11.0 and rejects v18.20.1; pin 1.75.0 accepts only 1.75.0.
  local label="$1" want="$2" got ver
  shift 2
  got="$("$@" 2>&1 | head -n 1)"
  ver="$(printf '%s\n' "$got" | grep -oE '[0-9]+(\.[0-9]+)*' | head -n 1)"
  case "$ver" in
    "$want"|"$want".*) echo "pin  $label $want" ;;
    *) echo "FAIL pin $label: CI pins $want, local is: $got"; exit 2 ;;
  esac
}

step() {  # step <name> <command...>: output goes to the log, one verdict line is printed
  local name="$1" start=$SECONDS rc
  shift
  STEPS=$((STEPS + 1))
  { echo "=== $name: $*"; "$@"; } >> "$LOG" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then echo "ok   $name ($((SECONDS - start))s)"; return 0; fi
  echo "FAIL $name (exit $rc), last lines of $LOG:"
  tail -n 30 "$LOG"
  exit 1
}

step_opt() {  # step_opt <name> <tool> <command...>: as step, but with <tool> not installed one SKIP line is printed and logged and the gate goes on
  local name="$1" tool="$2"
  shift 2
  if ! command -v "$tool" > /dev/null 2>&1; then
    echo "SKIP $name: $tool not installed" | tee -a "$LOG"
    return 0
  fi
  step "$name" "$@"
}

# EDIT: one pin per version the CI file fixes (toolchain, package manager, linter). Examples:
# pin rust 1.75.0 rustc --version
# pin pnpm 9.12.0 pnpm --version

# EDIT: one step per CI command, in CI's order, with CI's flags.
# Fast deterministic checks first: pins, format, lint, type check, path scan, then tests.
# Time budget: the steps before tests finish within 120 s on a change of up to 6 files. The 120 s is a
# starting number, unmeasured; the seconds each `ok` line prints are its measurement.
# `paths` scans the changed source paths only, never the tree. A SKIP line is not a failure.
# The rule folder is copied from the plugin's templates/gate/semgrep/ into this repo next to this script. Examples:
# step fmt   cargo fmt --all -- --check
# step lint  cargo clippy --all-targets -- -D warnings
# step types pnpm exec tsc --noEmit
# `paths`: changed and untracked source files against the merge base with the target branch (EDIT origin/main),
# the rule folder and its fixtures excluded; no such file runs no `paths` step, and no semgrep prints its SKIP line. A path holding a space is not supported.
# SRC=('*.py' '*.js' '*.jsx' '*.ts' '*.tsx' ':(exclude)scripts/semgrep')
# if ! command -v semgrep > /dev/null 2>&1; then step_opt paths semgrep; else
#   PATHS_BASE=$(git merge-base HEAD origin/main) || { echo "FAIL paths: no merge base with origin/main"; exit 1; }
#   CHANGED=$({ git diff --name-only --diff-filter=d "$PATHS_BASE" -- "${SRC[@]}"; git ls-files --others --exclude-standard -- "${SRC[@]}"; } | sort -u)
#   if [ -n "$CHANGED" ]; then step paths semgrep scan --metrics off --error --config scripts/semgrep $CHANGED; fi
# fi
# step test  pnpm test

if [ "$STEPS" -eq 0 ]; then echo "FAIL gate has no step: fill the EDIT lines from the CI file"; exit 1; fi
echo "gate: $STEPS steps passed"
