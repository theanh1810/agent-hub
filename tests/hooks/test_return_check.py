"""Tests for plugins/agent-hub/hooks/return_check.py and scripts/return-check.py (runs under unittest and pytest)."""
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
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "agent-hub"
HOOK = PLUGIN / "hooks" / "return_check.py"
SCRIPT = PLUGIN / "scripts" / "return-check.py"
SIX = "## Understanding\nfix the header\n## Files\n- src/mail.py\n## Changes / Plan\nset Reply-To\n## Validation\n`pytest -q` exit 0\n## Risks\n- none\n## Next Step\nreview\n"


def report(role, model, obj, sections=SIX):
    return "[%s · model: %s]\n%s```json\n%s\n```\n" % (role, model, sections, json.dumps(obj, indent=2))


IMPLEMENT = {"status": "completed", "task_id": "1.2", "summary": "done", "pattern_reference": "src/mail.py:40",
             "extra": {"files_modified": 1, "test_results": {"total": 3, "passed": 3, "failed": 0,
                                                             "commands": [{"cmd": "pytest -q", "exit": 0, "evidence_path": ".cm-tmp/1.2/test.log"}]}}}
SCOUT = {"status": "completed", "mode": "scan", "hits": [], "handoff": {"understanding": "", "files_touched_or_referenced": [],
                                                                         "changes_or_findings": "", "validation_done": "", "risks": [], "next_step": ""}}
BRIEF_WITH_REFS = 'sub_question: hook cap\n"doc_sources": ["search: hook cap"], "cache_refs": ["research-cache/tool-x-hooks.md"]'


def load_checker():
    spec = importlib.util.spec_from_file_location("return_check_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_transcript(path, brief, tools=()):
    """A subagent transcript as Claude Code writes it: the brief first, then one assistant line per tool call."""
    lines = []
    lines.append({"type": "user", "timestamp": "2026-11-23T01:00:00.000Z", "message": {"role": "user", "content": brief}})
    lines += [{"type": "assistant", "message": {"model": "claude-sonnet-4-6", "id": "m%d" % n,
                                                "content": [{"type": "tool_use", "id": "t%d" % n, "name": name, "input": {}}]}} for n, name in enumerate(tools)]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


class Shape(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="agent-hub-return-")
        self.addCleanup(tmp.cleanup)
        self.cwd = Path(tmp.name).resolve()
        self.check = load_checker().problems

    def test_conforming_returns_have_no_problem(self):
        self.assertEqual(self.check(report("implement", "sonnet", IMPLEMENT), "implement", str(self.cwd)), [])
        self.assertEqual(self.check(report("brainstorm", "opus", {"status": "needs_user_input", "user_questions": []}), "brainstorm", str(self.cwd)), [])
        self.assertEqual(self.check("[scout · model: sonnet]\n" + json.dumps(SCOUT), "scout", str(self.cwd)), [])
        self.assertEqual(self.check(report("implement", "sonnet", IMPLEMENT).replace("```json", "```jsonc"), "implement", str(self.cwd)), [])

    def test_each_missing_part_is_named(self):
        good = report("implement", "sonnet", IMPLEMENT)
        cases = {
            good.replace("[implement · model: sonnet]", "**[implement · model: sonnet]**"): "line 1 must be exactly `[implement · model: sonnet]`",
            good.replace("model: sonnet", "model: opus"): "line 1 must be exactly `[implement · model: sonnet]`",
            good.replace("## Risks\n- none\n", ""): "section `## Risks` is missing or out of order",
            good.replace("## Files", "## Validation").replace("## Validation\n`pytest", "## Files\n`pytest"): "section `## Changes / Plan` is missing or out of order",
            good.split("```json")[0]: "must end with one fenced ```json block",
            good.replace('"status": "completed"', '"status": "completed", // done'): "does not parse as JSON",
            good.replace('"status": "completed"', '"status": "done"'): "`status` must be one of: completed, in_progress",
            good.replace('"src/mail.py:40"', '"see the mail module"'): "`pattern_reference` must be the `file:line`",
            good.replace('"cmd": "pytest -q",', ""): "`extra.test_results.commands[]` must list",
        }
        for text, want in cases.items():
            found = self.check(text, "implement", str(self.cwd))
            self.assertTrue(any(want in line for line in found), (want, found))

    def test_the_model_that_ran_wins_over_the_agent_file(self):
        opus = report("implement", "opus", IMPLEMENT)
        self.assertEqual(self.check(opus, "implement", str(self.cwd), model="opus"), [])
        self.assertNotEqual(self.check(opus, "implement", str(self.cwd)), [])

    def test_a_blocking_status_is_held_to_the_shape_only(self):
        self.assertEqual(self.check(report("reviewer", "opus", {"status": "needs_user_input"}), "reviewer", str(self.cwd)), [])

    def test_reviewer_needs_a_verdict_word_and_a_review_file_with_a_round_section(self):
        (self.cwd / "review.md").write_text("# Review\n\nno round here\n", encoding="utf-8")
        obj = {"status": "completed", "verdict": "LGTM", "review_file": "%s ## Round 1 · independent" % (self.cwd / "review.md")}
        found = self.check(report("reviewer", "opus", obj), "reviewer", str(self.cwd))
        self.assertEqual(len(found), 2, found)
        (self.cwd / "review.md").write_text("# Review\n\n## Round 1 · independent\n", encoding="utf-8")
        obj["verdict"] = "needs_changes"
        self.assertEqual(self.check(report("reviewer", "opus", obj), "reviewer", str(self.cwd)), [])

    def test_test_needs_a_gate_commands_with_evidence_and_clean_evidence(self):
        kept = self.cwd / "evidence" / "login.txt"
        kept.parent.mkdir()
        kept.write_text("status 200\n", encoding="utf-8")
        obj = {"status": "completed", "gate": "GREEN", "cleanup_done": True,
               "commands": [{"cmd": "npx playwright test", "exit": 0, "evidence_path": "evidence/login.txt"},
                            {"cmd": "curl -s localhost", "exit": 0, "evidence_path": str(self.cwd / ".cm-tmp" / "1.2" / "curl.txt")}]}
        self.assertEqual(self.check(report("test", "sonnet", obj), "test", str(self.cwd)), [])
        obj["cleanup_done"] = False
        self.assertIn("`evidence_path` %s does not exist" % (self.cwd / ".cm-tmp" / "1.2" / "curl.txt"), self.check(report("test", "sonnet", obj), "test", str(self.cwd)))
        obj["cleanup_done"] = True
        (kept.parent / "network.txt").write_text("token: ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8\n", encoding="utf-8")
        obj["commands"].append({"cmd": "curl -s localhost/net", "exit": 0, "evidence_path": "evidence/network.txt"})
        self.assertTrue(any("secret-scan found a secret" in line for line in self.check(report("test", "sonnet", obj), "test", str(self.cwd))))
        self.assertIn("`gate` must be `GREEN` or `RED`", self.check(report("test", "sonnet", {"status": "completed", "gate": "green"}), "test", str(self.cwd)))

    def test_scout_returns_the_raw_object(self):
        fenced = "[scout · model: sonnet]\n```json\n" + json.dumps(SCOUT) + "\n```"
        self.assertTrue(any("one raw JSON object" in line for line in self.check(fenced, "scout", str(self.cwd))))
        bare = dict(SCOUT, handoff={"understanding": ""})
        self.assertTrue(any("`handoff` lacks: files_touched_or_referenced" in line for line in self.check("[scout · model: sonnet]\n" + json.dumps(bare), "scout", str(self.cwd))))

    def test_status_values_come_from_the_agent_file(self):
        model, statuses = load_checker().agent_facts("devops")
        self.assertEqual(model, "opus")
        self.assertIn("needs_approval", statuses)
        self.assertEqual(load_checker().agent_facts("nobody"), ("", []))

    def elsewhere(self):
        """Two folders: `session` (the hook payload cwd, where a subagent's shell resets to) and `target` (the repo the work happened in)."""
        session, target = self.cwd / "session", self.cwd / "target"
        for folder in (session, target):
            folder.mkdir()
        return session, target

    def test_a_relative_path_not_found_under_cwd_is_unverifiable_not_a_problem(self):
        session, target = self.elsewhere()
        (target / ".cm-tmp" / "T1").mkdir(parents=True)
        (target / ".cm-tmp" / "T1" / "run.log").write_text("ok\n", encoding="utf-8")
        (target / "review.md").write_text("# Review\n\nno round here\n", encoding="utf-8")
        tested = {"status": "completed", "gate": "GREEN", "task_id": "T1", "cleanup_done": False,
                  "commands": [{"cmd": "pytest", "exit": 0, "evidence_path": ".cm-tmp/T1/run.log"}]}
        reviewed = {"status": "completed", "verdict": "pass", "review_file": "review.md ## Round 1 · independent"}
        for cwd in (session, self.cwd / "absent"):
            self.assertEqual(self.check(report("test", "sonnet", tested), "test", str(cwd)), [])
            self.assertEqual(self.check(report("reviewer", "opus", reviewed), "reviewer", str(cwd)), [])
        self.assertEqual(self.check(report("test", "sonnet", tested), "test", str(target)), [])
        self.assertTrue(any("`## Round {n}" in line for line in self.check(report("reviewer", "opus", reviewed), "reviewer", str(target))))

    def test_a_relative_evidence_path_that_resolves_is_still_scanned(self):
        _, target = self.elsewhere()
        (target / "evidence").mkdir()
        (target / "evidence" / "net.txt").write_text("token: ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8\n", encoding="utf-8")
        tested = {"status": "completed", "gate": "GREEN", "commands": [{"cmd": "x", "exit": 0, "evidence_path": "evidence/net.txt"}]}
        self.assertTrue(any("secret-scan found a secret" in line for line in self.check(report("test", "sonnet", tested), "test", str(target))))

    def test_an_absolute_evidence_path_is_checked_wherever_the_cwd_is(self):
        session, _ = self.elsewhere()
        gone = str(self.cwd / "target" / "gone.txt")
        tested = {"status": "completed", "gate": "GREEN", "commands": [{"cmd": "x", "exit": 0, "evidence_path": gone}]}
        self.assertIn("`evidence_path` %s does not exist" % gone, self.check(report("test", "sonnet", tested), "test", str(session)))

    def test_a_reviewer_that_wrote_no_file_returns_null_review_file(self):
        obj = {"status": "completed", "verdict": "pass", "review_file": None}
        self.assertEqual(self.check(report("reviewer", "opus", obj), "reviewer", str(self.cwd)), [])

    def test_headings_match_by_case_insensitive_prefix_at_a_word_boundary_and_keep_their_order(self):
        loose = SIX.replace("## Changes / Plan", "## Changes / Plan (findings)").replace("## Next Step", "## Next step")
        self.assertEqual(self.check(report("implement", "sonnet", IMPLEMENT, loose), "implement", str(self.cwd)), [])
        for broken in (SIX.replace("## Files", "## Filesystem"), SIX.replace("## Risks", "## Riskier")):
            self.assertTrue(any("is missing or out of order" in line for line in self.check(report("implement", "sonnet", IMPLEMENT, broken), "implement", str(self.cwd))))

    def test_a_non_integer_files_modified_does_not_crash(self):
        for value in (["a.py"], "2", None, True):
            obj = dict(IMPLEMENT, extra=dict(IMPLEMENT["extra"], files_modified=value))
            self.assertIsInstance(self.check(report("implement", "sonnet", obj), "implement", str(self.cwd)), list)

    def test_a_secret_scan_that_cannot_read_the_evidence_is_not_a_problem(self):
        locked = self.cwd / "locked.txt"
        locked.write_text("x\n", encoding="utf-8")
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o600)
        tested = {"status": "completed", "gate": "GREEN", "commands": [{"cmd": "x", "exit": 0, "evidence_path": str(locked)}]}
        self.assertEqual(self.check(report("test", "sonnet", tested), "test", str(self.cwd)), [])

    def test_only_the_cited_evidence_files_are_scanned_not_their_folder(self):
        folder = self.cwd / "evidence"
        folder.mkdir()
        (folder / "mine.txt").write_text("status 200\n", encoding="utf-8")
        (folder / "theirs.txt").write_text("token: ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8\n", encoding="utf-8")
        tested = {"status": "completed", "gate": "GREEN", "commands": [{"cmd": "x", "exit": 0, "evidence_path": "evidence/mine.txt"}]}
        self.assertEqual(self.check(report("test", "sonnet", tested), "test", str(self.cwd)), [])

    def reviewed(self, review_file, cwd=None):
        obj = {"status": "completed", "verdict": "pass", "review_file": review_file}
        return self.check(report("reviewer", "opus", obj), "reviewer", str(cwd or self.cwd))

    def test_a_review_file_cited_with_a_suffix_other_than_the_heading_is_read_by_its_path(self):
        good, bare = self.cwd / "review.md", self.cwd / "norounds.md"
        good.write_text("## Round 1 · independent\n", encoding="utf-8")
        bare.write_text("no round\n", encoding="utf-8")
        for suffix in (":1", ":12-20", " § Round 1", " (round 1)", " ## Round 1"):
            self.assertEqual(self.reviewed(str(good) + suffix), [], suffix)
            self.assertEqual(self.reviewed("review.md" + suffix), [], suffix)
            self.assertTrue(any("`## Round {n}" in line for line in self.reviewed(str(bare) + suffix)), suffix)
        self.assertEqual(self.reviewed(str(self.cwd / "gone.md") + ":1"), [])   # nothing there to read: unverifiable

    def test_a_review_file_that_is_a_folder_is_unverifiable(self):
        (self.cwd / "docs").mkdir()
        self.assertEqual(self.reviewed(str(self.cwd / "docs")), [])

    def test_a_review_file_that_is_a_fifo_never_hangs(self):
        os.mkfifo(self.cwd / "fifo.md")
        text = self.cwd / "r.txt"
        text.write_text(report("reviewer", "opus", {"status": "completed", "verdict": "pass", "review_file": "fifo.md"}), encoding="utf-8")
        res = subprocess.run([sys.executable, "-B", str(SCRIPT), str(text), "--cwd", str(self.cwd)], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_the_secret_scan_walks_only_regular_files_and_the_tasks_own_confined_run_folder(self):
        secret = "token: ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8\n"
        work = self.cwd / "work"
        for sub in ("other", ".cm-tmp/T1", ".cm-tmp/OTHER"):
            (work / sub).mkdir(parents=True)
        (work / ".cm-tmp" / "T1" / "run.log").write_text("ok\n", encoding="utf-8")
        for leak in (work / "other" / "leak.txt", work / ".cm-tmp" / "OTHER" / "leak.txt", self.cwd / "leak.txt"):
            leak.write_text(secret, encoding="utf-8")

        def tested(evidence, task_id="T1"):
            obj = {"status": "completed", "gate": "GREEN", "task_id": task_id, "commands": [{"cmd": "x", "exit": 0, "evidence_path": evidence}]}
            return [line for line in self.check(report("test", "sonnet", obj), "test", str(work)) if "secret-scan" in line]
        for evidence in (".", ".cm-tmp"):
            self.assertEqual(tested(evidence), [], evidence)
        for task_id in ("../..", "..", ".", str(self.cwd), "T1/../OTHER"):
            self.assertEqual(tested(".cm-tmp/T1/run.log", task_id), [], task_id)
        self.assertEqual(tested(".cm-tmp/T1/run.log"), [])
        (work / ".cm-tmp" / "T1" / "extra.txt").write_text(secret, encoding="utf-8")
        self.assertTrue(tested(".cm-tmp/T1/run.log"))   # inside the task's own run folder
        (work / ".cm-tmp" / "T1" / "extra.txt").unlink()
        self.assertTrue(tested("other/leak.txt"))   # a cited regular file

    def test_a_pattern_reference_may_carry_a_note_after_the_file_and_line(self):
        for value in ("src/mail.py:76 (VirtualList + the hook)", "src/mail.py:40-52 neighbour", "src/mail.py:40"):
            obj = dict(IMPLEMENT, pattern_reference=value)
            self.assertEqual(self.check(report("implement", "sonnet", obj), "implement", str(self.cwd)), [], value)
        for value in ("see src/mail.py:40", "src/mail.py", "", None):
            obj = dict(IMPLEMENT, pattern_reference=value)
            self.assertTrue(any("`pattern_reference`" in line for line in self.check(report("implement", "sonnet", obj), "implement", str(self.cwd))), value)

    def test_the_last_closed_json_block_is_found_in_one_linear_pass(self):
        checker = load_checker()
        old = re.compile(r"(?msi)^```jsonc?[ \t]*\r?\n(.*?)^```[ \t]*\r?$")
        for body in ("```json\n{\"a\": 1}\n```\n", "x\n```json\n1\n```\ny\n```jsonc\n2\n```\n```json\n3\n", "```JSON\r\n{}\r\n```\r\n",
                     "```json\n```\n", "```json\n1\n```json\n2\n```\n", "```\nplain\n```\n```json\n4\n```  \n", "```jsonx\n5\n```\n", "no fence", "```json\n6\n```"):
            found = old.findall(body)
            self.assertEqual(checker.last_json_block(body), found[-1] if found else None, body)

    def test_unclosed_json_fences_do_not_make_the_check_slow(self):
        big = "[reviewer · model: opus]\n" + SIX + "```json\n{\n" * 20000
        start = time.time()
        found = self.check(big, "reviewer", str(self.cwd))
        self.assertLess(time.time() - start, 1.0)
        self.assertTrue(any("must end with one fenced" in line for line in found))

    def test_devops_validation_wording_is_not_checked(self):
        sections = SIX.replace("`pytest -q` exit 0", "checked the log by eye")
        self.assertEqual(self.check(report("devops", "opus", {"status": "completed"}, sections), "devops", str(self.cwd)), [])

    def test_an_internal_error_exits_2_with_one_stderr_line(self):
        module = load_checker()
        module.problems = lambda *a, **k: 1 / 0
        good = self.cwd / "good.md"
        good.write_text(report("brainstorm", "opus", {"status": "completed"}), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = module.main([str(good)])
        self.assertEqual((code, len(err.getvalue().splitlines())), (2, 1))


class Cli(unittest.TestCase):
    def test_exit_codes_and_last_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / "good.md", Path(tmp) / "bad.md"
            good.write_text(report("brainstorm", "opus", {"status": "completed"}), encoding="utf-8")
            bad.write_text("Here is my report.\n", encoding="utf-8")
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True, text=True, timeout=30)
            res = run(str(good))
            self.assertEqual((res.returncode, res.stdout), (0, "return-check: brainstorm: 0 problems\n"))
            self.assertEqual(run(str(bad)).returncode, 2)
            res = run(str(bad), "--agent", "test")
            self.assertEqual(res.returncode, 1)
            self.assertEqual(res.stdout.splitlines()[-1], "return-check: test: 3 problems")
            self.assertEqual(run().returncode, 2)
            self.assertEqual(run(str(Path(tmp) / "absent.md")).returncode, 2)


class Hook(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="agent-hub-return-hook-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()

    def env(self, **env_extra):
        env = {**os.environ, "AGENT_HUB_STATE_DIR": str(self.tmp), "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
        for key in ("AGENT_HUB_MOMENTS", "AGENT_HUB_BLOCKS", "CLAUDE_PLUGIN_OPTION_MOMENT_HOOKS", "CLAUDE_PLUGIN_OPTION_HOOK_BLOCKS"):
            env.pop(key, None)
        env.update(env_extra)
        return env

    def payload(self, text, agent="a1", role="brainstorm", active=False, transcript=None):
        data = {"session_id": "s1", "agent_id": agent, "agent_type": "agent-hub:" + role, "cwd": str(self.tmp),
                "last_assistant_message": text, "stop_hook_active": active}
        if transcript:
            data["agent_transcript_path"] = str(transcript)
        return data

    def stop(self, text, agent="a1", role="brainstorm", active=False, transcript=None, **env_extra):
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(self.payload(text, agent, role, active, transcript)),
                              capture_output=True, text=True, env=self.env(**env_extra), timeout=30)

    def test_a_conforming_message_passes_silently(self):
        res = self.stop(report("brainstorm", "opus", {"status": "completed"}))
        self.assertEqual((res.returncode, res.stdout, res.stderr), (0, "", ""))

    def test_two_refusals_name_what_is_missing_then_the_message_goes_through_marked(self):
        for active in (False, True):
            res = self.stop("All done, see above.", active=active)
            self.assertEqual(res.returncode, 2)
            self.assertIn("- line 1 must be exactly `[brainstorm · model: opus]`", res.stderr)
            self.assertIn("- section `## Understanding` is missing", res.stderr)
            self.assertEqual(res.stdout, "")
        third = self.stop("All done, see above.", active=True)
        self.assertEqual(third.returncode, 0)
        out = json.loads(third.stdout)
        self.assertIn("the brainstorm agent returned with 3 unfixed problems", out["systemMessage"])
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SubagentStop")
        fourth = self.stop("All done, see above.", active=True)
        self.assertEqual((fourth.returncode, fourth.stdout), (0, ""))

    def test_a_fixed_message_after_one_refusal_passes(self):
        self.assertEqual(self.stop("no shape").returncode, 2)
        self.assertEqual(self.stop(report("brainstorm", "opus", {"status": "completed"}), active=True).returncode, 0)

    def handback_transcript(self, name, message, text_after=False):
        path = self.tmp / name
        rows = [{"type": "assistant", "message": {"id": "m1", "model": "claude-opus-5", "content": [
            {"type": "tool_use", "id": "t1", "name": "SubagentHandback", "input": {"message": message}}]}}]
        if text_after:
            rows.append({"type": "assistant", "message": {"id": "m2", "model": "claude-opus-5", "content": [{"type": "text", "text": "more"}]}})
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_an_empty_final_message_passes_silently(self):
        for n, text in enumerate(("", "   \n", None)):
            res = self.stop(text, agent="e%d" % n)
            self.assertEqual((res.returncode, res.stdout, res.stderr), (0, "", ""))

    def test_a_handback_ending_checks_the_handback_message_and_never_refuses(self):
        good = self.stop("", agent="h1", transcript=self.handback_transcript("h1.jsonl", report("brainstorm", "opus", {"status": "completed"})))
        self.assertEqual((good.returncode, good.stdout, good.stderr), (0, "", ""))
        for active in (False, True):
            bad = self.stop("[brainstorm · model: opus]", agent="h2", active=active,
                            transcript=self.handback_transcript("h2.jsonl", "All done, see above."))
            self.assertEqual((bad.returncode, bad.stderr), (0, ""))
        first = self.stop("", agent="h3", transcript=self.handback_transcript("h3.jsonl", "All done, see above."))
        self.assertIn("the brainstorm agent returned with", json.loads(first.stdout)["systemMessage"])

    def test_text_after_a_handback_is_checked_and_refused_as_before(self):
        res = self.stop("no shape", agent="h4", transcript=self.handback_transcript("h4.jsonl", "x", text_after=True))
        self.assertEqual(res.returncode, 2)
        self.assertIn("section `## Understanding` is missing", res.stderr)

    def test_stop_hook_active_with_no_recorded_block_counts_as_one(self):
        self.assertEqual(self.stop("no shape", agent="lost", active=True).returncode, 2)
        self.assertEqual(self.stop("no shape", agent="lost", active=True).returncode, 0)

    def test_counts_are_per_spawn(self):
        for agent in ("a1", "a2"):
            self.assertEqual(self.stop("no shape", agent=agent).returncode, 2)

    def test_concurrent_stops_of_one_spawn_refuse_at_most_twice(self):
        wrapper = ("import os, runpy, sys, time\ngo = sys.argv[1]\nwhile not os.path.exists(go): time.sleep(0.0005)\n"
                   "sys.argv = [%r]\nrunpy.run_path(%r, run_name='__main__')" % (str(HOOK), str(HOOK)))
        for round_no in range(5):
            go = self.tmp / ("go%d" % round_no)
            data = json.dumps(self.payload("no shape", agent="race%d" % round_no))
            procs = [subprocess.Popen([sys.executable, "-c", wrapper, str(go)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True, env=self.env()) for _ in range(6)]
            for proc in procs:
                proc.stdin.write(data)
                proc.stdin.close()
            time.sleep(0.3)
            go.write_text("go")
            codes = []
            for proc in procs:
                proc.stdout.read()
                proc.stderr.read()
                codes.append(proc.wait(timeout=30))
            self.assertEqual(sorted(codes), [0, 0, 0, 0, 2, 2], "round %d" % round_no)

    def test_switches_and_failures_let_everything_through(self):
        self.assertEqual(self.stop("no shape", AGENT_HUB_MOMENTS="0").returncode, 0)
        res = self.stop("no shape", agent="b1", AGENT_HUB_BLOCKS="0")
        self.assertEqual(res.returncode, 0)
        self.assertIn("unfixed problems", res.stdout)
        self.assertEqual(self.stop("no shape", agent="b2", CLAUDE_PLUGIN_OPTION_HOOK_BLOCKS="off").returncode, 0)
        self.assertEqual(self.stop("no shape", agent="b3", AGENT_HUB_STATE_DIR="/dev/null/nope").returncode, 0)
        self.assertEqual(self.stop("no shape", role="unknown-role").returncode, 0)
        self.assertEqual(self.stop("", agent="b4").returncode, 0)
        res = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0)

    def test_the_model_word_is_read_from_the_transcript(self):
        transcript = self.tmp / "agent.jsonl"
        transcript.write_text(json.dumps({"type": "user", "timestamp": "2026-11-23T01:00:00.000Z"}) + "\n"
                              + json.dumps({"type": "assistant", "message": {"model": "claude-opus-4-8", "id": "m1"}}) + "\n", encoding="utf-8")
        checker = load_checker()
        self.assertEqual(checker.transcript_facts(str(transcript)), "opus")
        self.assertIsNone(checker.transcript_facts(str(self.tmp / "absent.jsonl")))
        self.assertIsNone(checker.transcript_facts(None))

    def test_implement_completed_with_an_old_head_in_the_session_repo_is_not_refused(self):
        env = {**os.environ, "GIT_AUTHOR_DATE": "2026-11-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-01T00:00:00Z"}
        for args in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "old"]):
            subprocess.run(["git", "-C", str(self.tmp), *args], check=True, env=env, capture_output=True)
        transcript = write_transcript(self.tmp / "i.jsonl", "task 1.2")
        self.assertEqual(self.stop(report("implement", "sonnet", IMPLEMENT), role="implement", transcript=transcript).returncode, 0)

    def test_a_tool_result_that_mentions_another_model_does_not_change_the_verdict(self):
        transcript = write_transcript(self.tmp / "m.jsonl", "task 1.2")
        with open(transcript, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"type": "user", "message": {"role": "user", "content": "ok"}, "toolUseResult": {"model": "claude-opus-4-8"}}) + "\n")
        self.assertEqual(self.stop(report("implement", "sonnet", IMPLEMENT), role="implement", transcript=transcript).returncode, 0)

    def test_a_scout_that_searched_past_its_cache_refs_and_lists_none_goes_through(self):
        searched = write_transcript(self.tmp / "s.jsonl", BRIEF_WITH_REFS, ["Read", "WebSearch"])
        res = self.stop("[scout · model: sonnet]\n" + json.dumps(dict(SCOUT, cache_used=[])), agent="s1", role="scout", transcript=searched)
        self.assertEqual((res.returncode, res.stderr), (0, ""))

    def test_hooks_json_runs_it_on_agent_hub_subagents_only(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]["SubagentStop"]
        self.assertEqual([(g["matcher"], [h["command"] for h in g["hooks"]]) for g in hooks],
                         [("^agent-hub:", ['python3 "${CLAUDE_PLUGIN_ROOT}/hooks/return_check.py"'])])


if __name__ == "__main__":
    unittest.main()
