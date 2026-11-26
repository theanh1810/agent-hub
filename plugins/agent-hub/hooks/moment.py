#!/usr/bin/env python3
"""moment.py <PreToolUse|PostToolUse|PostToolUseFailure|SessionStart>: deliver a rule at the moment it applies.

Reads hooks/moments.json. Each moment fires once per spawn and injects one or more rule slices
(scripts/rule-slice.py) or a one-line note as additionalContext.

Two points may refuse a call, for an agent-hub:implement spawn only, each at most `max_blocks` times per spawn,
after which the call goes through with a warning (a systemMessage for the user, one line for the model):
  baseline  a write to a code file before a test runner finished in this spawn. A runner counts as the command
            word of a shell segment (`runners.runs_tests`), not as text, and only a test run: lint, build, type
            check, `agent-hub check`, `--version` and `--collect-only` calls do not open it. One that never ran (the
            shell's own `command not found` for the runner, a launch failure, exit 126/127 with no test summary) does
            not count; a red run does. A spawn that read `.cm-tmp/*/progress.yaml` (the Read tool, or `cat`, `head`,
            `less`, `sed -n` of it: a resume from a ceiling stop) or invoked the `simplify` skill is exempt: it gets
            the text once as a note.
  commit    `git commit` whose message has no `Refs:` line (a message built by the shell is unread, not missing)
AGENT_HUB_BLOCKS=0 or plugin option hook_blocks=off turns both into notes; AGENT_HUB_MOMENTS=0 or plugin
option moment_hooks=off turns this hook off.

A moment with role `*` reaches the main thread and every `agent-hub:` agent, not another plugin's subagent.
A subagent's own compaction does not re-arm its notes: only SessionStart(compact) of the main thread advances
the generation, so a subagent that compacts mid-spawn is not told a second time.
Shell writes are seen from the command text only (redirects, tee, sed -i, a python or node heredoc's write call);
a write a script makes by other means is not.

Every fact is a marker file of hooks/_state.py (claim, claimed, claim_once, take_block), never a load-then-save:
the hooks of parallel tool calls run at once, and a marker, made by one O_EXCL create, cannot be lost to a
concurrent writer. A PreToolUse hook also fires for a call that permissions then deny, so PreToolUse makes only
"this note was delivered" and "this call was refused". What needs the call to have run (a test command
finished, a write happened, the call number) is made on PostToolUse and PostToolUseFailure.

Always exits 0. A refusal is a `permissionDecision: deny` envelope on stdout. Any failure ends with no output,
so a fault here never blocks or changes a call.
"""
import importlib.util
import json
import os
import re
import sys

if sys.version_info < (3, 11):  # the doctor hook reports it; stay silent here
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common  # noqa: E402
import _state  # noqa: E402
import git_guard  # noqa: E402
import runners  # noqa: E402

CODE = r"\.(?:tsx?|mts|cts|jsx?|mjs|cjs|py|rs|go|java|rb|php|sh|css|scss|vue|svelte|swift|kt|c|cpp|h|html|sql)$"
BASELINE_CODE = r"\.(?:tsx?|mts|cts|jsx?|mjs|cjs|py|rs|go|java|rb|php|sh|vue|svelte|swift|kt|c|cpp|h)$"   # CODE minus what no recognised runner tests
UI = r"\.(?:tsx|jsx|vue|svelte|css|scss|html)$"
NAMED = {"CODE": CODE, "UI": UI}
TEMPORARY = re.compile(r"(?:^|/)(?:tmp|\.cm-tmp|scratchpad|claude-backups)/|^/var/folders/|^/private/|\$\{?TMP")
PROGRESS = re.compile(r"(?:^|/)\.cm-tmp/[^/]+/progress\.yaml$")
QUOTED_HEREDOC = re.compile(r"\$\(\s*cat\s+<<-?\s*(['\"])\w+\1")
WEB_TOOL = re.compile(r"WebSearch|WebFetch|mcp__kindly|mcp__plugin_context7")
WRITE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
MESSAGE_ELSEWHERE = {"-F", "--file", "-C", "-c", "--reuse-message", "--reedit-message", "--fixup", "--squash", "-t", "--template", "--no-edit"}
REFS_LINE = re.compile(r"(?m)^\s*Refs:[ \t]*\S")
MAX_GENERATIONS = 64   # compactions counted per spawn; past it the main thread's notes stop re-arming

BASELINE_REFUSAL = ("agent-hub: this spawn has not run the baseline tests yet. `agents/implement.md` Workflow step 5: run `git status --porcelain`, "
                    "then the project's tests, before the first edit; a red baseline is `needs_user_input` quoting the first failure.")
COMMIT_REFUSAL = ("agent-hub: this commit message has no `Refs:` line. End the message with `Refs: <change> / <task_id>` on its own line, "
                  "then the `Co-Authored-By:` line (`refs/roles/implement/close-task.md § Commit`), and commit again.")
BASELINE_WARNING = "agent-hub: an implement spawn edited code with no baseline test run (refused %d times, then let through)."
COMMIT_WARNING = "agent-hub: an implement spawn committed with no `Refs:` line (refused %d times, then let through)."
BASELINE_RISK = "agent-hub: this code edit went through without the baseline test run; state that under `## Risks` of your return."
COMMIT_RISK = "agent-hub: this commit went through with no `Refs:` line; state that under `## Risks` of your return."

def load_config():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "moments.json"), encoding="utf-8") as handle:
        return json.load(handle)


def load_slicer():
    spec = importlib.util.spec_from_file_location("rule_slice", _common.plugin_root() / "scripts" / "rule-slice.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bash_write_targets(command):
    """Paths a shell command writes, as far as its text shows: redirects, tee, sed -i, and a python heredoc's open(..., 'w') or write_text."""
    shell, targets = command, []
    for found in HEREDOC.finditer(command):
        head = command[command.rfind("\n", 0, found.start()) + 1:found.start()]
        body = found.group(3)
        if re.search(r"\b(?:python3?|node)\b", head):
            targets += re.findall(r"open\(\s*[rf]?['\"]([^'\"]+)['\"]\s*,\s*['\"][wa]b?\+?['\"]", body)
            targets += re.findall(r"Path\(\s*[rf]?['\"]([^'\"]+)['\"]\s*\)\.write_(?:text|bytes)\(", body)
            targets += re.findall(r"writeFileSync\(\s*['\"]([^'\"]+)['\"]", body)
        shell = shell[:found.start(3)] + " " * len(body) + shell[found.end(3):]
    quoted = [(q.start(), q.end()) for q in re.finditer(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"", shell)]
    for found in re.finditer(r"(?<![0-9&>=-])>>?\s*([^\s&|;<>()]+)", shell):
        if not any(a < found.start() < b for a, b in quoted):
            targets.append(found.group(1))
    targets += re.findall(r"\btee\s+(?:-a\s+)?([^\s|;&]+)", shell)
    targets += re.findall(r"\bsed\s+(?:-[a-zA-Z]*\s+)*-i[^\n|;&]*?([^\s|;&]+)\s*(?=$|\n|;|&&|\|)", shell)
    return [t.strip("\"'") for t in targets if t.strip("\"'") not in ("/dev/null", "/dev/stderr", "/dev/stdout") and not t.startswith("&")]


def git_calls(command, depth=0):
    """[(subcommand, arguments after it)] for each real git invocation: quoted text, heredoc bodies and comments are not commands."""
    lines, substitutions = git_guard.split_lines(command)
    calls = []
    if depth < 3:
        for inner in substitutions:
            calls += git_calls(inner, depth + 1)
    for line in lines:
        for segment in git_guard.segments(line):
            at = 0
            while at < len(segment) and (re.fullmatch(r"\w+=.*", segment[at]) or segment[at] in git_guard.WRAP):
                at += 1
            if at >= len(segment) or os.path.basename(segment[at]) != "git":
                continue
            args, i = segment[at + 1:], 0
            while i < len(args) and args[i].startswith("-"):
                i += 2 if args[i] in git_guard.GOPT_ARG else 1
            if i < len(args):
                calls.append((args[i], args[i + 1:]))
    return calls




def shell_expands(command):
    """True when the command text has a `$name`, `${`, `$(` or backtick outside single quotes: a value built by the shell."""
    quote, at = None, 0
    while at < len(command):
        char = command[at]
        if quote == "'":
            quote = None if char == "'" else quote
        elif char == "\\":
            at += 1
        elif char == "`" or (char == "$" and re.match(r"[\w({]", command[at + 1:at + 2] or " ")):
            return True
        elif char in "'\"":
            quote = None if quote == char else (quote or char)
        at += 1
    return False


def single_quoted(message, command):
    """True when the command passes this message as a `-m`/`--message` value in single quotes: the text itself, whatever else the command does with `$`."""
    return bool(re.search(r"(?:-[a-zA-Z]*m\s*|--message[=\s]\s*)'" + re.escape(message) + "'", command))


def commit_state(command):
    """None when the command makes no commit; else 'refs', 'no-refs', or 'unread' when the message is not in the command
    (`-F`, no `-m`, or a `-m` value the shell builds: `$MSG`, `$(cat f)`, a backtick). A quoted-heredoc `$(cat <<'EOF'` and a value
    the command single-quotes are the text itself, whatever else the command expands."""
    verdict = None
    for subcommand, args in git_calls(command):
        if subcommand != "commit":
            continue
        messages, i = [], 0
        while i < len(args):
            arg = args[i]
            if arg in MESSAGE_ELSEWHERE or arg.startswith(("--file=", "--fixup=", "--squash=", "--reuse-message=", "--template=")):
                return "unread"
            if arg.startswith("--message="):
                messages.append(arg.split("=", 1)[1])
            elif (arg == "--message" or re.fullmatch(r"-[a-zA-Z]*m", arg)) and i + 1 < len(args):
                messages.append(args[i + 1])
                i += 1
            i += 1
        built = [m for m in messages if re.search(r"[$`]", m) and not QUOTED_HEREDOC.match(m) and not single_quoted(m, command)]
        if not messages or (built and shell_expands(command)):
            return "unread"
        verdict = "refs" if REFS_LINE.search("\n\n".join(messages)) and verdict != "no-refs" else "no-refs"
    return verdict


def is_temporary(path):
    return bool(TEMPORARY.search(path))


def targets_of(payload):
    """Paths the call writes (write tools and shell writes), temporary paths left out."""
    tool, tool_input = payload.get("tool_name"), payload.get("tool_input") or {}
    if tool in WRITE_TOOLS:
        found = [tool_input.get("file_path") or tool_input.get("notebook_path") or ""]
    elif tool == "Bash":
        found = bash_write_targets(tool_input.get("command") or "")
    else:
        found = []
    return [p for p in found if isinstance(p, str) and p and not is_temporary(p)]


def touched_text(payload):
    """Every path or command text of the call, for a `touch` moment."""
    tool_input = payload.get("tool_input") or {}
    return " ".join(str(tool_input.get(k) or "") for k in ("file_path", "path", "command", "pattern"))


def role_matches(moment, role):
    roles = moment.get("roles") or []
    return ("*" in roles and bool(role)) or role in roles


def pattern_of(moment, key="match"):
    raw = moment.get(key)
    return re.compile(NAMED.get(raw, raw)) if raw else None


def call_number(payload, last):
    """The number of the call this event closes, 1-based: the lowest `call-<n>` marker this process wins, so two
    concurrent hooks never share a number. None past `last`, where counting stops."""
    for number in range(1, last + 1):
        if _state.claim(payload, "call-%d" % number):
            return number
    return None


def generation(payload):
    """How many compactions this spawn has had; a moment's marker carries it, so a compaction re-arms every note."""
    count = 0
    while count < MAX_GENERATIONS and _state.claimed(payload, "compact-%d" % count):
        count += 1
    return count


def applies(moment, event, payload, role, facts):
    """True when the moment's trigger holds for this call."""
    kind, tool = moment.get("on"), payload.get("tool_name")
    if not role_matches(moment, role):
        return False
    match, excluded = pattern_of(moment), pattern_of(moment, "not_match")
    command = (payload.get("tool_input") or {}).get("command") or ""
    if event == "PreToolUse":
        if kind == "write":
            paths = facts["targets"]
            if moment.get("match") == "DOC":
                paths = [p for p in paths if not re.search(CODE, p)]
                return bool(paths)
            return any(match.search(p) and not (excluded and excluded.search(p)) for p in paths)
        if kind == "touch":
            return bool(match.search(touched_text(payload)))
        if kind == "bash":
            return tool == "Bash" and bool(match.search(command))
        if kind == "commit":
            return tool == "Bash" and facts["commit"] is not None
        if kind == "web":
            return bool(WEB_TOOL.match(tool or ""))
        return False
    if kind == "calls":
        return facts["call"] is not None and facts["call"] == moment.get("at")
    if kind == "fail" and event == "PostToolUseFailure" and tool == "Bash":
        if moment.get("after_write") and not facts["wrote"]:
            return False
        return not moment.get("match") or bool(runners.runs_checks(command) if moment["match"] == "TEST" else match.search(command))   # broad on purpose: a lint or build failure after an edit is red too
    return False


def render(moment, slicer):
    """The text a moment injects: its slices, each under a `[file § heading]` line, then its note. '' when a slice is missing."""
    parts = []
    for spec in moment.get("slices") or []:
        try:
            body = slicer.slice_text(str(_common.plugin_root()), spec)
        except Exception:
            return ""
        parts.append("[%s]\n%s" % (spec.replace("#", " § "), body))
    if moment.get("note"):
        parts.append(moment["note"] + "\n")
    return "\n".join(parts)


def deny(reason):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                         "permissionDecisionReason": reason}}, ensure_ascii=False) + "\n")


def reads_progress(command):
    """True when a shell segment of `command` is `cat`, `head`, `less` or `sed -n` of a `.cm-tmp/<task>/progress.yaml`."""
    lines, _ = git_guard.split_lines(command)
    for line in lines:
        for words in git_guard.segments(line):
            words = runners.unwrap(words)
            name = os.path.basename(words[0]) if words else ""
            if name in ("cat", "head", "less") or (name == "sed" and "-n" in words):
                if any(PROGRESS.search(w) for w in words[1:]):
                    return True
    return False


def exempting(payload):
    """True when this call marks the spawn as continuing or simplifying, which has no baseline run of its own: a Read of
    `.cm-tmp/<task>/progress.yaml`, by the tool or by `cat` (resume from a ceiling stop, `refs/turn-budget.md`), or the `simplify` skill."""
    tool, tool_input = payload.get("tool_name"), payload.get("tool_input") or {}
    if tool == "Read":
        return bool(PROGRESS.search(str(tool_input.get("file_path") or "")))
    if tool == "Bash":
        return reads_progress(str(tool_input.get("command") or ""))
    return tool == "Skill" and bool(re.fullmatch(r"(?:[\w.-]+:)?simplify", str(tool_input.get("skill") or "")))


def refusal(payload, role, facts, limit):
    """(reason, note, warned). A reason refuses the call; a note is text delivered once instead (blocks off, or an exempt
    spawn); `warned` is (systemMessage, model line) once the limit is spent. Implement spawns only."""
    if role != "implement":
        return None, None, None
    checks = []
    if any(re.search(BASELINE_CODE, p) for p in facts["targets"]) and not _state.claimed(payload, "tests-ran"):
        checks.append(("baseline", BASELINE_REFUSAL + " Then repeat this call.", BASELINE_WARNING, BASELINE_RISK))
    if facts["commit"] == "no-refs":
        checks.append(("commit", COMMIT_REFUSAL, COMMIT_WARNING, COMMIT_RISK))
    for point, reason, warning, risk in checks:
        if _state.blocks_off() or (point == "baseline" and _state.claimed(payload, "exempt")):
            return None, (reason.replace(" Then repeat this call.", "") if _state.claim_once(payload, "note-" + point) else None), None
        if _state.take_block(payload, point, limit):
            return reason, None, None
        if _state.claim_once(payload, "warned-" + point):
            return None, None, (warning % limit, risk)
    return None, None, None


def main(argv):
    event = argv[0] if argv else ""
    payload = _common.read_stdin_json()
    if event not in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "SessionStart") or _state.switched_off():
        return
    if event == "SessionStart":   # after a compaction the earlier notes are summarised away: a new generation lets them fire again
        if payload.get("source", "compact") == "compact":
            for count in range(MAX_GENERATIONS):
                if _state.claim(payload, "compact-%d" % count):
                    break
        return
    role = _state.agent_role(payload)
    config = load_config()
    limits, moments = config.get("limits") or {}, config.get("moments") or []
    tool, command = payload.get("tool_name"), (payload.get("tool_input") or {}).get("command") or ""
    facts = {"targets": targets_of(payload), "commit": commit_state(command) if tool == "Bash" else None, "call": None, "wrote": False}
    note = warned = None
    if event == "PreToolUse":
        reason, note, warned = refusal(payload, role, facts, int(limits.get("max_blocks", 2)))
        if reason:
            deny(reason)
            return
    else:
        last = max([int(m.get("at") or 0) for m in moments if m.get("on") == "calls" and role_matches(m, role)] or [0])
        facts["call"] = call_number(payload, last) if last else None
        if tool == "Bash" and runners.runs_tests(command) and not runners.never_ran(payload):
            _state.claim(payload, "tests-ran")
        if event == "PostToolUse" and exempting(payload):
            _state.claim(payload, "exempt")
        if event == "PostToolUse" and facts["targets"]:
            _state.claim(payload, "wrote")
        facts["wrote"] = event == "PostToolUseFailure" and _state.claimed(payload, "wrote")
    budget, texts, slicer, era = int(limits.get("max_chars", 9500)), [], None, None
    for line in (note, warned and warned[1]):
        if line:
            texts.append(line + "\n")
            budget -= len(line)
    for moment in moments:
        key = moment.get("id")
        if not key or not applies(moment, event, payload, role, facts):
            continue
        era = generation(payload) if era is None else era
        marker = "moment-%s-%d" % (key, era)
        if _state.claimed(payload, marker):
            continue
        slicer = slicer or load_slicer()
        text = render(moment, slicer)
        if not text or len(text) > budget:
            continue   # too long for what is left of this call: no marker, so it goes out on the next matching call
        if not _state.claim(payload, marker):
            continue   # a concurrent hook of this spawn delivered it first
        budget -= len(text)
        texts.append(text)
    if texts or warned:
        _common.emit(event, "\n".join(texts) if texts else None, warned and warned[0])
        sys.stdout.flush()
    try:
        _state.prune_sometimes()   # after the output: nothing it raises may cost it
    except Exception:
        pass


if __name__ == "__main__":
    _common.utf8_stdio()
    try:
        main(sys.argv[1:])
    except Exception:
        pass  # a fault here must leave the call untouched
    sys.exit(0)
