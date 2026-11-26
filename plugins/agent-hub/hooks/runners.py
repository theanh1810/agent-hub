#!/usr/bin/env python3
"""runners.py: is this shell command a test run, and did it run at all? Pure functions, no state, no I/O.

`runs_tests(command)` is true when a real shell segment of the command (quoted text, heredoc bodies and comments are not
segments) has a test runner as its command word: the predicate that opens the baseline gate. `runs_checks(command)` is the
broader one, a test run or a lint, type check, build or project checker: a red result of any of them follows an edit.
`never_ran(payload)` reads a Bash hook payload and says the command failed to launch.
Used by moment.py; beside git_guard.py, whose shell splitter it shares.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import git_guard  # noqa: E402

PYTHON = re.compile(r"(?:python|py)\d*(?:\.\d+)*")
SCRIPT = re.compile(r"(?:^|/)(?:test[^/]*\.(?:sh|py)|run[-_]tests?[^/]*|gate\.sh)$")
CHECKER = re.compile(r"(?:^|/)tools/check\.py$")   # a project's own checker: a check, not a test
LAUNCHERS = {"uv": {"run"}, "poetry": {"run"}, "pipenv": {"run"}, "pdm": {"run"}, "hatch": {"run"}, "rye": {"run"}, "bundle": {"exec"},
             "pnpm": {"exec", "dlx"}, "yarn": {"exec", "dlx"}, "npm": {"exec"}, "bun": {"x"}}
VALUE_OPTIONS = {"--with", "-p", "--python", "--directory", "--project", "--package", "-w", "--workspace", "--filter", "-C", "--cwd", "--prefix",
                 "-f", "--file", "--config"}
WRAPPERS = {"timeout": {"-s", "--signal", "-k", "--kill-after"}, "gtimeout": {"-s", "--signal", "-k", "--kill-after"},
            "nice": {"-n", "--adjustment"}, "ionice": {"-c", "-n", "-p", "-P", "-u"}, "stdbuf": {"-i", "-o", "-e"},
            "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}}   # wrapper word -> its options that take a value
DURATION = {"timeout", "gtimeout"}   # these take one positional (the duration) before the command
KEYWORDS = {"if", "then", "elif", "else", "do", "while", "until", "!"}
INERT = {"--version", "-V", "--help", "-h", "--collect-only", "--co", "--list-tests", "--dry-run"}   # asks the runner about itself, runs nothing
DIRECT = {"pytest", "py.test", "pest", "tox", "nox", "phpunit", "rspec", "ctest", "jest", "vitest", "mocha", "bats"}
LINTERS = {"shellcheck", "eslint", "ruff"}   # checks, not tests
TEST_SCRIPT = re.compile(r"test(?:[:-]\w+)*")   # a package script, justfile recipe or task: test, test:unit, test-e2e
CHECK_SCRIPT = re.compile(r"(?:lint|build|typecheck)(?:[:-]\w+)*")
TEST_SCRIPTS = {"t", "tst"}
TEST_SUBCOMMAND = {"deno": "test", "go": "test", "dotnet": "test", "swift": "test", "flutter": "test", "dart": "test", "mix": "test",
                   "bazel": "test", "bazelisk": "test", "hatch": "test"}
GRADLE_TASK = re.compile(r"(?:[\w-]*:)*(?:test|check)")
NX_TARGET = re.compile(r"(?:[\w@./-]+:)?test(?:[:-]\w+)*")

SHELL_PREFIX = r"(?:(?:\(eval\)|[-/\w.]*(?:sh|bash|zsh|dash|ksh))(?::\d+)?: )?(?:(?:line )?\d+: )?"   # `bash: line 3: `, `/bin/sh: 1: `, `zsh: `, `zsh:1: `, `(eval):1: `
LAUNCH_FAILURES = re.compile(
    r"^npm (?:ERR!|error) (?:[Mm]issing script|could not determine executable to run)"
    r"|^\s*ERR_PNPM_NO_SCRIPT\b"
    r"|^error (?:Command \".*\" not found|Couldn't find a script named)"
    r"|^g?make(?:\[\d+\])?: \*\*\* (?:No rule to make target|No targets)"
    r"|^error: could not find `Cargo\.toml`"
    r"|^[-/\w.]*python[\d.]*: can't open file\b", re.M)
SUMMARY = re.compile(r"\b\d+\s+(?:passed|failed|passing|failing|skipped|tests?|specs?|examples?)\b|\bRan \d+ tests?\b|\btest result:"
                     r"|^\s*(?:PASS|FAIL)\s|^OK\b|^ok\s+\S+\s+[\d.]+s|^\u2139 (?:pass|tests) \d+", re.M)


def tail(args):
    """The arguments from the first positional one on: leading options, and the value of a value-taking option, dropped."""
    skip = False
    for at, arg in enumerate(args):
        if skip:
            skip = False
        elif arg.startswith("-"):
            skip = arg in VALUE_OPTIONS
        elif not arg.startswith("+"):
            return args[at:]
    return []


def positional(args):
    """The positional arguments: options, their values and `+toolchain` words dropped."""
    found, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg.startswith("-"):
            skip = arg in VALUE_OPTIONS
        elif not arg.startswith("+"):
            found.append(arg)
    return found


def python_module(args):
    """The module `python -m <module>` runs, or None."""
    for at, arg in enumerate(args):
        if arg == "-m":
            return args[at + 1] if at + 1 < len(args) else None
        if arg.startswith("-m") and len(arg) > 2:
            return arg[2:]
        if not arg.startswith("-"):
            return None
    return None


def python_runs_tests(args):
    for at, arg in enumerate(args):
        if arg == "-m":
            return at + 1 < len(args) and args[at + 1] in ("pytest", "unittest", "tox", "nox")
        if arg.startswith("-m") and arg[2:] in ("pytest", "unittest"):
            return True
        if not arg.startswith("-"):
            return bool(SCRIPT.search(arg))
    return False


def unwrap(words):
    """The command and its arguments with leading `VAR=x`, wrapper words (sudo, timeout 60, nice -n 10, env -i, ...) and
    shell keywords (`if`, `then`, `do`, `while`, `!`, ...) dropped."""
    at = 0
    while at < len(words):
        word = words[at]
        if word in WRAPPERS:
            at += 1
            while at < len(words) and words[at].startswith("-"):
                at += 2 if words[at] in WRAPPERS[word] else 1
            if word in DURATION and at < len(words):
                at += 1
        elif re.fullmatch(r"\w+=.*", word) or word in git_guard.WRAP or word in KEYWORDS:
            at += 1
        else:
            break
    return words[at:]


def is_runner(words, depth=0, broad=False, names=None):
    """True when this shell segment's command word runs tests (`broad`: or a check, lint or build): pytest, `npm test`,
    `cargo test`, ./test.sh, ... Asking a runner about itself (`--version`, `--help`, `--collect-only`) runs nothing.
    `names`, when given, collects the command words the segment executes, for never_ran."""
    words = unwrap(words)
    if not words or depth > 4:
        return False
    name, args = os.path.basename(words[0]), words[1:]
    if names is not None:
        names.append(name)
    if any(a in INERT for a in args) or (name in ("make", "gmake") and "-n" in args):
        return False
    if name in ("npx", "bunx", "pnpx"):
        return is_runner(tail(args), depth + 1, broad, names)
    if name in LAUNCHERS and tail(args)[:1] and tail(args)[0] in LAUNCHERS[name]:
        return is_runner(tail(tail(args)[1:]), depth + 1, broad, names)
    if name in git_guard.SHELLS:
        if "-c" in args[:-1]:
            return _runs(args[args.index("-c") + 1], depth + 1, broad, names)
        return any(SCRIPT.search(a) or (broad and CHECKER.search(a)) for a in positional(args)[:1])
    if PYTHON.fullmatch(name):
        if python_runs_tests(args) and names is not None and python_module(args):
            names.append(python_module(args))
        script = [a for a in args if not a.startswith("-")]
        if script[:1] and os.path.basename(script[0]) == "manage.py":
            return script[1:2] == ["test"]
        return python_runs_tests(args) or (broad and any(CHECKER.search(a) for a in script[:1]))
    if SCRIPT.search(words[0]) or name in DIRECT or (broad and (CHECKER.search(words[0]) or name in LINTERS)):
        return True
    pos = positional(args)
    sub = pos[0] if pos else ""
    if name in ("npm", "pnpm", "yarn", "bun", "composer"):
        if sub in ("run", "run-script"):
            sub = pos[1] if len(pos) > 1 else ""
        return bool(TEST_SCRIPT.fullmatch(sub)) or (name != "composer" and sub in TEST_SCRIPTS | DIRECT) \
            or (broad and name != "composer" and bool(CHECK_SCRIPT.fullmatch(sub)))
    if name in TEST_SUBCOMMAND:
        return sub == TEST_SUBCOMMAND[name]
    if name in ("rails", "just", "task", "manage.py"):
        return bool(TEST_SCRIPT.fullmatch(sub))
    if name == "coverage":
        return "run" in args and python_runs_tests(args[args.index("run") + 1:])
    if name == "turbo":
        return bool(TEST_SCRIPT.fullmatch(pos[1] if sub == "run" and len(pos) > 1 else sub))
    if name == "nx":
        return bool(TEST_SCRIPT.fullmatch(sub)) or (sub == "run" and len(pos) > 1 and bool(NX_TARGET.fullmatch(pos[1])))
    if name == "playwright":
        return sub == "test"
    if name == "tsc":
        return broad and any(a in ("--noEmit", "-p", "--build") for a in args)
    if name == "agent-hub":
        return broad and sub == "check"
    if name == "node":
        return "--test" in args
    if name == "cargo":
        return sub == "test" or (sub == "nextest" and pos[1:2] == ["run"]) or (broad and sub in ("check", "clippy"))
    if name in ("gradle", "gradlew", "gradlew.bat"):
        return any(GRADLE_TASK.fullmatch(a) for a in pos)
    if name in ("mvn", "mvnw"):
        return any(a in ("test", "verify") for a in pos)
    if name == "rake":
        return not pos or bool(re.match(r"(?:test|spec|default)\b", sub))
    if name == "xcodebuild":
        return any(a in ("test", "test-without-building") for a in args)
    if name == "php":
        return pos[:2] == ["artisan", "test"]
    if name in ("make", "gmake"):
        targets = [a for a in pos if not a.isdigit() and "=" not in a]
        return (not targets and broad) or bool(targets and targets[0] in ("test", "tests", "check"))
    return False


def _runs(command, depth, broad, names=None):
    lines, substitutions = git_guard.split_lines(command)
    if depth < 3 and any(_runs(inner, depth + 1, broad, names) for inner in substitutions):
        return True
    found = False
    for line in lines:
        for segment in git_guard.segments(line):
            local = []
            if is_runner(segment, depth, broad, local):
                found = True
                if names is not None:
                    names.extend(local)
    return found


def runs_tests(command, depth=0):
    """True when a real shell segment of `command` runs a test runner; one named only in text, or a lint, build, check or
    `--version` call, does not count."""
    return _runs(command, depth, False)


def runs_checks(command, depth=0):
    """True when a real shell segment of `command` runs a test runner, a linter, a type check, a build or the project's checker."""
    return _runs(command, depth, True)


def never_ran(payload):
    """True when the tool output says the runner of this Bash command did not launch. A shell error line counts only when
    it names a command word the command itself runs (`sh: husky: command not found` in a passing run is not it, nor is a
    missing `jq` after `pytest &&`); a launch failure of npm, pnpm, make, cargo or python counts; `Exit code 126|127` counts
    when no test summary is present. Output is read as the harness sends it: `tool_response.stdout` and `.stderr` of a success,
    `error` (`Exit code N` and the text) of a failure; there is no exit-code field."""
    texts = []

    def walk(value, depth=0):
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict) and depth < 4:
            for inner in value.values():
                walk(inner, depth + 1)
        elif isinstance(value, list) and depth < 4:
            for inner in value:
                walk(inner, depth + 1)

    for key in ("tool_response", "tool_output", "error", "stderr", "stdout", "output"):
        walk(payload.get(key))
    text = "\n".join(texts)
    names = []
    _runs(str((payload.get("tool_input") or {}).get("command") or ""), 0, True, names)
    if LAUNCH_FAILURES.search(text) and not SUMMARY.search(text):
        return True
    error = payload.get("error")
    if isinstance(error, str) and re.match(r"Exit code (?:126|127)\b", error) and not SUMMARY.search(error):
        return True
    if not names:
        return False
    alt = "|".join(re.escape(n) for n in sorted(set(names)))
    shell = "^" + SHELL_PREFIX
    patterns = (shell + r"command not found: (?:%s)\s*$" % alt,
                shell + r"'?(?:%s)'?: (?:command )?not found\s*$" % alt,
                r"^'?(?:%s)'?\s+is not recognized as\b" % alt,
                r"^(?:[-/\w.]*python[\d.]*: |ModuleNotFoundError: |ImportError: )?No module named '?(?:%s)'?\s*$" % alt)
    return any(re.search(pattern, text, re.M) for pattern in patterns)
