"""Tests for plugins/agent-hub/hooks/moment.py, hooks/moments.json and scripts/rule-slice.py (runs under unittest and pytest)."""
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "agent-hub"
HOOKS = PLUGIN / "hooks"
SCRIPT = HOOKS / "moment.py"
RUNNERS_PY = HOOKS / "runners.py"
SLICE = PLUGIN / "scripts" / "rule-slice.py"
CONFIG = json.loads((HOOKS / "moments.json").read_text(encoding="utf-8")) if (HOOKS / "moments.json").exists() else {"moments": []}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MomentCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="agent-hub-moment-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.races = 0

    def env(self, **env_extra):
        env = {**os.environ, "AGENT_HUB_STATE_DIR": str(self.tmp), "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
        for key in ("AGENT_HUB_MOMENTS", "AGENT_HUB_BLOCKS", "CLAUDE_PLUGIN_OPTION_MOMENT_HOOKS", "CLAUDE_PLUGIN_OPTION_HOOK_BLOCKS"):
            env.pop(key, None)
        env.update(env_extra)
        return env

    def hook(self, event, payload, **env_extra):
        data = payload if isinstance(payload, str) else json.dumps(payload)
        res = subprocess.run([sys.executable, str(SCRIPT), event], input=data, capture_output=True, text=True, env=self.env(**env_extra), timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout) if res.stdout.strip() else {}

    def race(self, event, payloads):
        """One hook process per payload, all released at once by a go file; their parsed outputs."""
        self.races += 1
        go = self.tmp / ("go%d" % self.races)
        wrapper = ("import os, runpy, sys, time\ngo = sys.argv[1]\nwhile not os.path.exists(go): time.sleep(0.0005)\n"
                   "sys.argv = [%r, %r]\nrunpy.run_path(%r, run_name='__main__')" % (str(SCRIPT), event, str(SCRIPT)))
        procs = [subprocess.Popen([sys.executable, "-c", wrapper, str(go)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, env=self.env()) for _ in payloads]
        for proc, payload in zip(procs, payloads):
            proc.stdin.write(json.dumps(payload))
            proc.stdin.close()
        time.sleep(0.3)
        go.write_text("go")
        outs = [proc.stdout.read() for proc in procs]
        for proc in procs:
            proc.wait(timeout=30)
        return [json.loads(out) if out.strip() else {} for out in outs]

    def call(self, tool, role="implement", agent="a1", **tool_input):
        payload = {"session_id": "s1", "tool_name": tool, "tool_input": tool_input}
        if role != "main":
            payload.update(agent_id=agent, agent_type="agent-hub:" + role)
        return payload

    def context(self, out):
        return out.get("hookSpecificOutput", {}).get("additionalContext", "")

    def denied(self, out):
        spec = out.get("hookSpecificOutput", {})
        return spec.get("permissionDecisionReason", "") if spec.get("permissionDecision") == "deny" else ""

    def ran_tests(self, role="implement", agent="a1", event="PostToolUse"):
        self.hook(event, self.call("Bash", role, agent, command="python3 -m unittest discover -s tests"))


class Baseline(MomentCase):
    def test_a_code_edit_before_any_test_run_is_refused_twice_then_let_through_with_a_warning(self):
        edit = self.call("Edit", file_path="src/app.py")
        for _ in range(2):
            self.assertIn("has not run the baseline tests yet", self.denied(self.hook("PreToolUse", edit)))
        third = self.hook("PreToolUse", edit)
        self.assertEqual(self.denied(third), "")
        self.assertIn("refused 2 times, then let through", third["systemMessage"])
        self.assertIn("[refs/roles/implement/craft.md § Priorities", self.context(third))
        self.assertNotIn("systemMessage", self.hook("PreToolUse", edit))

    def test_a_finished_test_command_green_or_red_opens_the_edit(self):
        for event in ("PostToolUse", "PostToolUseFailure"):
            agent = "a-" + event
            self.ran_tests(agent=agent, event=event)
            self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Write", agent=agent, file_path="src/app.ts"))), "")

    def test_a_test_command_that_was_only_attempted_does_not_count(self):
        self.hook("PreToolUse", self.call("Bash", command="pytest -q"))
        self.assertNotEqual(self.denied(self.hook("PreToolUse", self.call("Edit", file_path="src/app.py"))), "")

    def test_shell_writes_to_code_are_seen_and_temporary_or_doc_paths_are_not(self):
        heredoc = "python3 - <<'PY'\nopen('src/app.py', 'w').write('x')\nPY"
        for n, command in enumerate(("cat > src/app.py <<'EOF'\nx\nEOF", "sed -i '' 's/a/b/' src/app.py", "echo x | tee src/app.py", heredoc)):
            self.assertNotEqual(self.denied(self.hook("PreToolUse", self.call("Bash", agent="w%d" % n, command=command))), "", command)
        for command in ("cat > .cm-tmp/t1/probe.py <<'EOF'\nx\nEOF", "echo done > notes.md", "grep -c 'a > b' src/app.py", "ls 2>/dev/null"):
            self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Bash", agent="b2", command=command))), "", command)

    def test_only_implement_is_held_to_it(self):
        for role in ("main", "reviewer", "test", "devops"):
            self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Edit", role, file_path="src/app.py"))), "", role)

    def test_blocks_off_turns_the_refusal_into_one_note(self):
        edit = self.call("Edit", file_path="src/app.py")
        first = self.hook("PreToolUse", edit, AGENT_HUB_BLOCKS="0")
        self.assertEqual(self.denied(first), "")
        self.assertIn("has not run the baseline tests yet", self.context(first))
        self.assertNotIn("baseline tests yet", self.context(self.hook("PreToolUse", edit, CLAUDE_PLUGIN_OPTION_HOOK_BLOCKS="off")))

    def test_moments_off_and_bad_input_are_silent(self):
        edit = self.call("Edit", file_path="src/app.py")
        self.assertEqual(self.hook("PreToolUse", edit, AGENT_HUB_MOMENTS="0"), {})
        self.assertEqual(self.hook("PreToolUse", "not json"), {})
        self.assertEqual(self.hook("PreToolUse", {"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}), {})
        self.assertEqual(self.hook("Stop", edit), {})


class Commit(MomentCase):
    GOOD = "git add -A && git commit -m \"$(cat <<'EOF'\nfix(mail): set Reply-To\n\nRefs: mail-fix / 1.2\n\nCo-Authored-By: Claude <noreply@anthropic.com>\nEOF\n)\""

    def test_a_commit_without_a_refs_line_is_refused_twice_then_let_through(self):
        self.ran_tests()
        bad = self.call("Bash", command="git add -A && git commit -m 'fix(mail): set Reply-To'")
        for _ in range(2):
            self.assertIn("has no `Refs:` line", self.denied(self.hook("PreToolUse", bad)))
        third = self.hook("PreToolUse", bad)
        self.assertEqual(self.denied(third), "")
        self.assertIn("committed with no `Refs:` line", third["systemMessage"])

    def test_a_message_with_refs_passes_and_brings_the_commit_section_once(self):
        first = self.hook("PreToolUse", self.call("Bash", command=self.GOOD))
        self.assertEqual(self.denied(first), "")
        self.assertIn("[refs/roles/implement/close-task.md § Commit]", self.context(first))
        self.assertEqual(self.hook("PreToolUse", self.call("Bash", command=self.GOOD)), {})

    def test_forms_of_commit(self):
        mod = load(SCRIPT, "moment")
        cases = {
            "git commit -m 'a' -m 'Refs: x / 1.1'": "refs",
            "git -C repo commit -am 'a\n\nRefs: x / 1.1'": "refs",
            "git -c user.name=a commit --message='a\n\nRefs: x / 1'": "refs",
            "git commit -m 'mentions Refs: inline only'": "no-refs",
            "git commit -m 'a' && git commit -m 'b\n\nRefs: x / 1'": "no-refs",
            "git commit -F msg.txt": "unread",
            "git commit --amend --no-edit": "unread",
            "git commit": "unread",
            "echo 'git commit -m x'": None,
            "git log --grep commit": None,
            "grep -rn 'git commit' docs": None,
        }
        for command, want in cases.items():
            self.assertEqual(mod.commit_state(command), want, command)

    def test_a_message_the_hook_cannot_read_is_let_through(self):
        self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Bash", command="git commit -F .cm-tmp/msg.txt"))), "")

    def test_main_thread_commits_are_not_held_to_it(self):
        self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Bash", "main", command="git commit -m wip"))), "")


class Advisory(MomentCase):
    def test_first_python_write_brings_craft_the_language_file_and_the_discipline_slices_once(self):
        self.ran_tests()
        text = self.context(self.hook("PreToolUse", self.call("Edit", file_path="src/app.py")))
        for head in ("[refs/roles/implement/craft.md § Priorities", "[refs/roles/implement/craft.md § Cases and security]", "[rules/code-style/python.md]"):
            self.assertIn(head, text)
        self.assertNotIn("paths:", text.split("[rules/code-style/python.md]")[1][:80])
        self.assertLess(len(text), 9500)
        later = self.context(self.hook("PreToolUse", self.call("Edit", file_path="src/other.py")))   # what did not fit goes out on the next write
        for head in ("§ Naming]", "§ Function and file shape]"):
            self.assertIn(head, later)
        self.assertEqual(self.hook("PreToolUse", self.call("Edit", file_path="src/third.py")), {})

    def test_the_discipline_file_is_read_at_intake_so_only_the_main_thread_is_handed_its_slices(self):
        self.ran_tests()
        seen = "".join(self.context(self.hook("PreToolUse", self.call("Edit", file_path="src/f%d.py" % n))) for n in range(4))
        self.assertNotIn("[rules/code-style/_discipline.md", seen)
        main = "".join(self.context(self.hook("PreToolUse", {**self.call("Edit", "main", file_path="src/f%d.py" % n), "session_id": "m1"})) for n in range(3))
        for head in ("[rules/code-style/_discipline.md § 4. Scope]", "[rules/code-style/_discipline.md § The quality floor]"):
            self.assertEqual(main.count(head), 1, head)

    def test_craft_arrives_whole_at_the_first_writes_with_cases_ahead_of_the_language_style(self):
        self.ran_tests()
        seen = []
        for _ in range(4):
            seen.append(self.context(self.hook("PreToolUse", self.call("Edit", file_path="src/app.py"))))
        for head in ("§ Priorities", "§ Naming]", "§ Function and file shape]", "§ Cases and security]", "[rules/code-style/python.md]"):
            self.assertEqual("".join(seen).count(head), 1, head)
        self.assertLess(seen[0].index("§ Cases and security]"), seen[0].index("[rules/code-style/python.md]"))
        for text in seen:
            self.assertLess(len(text), 9500)

    def test_what_does_not_fit_one_call_goes_out_on_the_next_matching_one(self):
        self.ran_tests()
        seen = ""
        for _ in range(4):
            seen += self.context(self.hook("PreToolUse", self.call("Write", file_path="web/Button.tsx")))
        for head in ("[rules/code-style/typescript.md]", "[rules/code-style/react.md]", "[rules/UI_RULES.md]"):
            self.assertEqual(seen.count(head), 1, head)

    def test_state_is_per_spawn(self):
        self.ran_tests(agent="a1")
        self.ran_tests(agent="a2")
        self.assertIn("python.md", self.context(self.hook("PreToolUse", self.call("Edit", agent="a1", file_path="a.py"))))
        self.assertIn("python.md", self.context(self.hook("PreToolUse", self.call("Edit", agent="a2", file_path="a.py"))))

    def test_role_scoped_moments(self):
        self.assertIn("§ Review shape]", self.context(self.hook("PreToolUse", self.call("Write", "reviewer", agent="r1", file_path="openspec/changes/x/review.md"))))
        self.assertIn("§ Where writing is allowed]", self.context(self.hook("PreToolUse", self.call("Write", "devops", agent="d1", file_path="docs/devops/SERVER-INFO.md"))))
        self.assertIn("§ Lookup order]", self.context(self.hook("PreToolUse", self.call("WebSearch", "scout", agent="s1", query="x"))))
        self.assertIn("H1 and H5", self.context(self.hook("PreToolUse", self.call("Bash", "scout", agent="s2", command="grep -rn foo src 2>/dev/null | head -5"))))
        self.assertIn("§ 1.1 Spec Layer", self.context(self.hook("PreToolUse", self.call("Read", "test", agent="t1", file_path="openspec/specs/mail/spec.md"))))
        spec_edit = self.context(self.hook("PreToolUse", self.call("Write", "implement", agent="a9", file_path="openspec/specs/mail/spec.md")))
        self.assertIn("undo this write", spec_edit)
        self.assertNotIn("undo this write", self.context(self.hook("PreToolUse", self.call("Edit", "implement", agent="a10", file_path="openspec/changes/x/tasks.md"))))

    def test_red_results(self):
        fail = self.call("Bash", "test", command="npx playwright test")
        self.assertIn("§ Evidence", self.context(self.hook("PostToolUseFailure", fail)))
        self.assertEqual(self.context(self.hook("PostToolUseFailure", fail)), "")
        red = self.call("Bash", "implement", command="pytest -q")
        self.assertEqual(self.context(self.hook("PostToolUseFailure", red)), "")
        self.hook("PostToolUse", self.call("Edit", "implement", file_path="src/app.py"))
        self.assertIn("red after three attempts", self.context(self.hook("PostToolUseFailure", red)))

    def test_the_counter_speaks_at_the_soft_and_hard_stops(self):
        said = {}
        for n in range(1, 42):
            text = self.context(self.hook("PostToolUseFailure" if n % 7 == 0 else "PostToolUse", self.call("Read", "reviewer", file_path="a.md")))
            if text:
                said[n] = text
        self.assertEqual(sorted(said), [25, 40])
        self.assertIn("soft stop", said[25])
        self.assertIn("hard stop", said[40])
        for n in range(1, 30):
            self.assertEqual(self.context(self.hook("PostToolUse", self.call("Read", "scout", agent="s1", file_path="a.md"))), "")

    def test_a_compaction_lets_the_main_threads_notes_fire_again(self):
        edit = self.call("Edit", "main", file_path="a.py")
        self.assertIn("python.md", self.context(self.hook("PreToolUse", edit)))
        self.assertEqual(self.hook("PreToolUse", edit), {})
        self.hook("SessionStart", {"session_id": "s1", "source": "compact"})
        self.assertIn("python.md", self.context(self.hook("PreToolUse", edit)))
        self.assertEqual(self.hook("PreToolUse", edit), {})


class Concurrency(MomentCase):
    """Parallel tool calls run their hooks at once: no fact may be lost and no moment or call number given twice."""

    def test_concurrent_calls_of_one_spawn_number_each_call_once(self):
        outs = self.race("PostToolUse", [self.call("Read", "reviewer", agent="r-race", file_path="a.md")] * 30)
        self.assertEqual(sum("soft stop" in self.context(out) for out in outs), 1)
        said = [self.context(self.hook("PostToolUse", self.call("Read", "reviewer", agent="r-race", file_path="a.md"))) for _ in range(10)]
        self.assertEqual([n for n, text in enumerate(said, 31) if text], [40])

    def test_a_finished_test_run_is_never_lost_to_a_concurrent_call(self):
        for round_no in range(5):
            agent = "t-race%d" % round_no
            payloads = [self.call("Bash", agent=agent, command="pytest -q")] + [self.call("Read", agent=agent, file_path="a.py")] * 5
            self.race("PostToolUse", payloads)
            self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Edit", agent=agent, file_path="src/app.py"))), "", round_no)

    def test_concurrent_first_writes_deliver_each_moment_once(self):
        self.ran_tests(agent="w-race")
        outs = self.race("PreToolUse", [self.call("Edit", agent="w-race", file_path="src/a%d.py" % n) for n in range(6)])
        self.assertEqual(sum(self.context(out).count("[rules/code-style/python.md]") for out in outs), 1)

    def test_claimed_reads_a_claim_without_making_one(self):
        code = ("import sys; sys.path.insert(0, %r); import _state; p = {'session_id': 's1', 'agent_id': 'a1'}; "
                "print(_state.claimed(p, 'x'), _state.claimed(p, 'x'), _state.claim(p, 'x'), _state.claimed(p, 'x'), _state.claim(p, 'x'))" % str(HOOKS))
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=self.env(), timeout=30)
        self.assertEqual(res.stdout.split(), ["False", "False", "True", "True", "False"], res.stderr)


class Runners(MomentCase):
    """The baseline gate opens on a test runner that ran as the command word of a shell segment, and only then."""
    counter = 0

    def opens(self, command, event="PostToolUse", **extra):
        Runners.counter += 1
        agent = "g%d" % Runners.counter
        self.hook(event, {**self.call("Bash", agent=agent, command=command), **extra})
        return self.denied(self.hook("PreToolUse", self.call("Edit", agent=agent, file_path="src/app.py"))) == ""

    RUNNERS = (
        "pytest -q", "python3 -m pytest -x", "python3.12 -m pytest", "python -m unittest discover -s tests", "tox -e py312", "nox -s tests",
        "npm test", "npm t", "pnpm test", "yarn test", "bun test", "npm run test", "npx jest --ci", "pnpm exec vitest run", "npx mocha",
        "npx playwright test", "node --test", "deno test", "go test ./...", "cargo test", "cargo nextest run", "./gradlew test", "gradle check",
        "mvn test", "./mvnw verify", "dotnet test", "rspec", "bundle exec rspec", "bundle exec rake", "rake test", "swift test",
        "xcodebuild -scheme App test", "flutter test", "dart test", "mix test", "php artisan test", "phpunit", "composer test", "make test",
        "make check", "make -j4 test", "ctest", "bazel test //...", "./scripts/test-all.sh", "bash scripts/run-tests.sh", "FOO=1 poetry run pytest",
        "uv run pytest", "cd sub && pytest", "PYTHONPATH=. python3 -m pytest",
    )
    WRAPPED = (
        "timeout 600 pytest", "gtimeout 60 pytest", "nice pytest", "nice -n 10 pytest", "ionice -c3 pytest", "stdbuf -oL pytest", "env -i pytest",
        "env -u X pytest", "if pytest; then echo ok; fi", "for f in a b; do pytest $f; done", "while ! pytest; do sleep 1; done", "! pytest",
    )
    FAMILIES = (
        "npm run test:unit", "pnpm test:unit", "yarn test-e2e", "python manage.py test", "./manage.py test", "coverage run -m pytest",
        "coverage run -m unittest", "hatch test", "rails test", "./vendor/bin/pest", "vendor/bin/phpunit", "just test", "task test", "turbo test",
        "turbo run test", "nx test app", "nx run app:test",
    )
    NOT_TESTS = (
        "npm run lint", "npm run build", "npm run typecheck", "eslint .", "ruff check .", "shellcheck a.sh", "tsc --noEmit", "agent-hub check",
        "python3 tools/check.py ruleset", "cargo check", "cargo clippy", "make", "make -j4", "make build", "make -n test", "pytest --version",
        "pytest -V", "pytest --help", "pytest -h", "pytest --collect-only", "cargo test --list-tests", "npm test --dry-run", "npx jest --version",
        "ls tests", "nice -n 10 ls", "if grep pytest x; then echo ok; fi", "just build", "turbo run build", "nx run app:build", "python manage.py migrate",
    )

    def test_every_runner_family_opens_the_gate(self):
        for command in self.RUNNERS:
            self.assertTrue(self.opens(command), command)

    def test_a_runner_behind_a_wrapper_or_a_shell_keyword_is_still_the_command_word(self):
        mod = load(RUNNERS_PY, "runners_wrapped")
        for command in self.WRAPPED + self.FAMILIES:
            with self.subTest(command=command):
                self.assertTrue(mod.runs_tests(command))

    def test_only_a_test_run_opens_the_gate_not_a_lint_a_build_a_check_or_a_version_call(self):
        mod = load(RUNNERS_PY, "runners_narrow")
        for command in self.NOT_TESTS:
            with self.subTest(command=command):
                self.assertFalse(mod.runs_tests(command))
        for command in ("npm run lint", "eslint .", "ruff check .", "tsc --noEmit", "agent-hub check", "python3 tools/check.py ruleset", "cargo clippy",
                        "make", "make -j4", "npm run typecheck", "shellcheck a.sh"):
            with self.subTest(broad=command):
                self.assertTrue(mod.runs_checks(command))
        for command in ("pytest --version", "make -n test", "ls", "make build"):
            with self.subTest(broad=command):
                self.assertFalse(mod.runs_checks(command))
        for n, command in enumerate(("npm run lint", "make", "cargo check")):
            self.assertFalse(self.opens(command), command)

    def test_a_red_lint_after_an_edit_still_brings_the_red_after_edit_note(self):
        self.hook("PostToolUse", self.call("Edit", agent="l1", file_path="src/app.py"))
        out = self.hook("PostToolUseFailure", self.call("Bash", agent="l1", command="npm run lint"))
        self.assertIn("red after three attempts", self.context(out))

    def test_a_runner_named_in_text_but_not_run_does_not_open_it(self):
        for command in ("grep pytest pyproject.toml", "cat package.json | grep jest", "echo run npm test", "git log --grep=pytest", "cat tests/test.sh", "ls tests"):
            self.assertFalse(self.opens(command), command)

    def test_a_runner_that_never_ran_does_not_count_but_a_red_run_does(self):
        self.assertFalse(self.opens("pytest -q", "PostToolUseFailure", error="Exit code 127\nbash: pytest: command not found"))
        self.assertFalse(self.opens("pytest -q", "PostToolUse", tool_response={"stdout": "", "stderr": "/usr/bin/python3: No module named pytest"}))
        self.assertFalse(self.opens("python3 -m unittest", "PostToolUseFailure", error="No module named unittest"))
        self.assertFalse(self.opens("npm test", "PostToolUseFailure", error="Exit code 127\nsh: jest: command not found"))
        self.assertFalse(self.opens("pytest", "PostToolUse", tool_response="'pytest' is not recognized as an internal or external command"))
        self.assertFalse(self.opens("pytest", "PostToolUseFailure", error="Exit code 127"))
        self.assertTrue(self.opens("pytest -q", "PostToolUseFailure", error="Exit code 1\nFAILED tests/test_a.py::test_b - assert 1 == 2"))

    RAN = (   # (command, payload fields): a runner that ran, whatever else the output says
        ("npm test", {"tool_response": {"stdout": "12 passing", "stderr": "sh: husky: command not found"}}),
        ("pytest && jq .", {"error": "Exit code 127\nbash: jq: command not found\n======= 120 passed in 3s ======="}),
        ("python3 -m pytest", {"error": "Exit code 1\nModuleNotFoundError: No module named 'unittest.mock2'\n1 failed, 3 passed"}),
        ("pytest -q", {"error": "Exit code 1\nE   AssertionError: pytest: command not found\n1 failed"}),
        ("pytest -q", {"error": "Exit code 1\n    assert 'command not found: pytest' in out\n1 failed"}),
        ("pytest -q", {"error": "Exit code 1\n    assert 'No module named pytest' == out\nFAILED tests/test_a.py::test_b"}),
        ("python3 -m unittest", {"error": "Exit code 1\nRan 3 tests in 0.1s\nFAILED (failures=1)"}),
        ("pytest -q", {"error": "Exit code 1\n    assert '(eval):1: command not found: pytest' in out\n1 failed"}),
        ("go test ./... && jq . x.json", {"error": "Exit code 127\nok  \texample.com/pkg\t0.01s\n(eval):1: command not found: jq"}),
        ("node --test && jq .", {"error": "Exit code 127\n\u2139 pass 5\n(eval):1: command not found: jq"}),
    )
    NOT_RAN = (   # a launch that failed
        ("npm test", {"error": "Exit code 1\nnpm error Missing script: \"test\""}),
        ("pnpm test", {"error": "Exit code 1\n ERR_PNPM_NO_SCRIPT  Missing script: test"}),
        ("npx jest", {"error": "Exit code 1\nnpm error could not determine executable to run"}),
        ("make test", {"error": "Exit code 2\nmake: *** No rule to make target 'test'.  Stop."}),
        ("cargo test", {"error": "Exit code 101\nerror: could not find `Cargo.toml` in `/x` or any parent directory"}),
        ("python3 run_tests.py", {"error": "Exit code 2\n/usr/bin/python3: can't open file '/x/run_tests.py': [Errno 2] No such file or directory"}),
        ("./scripts/test-all.sh", {"error": "Exit code 126\nbash: ./scripts/test-all.sh: Permission denied"}),
        ("pytest -q", {"error": "Exit code 127\nbash: line 1: pytest: command not found"}),
        ("pytest -q", {"error": "Exit code 127\nzsh: command not found: pytest"}),
        ("pytest -q 2>&1 | tail -5", {"tool_response": {"stdout": "(eval):1: command not found: pytest", "stderr": ""}}),
        ("pytest -q", {"error": "Exit code 127\nzsh:1: command not found: pytest"}),
        ("pytest -q", {"error": "Exit code 127\n(eval):1: pytest: command not found"}),
        ("pytest -q", {"tool_response": {"stdout": "", "stderr": "sh: 1: pytest: not found"}}),
        ("uv run pytest", {"error": "Exit code 127\nbash: uv: command not found"}),
        ("python3 -m pytest", {"tool_response": {"stdout": "", "stderr": "/usr/bin/python3: No module named pytest"}}),
        ("python3 -m pytest", {"error": "ModuleNotFoundError: No module named 'pytest'"}),
    )

    def test_never_ran_reads_the_shells_own_error_line_for_the_runners_own_name(self):
        mod = load(RUNNERS_PY, "runners_never")
        for command, fields in self.RAN:
            with self.subTest(ran=command, fields=fields):
                self.assertFalse(mod.never_ran({"tool_name": "Bash", "tool_input": {"command": command}, **fields}))
        for command, fields in self.NOT_RAN:
            with self.subTest(not_ran=command, fields=fields):
                self.assertTrue(mod.never_ran({"tool_name": "Bash", "tool_input": {"command": command}, **fields}))

    def test_a_passing_run_with_a_missing_helper_in_its_output_opens_the_gate(self):
        self.assertTrue(self.opens("npm test", "PostToolUse", tool_response={"stdout": "12 passing", "stderr": "sh: husky: command not found"}))
        self.assertFalse(self.opens("npm test", "PostToolUseFailure", error="Exit code 1\nnpm error Missing script: \"test\""))

    def test_a_code_extension_no_runner_can_satisfy_is_not_guarded(self):
        for n, path in enumerate(("web/site.css", "web/index.html", "db/schema.sql", "web/a.scss")):
            self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Edit", agent="u%d" % n, file_path=path))), "", path)
        self.assertNotEqual(self.denied(self.hook("PreToolUse", self.call("Edit", agent="u-py", file_path="src/app.py"))), "")


class Exemptions(MomentCase):
    def test_refusal_texts_promise_no_later_pass(self):
        edit = self.call("Edit", file_path="src/app.py")
        self.assertNotIn("goes through", self.denied(self.hook("PreToolUse", edit)).lower())
        bad = self.call("Bash", command="git commit -m 'x'")
        self.ran_tests(agent="c1")
        reason = self.denied(self.hook("PreToolUse", {**bad, "agent_id": "c1"}))
        self.assertTrue(reason)
        self.assertNotRegex(reason.lower(), r"goes through|let through|third")

    def test_a_resumed_spawn_that_read_its_progress_file_gets_the_baseline_text_once_and_no_deny(self):
        self.hook("PostToolUse", self.call("Read", file_path="/repo/.cm-tmp/1.2/progress.yaml"))
        edit = self.call("Edit", file_path="src/app.py")
        first = self.hook("PreToolUse", edit)
        self.assertEqual(self.denied(first), "")
        self.assertIn("has not run the baseline tests yet", self.context(first))
        self.assertNotIn("baseline tests yet", self.context(self.hook("PreToolUse", self.call("Edit", file_path="src/b.py"))))
        self.assertNotIn("systemMessage", first)

    def test_a_resume_that_read_its_checkpoint_with_cat_is_exempt_too(self):
        for n, command in enumerate(("cat .cm-tmp/1.2/progress.yaml", "head -n 40 /repo/.cm-tmp/1.2/progress.yaml", "less .cm-tmp/t/progress.yaml",
                                     "sed -n '1,40p' .cm-tmp/t/progress.yaml", "cd /repo && cat '.cm-tmp/t/progress.yaml'")):
            agent = "r%d" % n
            self.hook("PostToolUse", self.call("Bash", agent=agent, command=command))
            out = self.hook("PreToolUse", self.call("Edit", agent=agent, file_path="src/app.py"))
            self.assertEqual(self.denied(out), "", command)
            self.assertIn("has not run the baseline tests yet", self.context(out), command)
        for n, command in enumerate(("echo .cm-tmp/t/progress.yaml", "cat src/progress.yaml", "grep x .cm-tmp/t/progress.yaml", "sed 's/a/b/' .cm-tmp/t/progress.yaml")):
            agent = "q%d" % n
            self.hook("PostToolUse", self.call("Bash", agent=agent, command=command))
            self.assertNotEqual(self.denied(self.hook("PreToolUse", self.call("Edit", agent=agent, file_path="src/app.py"))), "", command)

    def test_the_baseline_refusal_asks_to_repeat_the_call_not_the_edit(self):
        reason = self.denied(self.hook("PreToolUse", self.call("Bash", command="cat > src/app.py <<'EOF'\nx\nEOF")))
        self.assertTrue(reason.endswith("Then repeat this call."), reason)

    def test_a_spawn_that_invoked_the_simplify_skill_is_exempt_too(self):
        self.hook("PostToolUse", self.call("Skill", skill="simplify"))
        out = self.hook("PreToolUse", self.call("Edit", file_path="src/app.py"))
        self.assertEqual(self.denied(out), "")
        self.assertIn("has not run the baseline tests yet", self.context(out))

    def test_reading_another_file_or_another_skill_or_a_mere_attempt_exempts_nothing(self):
        self.hook("PostToolUse", self.call("Read", agent="x1", file_path="/repo/src/progress.yaml"))
        self.hook("PostToolUse", self.call("Skill", agent="x1", skill="review"))
        self.hook("PreToolUse", self.call("Read", agent="x1", file_path="/repo/.cm-tmp/1.2/progress.yaml"))
        self.hook("PreToolUse", self.call("Skill", agent="x1", skill="simplify"))
        self.assertNotEqual(self.denied(self.hook("PreToolUse", self.call("Edit", agent="x1", file_path="src/app.py"))), "")

    def test_a_pass_with_warning_tells_the_model_to_report_it_under_risks(self):
        edit = self.call("Edit", file_path="src/app.py")
        for _ in range(2):
            self.hook("PreToolUse", edit)
        third = self.hook("PreToolUse", edit)
        self.assertIn("## Risks", self.context(third))
        self.assertIn("without the baseline test run", self.context(third))
        self.ran_tests(agent="c2")
        bad = {**self.call("Bash", agent="c2", command="git commit -m 'x'")}
        for _ in range(2):
            self.hook("PreToolUse", bad)
        last = self.hook("PreToolUse", bad)
        self.assertIn("## Risks", self.context(last))
        self.assertIn("no `Refs:` line", self.context(last))


class Unread(MomentCase):
    def test_a_message_built_by_the_shell_is_unread_not_missing(self):
        mod = load(SCRIPT, "moment_unread")
        cases = {
            'git commit -m "$MSG"': "unread",
            'git commit -m "$(cat .git/msg)"': "unread",
            "git commit -m \"$(printf 'fix: x\\n')\"": "unread",
            "git commit -m `cat msg`": "unread",
            "git commit -m 'costs $5 today'": "no-refs",
            "cd $R && git commit -m 'fix $PATH handling'": "no-refs",
            "cd $R && git commit -m 'fix: x\n\nRefs: a / 1'": "refs",
            'cd $R && git commit -m "fix $PATH handling"': "unread",
            "cd $R && git commit -m 'a' -m \"$MSG\"": "unread",
            "git commit -m 'a\n\nRefs: x / 1'": "refs",
            "git commit -m \"fix: x\"": "no-refs",
            "echo '$MSG'; git commit -m \"$MSG\"": "unread",
            "git commit -m 'feat: cost $5 fix'": "no-refs",
        }
        for command, want in cases.items():
            self.assertEqual(mod.commit_state(command), want, command)

    def test_a_shell_built_message_is_let_through(self):
        self.ran_tests()
        for command in ('git commit -m "$MSG"', 'git commit -m "$(cat .git/msg)"'):
            self.assertEqual(self.denied(self.hook("PreToolUse", self.call("Bash", command=command))), "", command)


class Scope(MomentCase):
    def test_a_star_role_is_the_main_thread_or_an_agent_hub_agent_only(self):
        write = {"tool_name": "Write", "tool_input": {"file_path": "docs/notes/README.md"}, "session_id": "s1"}
        other = self.hook("PreToolUse", {**write, "agent_id": "z1", "agent_type": "codex:codex-rescue"})
        self.assertEqual(other, {})
        for n, kind in enumerate(("agent-hub:devops", "agent-hub:brainstorm")):
            got = self.hook("PreToolUse", {**write, "agent_id": "z%d" % (n + 2), "agent_type": kind})
            self.assertIn("§ Where writing is allowed]", self.context(got), kind)
        self.assertIn("§ Where writing is allowed]", self.context(self.hook("PreToolUse", {**write, "session_id": "s2"})))


class Output(MomentCase):
    def test_a_prune_that_raises_costs_no_output(self):
        mod = load(SCRIPT, "moment_prune")
        payload = {**self.call("Write", "devops", agent="p1", file_path="docs/notes/README.md")}
        out = io.StringIO()
        with unittest.mock.patch.dict(os.environ, self.env()), unittest.mock.patch("sys.stdin", io.StringIO(json.dumps(payload))), \
                contextlib.redirect_stdout(out), unittest.mock.patch.object(mod._state, "prune_sometimes", side_effect=OSError("boom")):
            mod.main(["PreToolUse"])
        self.assertIn("Where writing is allowed", out.getvalue())


class Config(unittest.TestCase):
    def test_every_slice_resolves_and_every_moment_fits_the_context_cap(self):
        slicer, mod = load(SLICE, "rule_slice"), load(SCRIPT, "moment")
        ids = [m["id"] for m in CONFIG["moments"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 19)
        for moment in CONFIG["moments"]:
            self.assertRegex(moment["id"], r"^[a-z0-9-]{1,60}$")   # it becomes part of a marker file name
            self.assertIn(moment["on"], ("write", "touch", "bash", "commit", "web", "fail", "calls"), moment["id"])
            self.assertTrue(moment.get("slices") or moment.get("note"), moment["id"])
            text = mod.render(moment, slicer)
            self.assertTrue(text, "a slice of %s does not resolve" % moment["id"])
            self.assertLess(len(text), CONFIG["limits"]["max_chars"], moment["id"])

    def test_slices(self):
        slicer = load(SLICE, "rule_slice")
        text = slicer.slice_text(str(PLUGIN), "refs/turn-budget.md#The ceiling")
        self.assertTrue(text.startswith("## The ceiling\n"))
        self.assertNotIn("## The context backstop", text)
        self.assertIn("**Soft stop, 25 tool calls.**", text)
        for bad in ("refs/turn-budget.md#No such heading", "refs/absent.md", "../../README.md", "#The ceiling"):
            with self.assertRaises(slicer.NoSlice):
                slicer.slice_text(str(PLUGIN), bad)
        res = subprocess.run([sys.executable, str(SLICE), "refs/turn-budget.md#Nope"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        res = subprocess.run([sys.executable, str(SLICE), "rules/code-style/python.md"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertFalse(res.stdout.startswith("---"))

    def test_hooks_json_wires_the_four_events_and_pairs_no_if_with_a_multi_tool_matcher(self):
        hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            commands = [h["command"] for g in hooks[event] for h in g["hooks"]]
            self.assertIn('python3 "${CLAUDE_PLUGIN_ROOT}/hooks/moment.py" ' + event, commands)
        compact = [h["command"] for g in hooks["SessionStart"] if g.get("matcher") == "compact" for h in g["hooks"]]
        self.assertIn('python3 "${CLAUDE_PLUGIN_ROOT}/hooks/moment.py" SessionStart', compact)
        for groups in hooks.values():
            for group in groups:
                for handler in group["hooks"]:
                    if "if" in handler:   # an `if` names one tool: a matcher of several tools would leave the others unfiltered
                        self.assertRegex(group.get("matcher", ""), r"^\w+$", handler["command"])

    def test_the_hook_keeps_no_read_modify_write_state(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"_state\.(?:load|save|state_file)\(", source))


if __name__ == "__main__":
    unittest.main()
