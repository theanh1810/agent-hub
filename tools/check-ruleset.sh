#!/usr/bin/env bash
# Ruleset invariants as runnable checks. Every check prints the measured value and the
# expected one, so a PASS is evidence rather than an assertion. Exits 1 on any FAIL.
#
# Counting is done in python3 on purpose: `wc -l < f`, `diff a b` and
# `LC_ALL=C grep -c '[^[:print:]]'` all exit 0 with a wrong answer under the rtk hook
# (RTK.md § Commands that exit 0 with a wrong result). A whole-file `grep -c` answers a
# different question than a per-section count, so every range is sliced before counting.
#
# Repo layout: ROOT is the plugin folder plugins/agent-hub; the injected core is rules/core.md.
# Run it as `python3 tools/check.py ruleset` or `bash tools/check-ruleset.sh [PLUGIN_ROOT]`.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${1:-$REPO/plugins/agent-hub}"
[ -f "$ROOT/rules/core.md" ] || { echo "FATAL: no plugins/agent-hub/rules/core.md under $ROOT"; exit 2; }
exec python3 - "$ROOT" <<'PY'
import ast, os, re, sys, glob, fnmatch, subprocess
import yaml

ROOT = sys.argv[1]
# Excluded by PATH, never by count: these hold deliberate copies and archives whose
# number changes as work lands (a count went stale once already: 16 kept files, not 12).
# `docs/plan|reviews|audits|analysis|changes|brainstorm` are records that quote the rules verbatim; counting them
# as rule sources turns every review artifact into a duplicate-statement failure.
# SKIP means "not a rule SOURCE", not "never read": `docs/plan/` is read as `records()` below
# by the checks that resolve a pointer. Widening SKIP itself is not the way to add a corpus --
# it also feeds `no_bak_suffix_files`, which reads every file rather than the rule files, and
# the plan id `docs/plan/config-bundle-v2` is a name, not a versioned copy of anything.
SKIP = ('.cm-tmp/', 'worktrees/', 'backups/', 'plugins/', 'node_modules/', '.git/',
        'docs/plan/', 'docs/reviews/', 'docs/audits/', 'docs/analysis/', 'docs/changes/', 'docs/brainstorm/',  # scrub-allow: path literal in the skip list
        # harness-owned per-job scratch `jobs/{job_id}/tmp/`, the same class as
        # `.cm-tmp/`: a background job's working files are not ruleset artifacts.
        'jobs/')
# The record roots: trees that QUOTE the rules while describing work. `docs/plan/` and
# `docs/changes/` -- reviews, audits and analysis are the same class and can join it once their
# pointers are worth gating.
RECORDS = ('docs/plan/', 'docs/changes/')

def rel(p):            return os.path.relpath(p, ROOT).replace(os.sep, '/')
def read(p):
    """A file the package does not ship reads as empty, so the check that names it reports a FAIL instead of a traceback."""
    try:
        return open(os.path.join(ROOT, p), encoding='utf-8', errors='replace').read()
    except FileNotFoundError:
        return ''

def lines(p):          return read(p).splitlines()
def files(pat):        return sorted(rel(p) for p in glob.glob(os.path.join(ROOT, pat), recursive=True) if not is_variant(rel(p)))

def ruleset():
    """Every hand-written rule file -- a file that STATES a rule. Third-party and archived
    trees are out by path, and so are the records, which quote rules rather than state them."""
    out = []
    for p in glob.glob(os.path.join(ROOT, '**/*.md'), recursive=True):
        r = rel(p)
        if not any(s in r + '/' for s in SKIP) and not is_variant(r):
            out.append(r)
    return sorted(out)

def records():
    """Every record -- a file that QUOTES a rule while describing work, under RECORDS.

    A record is not a second statement of the rule it quotes, so the checks that COUNT
    statements read `ruleset()` and never this. Measured 2026-09-23, reading records as rule
    sources reddens three checks on quotation alone and finds no defect: `viewport enum` 7
    copies where 6 are one plan's prose, `no_eager_imports` 6 hits that are all `@file`
    inside a worked example, `budgets_and_self_counts_agree` 1 hit on a plan paragraph
    restating §6. The checks that resolve a POINTER read `scanned()` instead, because a
    pointer that no longer resolves is a defect wherever it is written."""
    out = []
    for root in RECORDS:
        out += [rel(p) for p in glob.glob(os.path.join(ROOT, root, '**/*.md'), recursive=True)]
    return sorted(out)

def scanned():
    """`ruleset() + records()` -- every file whose POINTERS are gated, rule or record."""
    return sorted(ruleset() + records())

# The record whose text is v1.1 byte for byte (SPEC-DEVIATIONS.md §27). Its pointers describe
# the tree v1.1 was written against; rewriting them would end the byte identity.
VERBATIM_RECORDS = ('docs/plan/ruleset-refactor/SPEC.md',)
# Quoted text inside a RECORD line: `` double-backtick `` spans, "..." and “...”, and a
# shell-quoted '...' string. A straight quote mark opens only after start, whitespace, `(`, `*`
# or a backtick and closes only before end, whitespace or `),.;:*`, so an inch mark (`5"`) or
# a word-leading apostrophe (`'90s`) does not open a span. A '...' span hides only a match that
# starts right after its opening mark -- a grep literal -- so `'90s ... users'` hides nothing.
QUOTED_SPAN = re.compile(r"``.+?``|(?:^|(?<=[\s(`*]))\"[^\"\n]+\"(?=$|[\s`),.;:*])"
                         r"|\u201c[^\u201d\n]+\u201d")
SHELL_QUOTE = re.compile(r"(?:^|(?<=[\s(`]))'[^'\n]+'(?=$|[\s`),.;:])")
CODE_SPAN   = re.compile(r'(?<!`)`([^`\n]+)`(?!`)')
PATH_CHARS  = re.compile(r'[~A-Za-z0-9_./-]*')
_record_set = None

def pointer_lines(f):
    """Yield `(line_no, line, quoted)` for the three pointer checks; `quoted(pos)` is True
    where a match starting at `pos` is quoted text rather than a pointer.

    Decided 2026-09-24 by the user (EXCEPTIONS-vs-v1.1.md X67): after cleanup-B converted 300
    record pointers to historical form, 56 hits left were no pointer at all -- verbatim
    quotations of old rule text, grep strings, code blocks, and the v1.1 copy. The skips apply
    to RECORDS only; a rule file is read in full, fences and quotes included. In a record:
    `VERBATIM_RECORDS` yield nothing; fenced blocks yield nothing; `QUOTED_SPAN` is quoted; and
    inside a single-backtick code span a match counts only when the span text before it is
    path characters -- `agents/x.md § Y` and `rules/core.md §6` are pointers,
    `The review file follows CLAUDE.md §16.1` and `(CLAUDE.md §20.2)` are quoted literals.
    A `SHELL_QUOTE` span hides only a match starting right after its opening mark. Outside
    these spans nothing in a record is skipped, and a stray quote mark or apostrophe opens no
    span (see QUOTED_SPAN), so a pointer in plain prose is still checked."""
    global _record_set
    if _record_set is None:
        _record_set = set(records())
    rec = f in _record_set
    if rec and f in VERBATIM_RECORDS:
        return
    fence = False
    for i, l in enumerate(lines(f), 1):
        if rec and l.lstrip().startswith('```'):
            fence = not fence
            continue
        if rec and fence:
            continue
        if not rec:
            yield i, l, (lambda pos: False)
            continue
        spans = [(m.start(), m.end(), 'quote') for m in QUOTED_SPAN.finditer(l)]
        spans += [(m.start(), m.end(), 'shell') for m in SHELL_QUOTE.finditer(l)]
        spans += [(m.start(1), m.end(1), 'code') for m in CODE_SPAN.finditer(l)]
        def quoted(pos, spans=spans, l=l):
            for a, b, kind in spans:
                if not a <= pos < b:
                    continue
                if kind == 'quote':
                    return True
                if kind == 'shell' and pos == a + 1:
                    return True
                if kind == 'code' and PATH_CHARS.fullmatch(l[a:pos]) is None:
                    return True
            return False
        yield i, l, quoted

def section(text, head_re):
    """Slice a markdown section: its heading to the next heading of the same depth or
    shallower. Scoping before counting is the whole point — RTK.md records twelve plan
    `verification` commands that grepped a whole file and answered a different question."""
    m = re.search(head_re, text, re.M)
    if not m:
        return None
    depth = len(re.match(r'#*', m.group(0)).group(0))
    tail = text[m.end():]
    nxt = re.search(r'^#{1,%d} ' % depth, tail, re.M)
    return m.group(0) + (tail[:nxt.start()] if nxt else tail)

def router_table():
    """CLAUDE.md §2.1A table A: {blocking status -> the agents that may return it}."""
    seg = re.search(r'\*\*A\. Blocking `status`.*?\*\*B\. Booleans', read('refs/gate-handling.md'), re.S)
    out = {}
    for l in (seg.group(0) if seg else '').splitlines():
        if l.count('|') < 3:
            continue
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        st = re.findall(r'`([a-z_]+)`', c[0])
        if st:
            out[st[0]] = re.findall(r'[a-z]+', c[1])
    return out

def model_table(text, head_re, label):
    """{agent -> model} from the one `| Agent | Model |` table under head_re. Column pairs come
    from the header row, never from position: CLAUDE.md §0 is TWO `Agent | Model` pairs on one
    line, and an agent name backticked inside another table's prose column is not a row."""
    ls = (section(text, head_re) or '').splitlines()
    hdr = [i for i, l in enumerate(ls) if re.match(r'^\|\s*Agent\s*\|\s*Model\s*\|', l)]
    if len(hdr) != 1:
        return None, f"{label}: {len(hdr)} `| Agent | Model |` header rows, expected 1"
    head = [c.strip() for c in ls[hdr[0]].strip().strip('|').split('|')]
    pairs = [(i, i + 1) for i in range(len(head) - 1)
             if head[i] == 'Agent' and head[i + 1] == 'Model']
    out = {}
    for l in ls[hdr[0] + 2:]:
        if not l.startswith('|'):
            break
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        for a, m in pairs:
            if m < len(c) and re.fullmatch(r'`(?:agent-hub:)?[a-z-]+`', c[a]):
                out[c[a].strip('`').replace('agent-hub:', '')] = c[m].replace('*', '').split('·')[0].strip()
    return (out, None) if out else (None, f"{label}: 0 rows parsed")

# Roles that live in an optional plugin or were removed: a row naming one is not a defect of this package.
NOT_SHIPPED = {'auditor', 'analyst'}

CHECKS = []
def check(fn):
    CHECKS.append(fn); return fn

# ---------------------------------------------------------------- checks

@check
def frontmatter_parses():
    """Every agent and command frontmatter loads. An unquoted ': ' inside a description
    breaks yaml.safe_load, and the harness then reads no frontmatter at all."""
    try:
        import yaml
    except ImportError:
        return (False, "pyyaml not installed", "pyyaml importable")
    bad = []
    for f in files('agents/*.md') + files('commands/*.md'):
        t = read(f)
        if not t.startswith('---'):
            bad.append(f"{f}: no frontmatter"); continue
        try:
            if yaml.safe_load(t.split('---')[1]) is None:
                bad.append(f"{f}: empty")
        except Exception as e:
            bad.append(f"{f}: {str(e).splitlines()[0]}")
    return (not bad, f"{len(bad)} broken: {bad}", "0 broken")

@check
def model_assignment_agrees():
    """The model an agent runs on is hand-written in four places and nothing compared them.
    Only the frontmatter is read by the harness: frontmatter `sonnet` under a CLAUDE.md that
    says `opus` means devops RUNS sonnet while the ruleset claims opus. §0 marks that one HARD
    do-not-downgrade and records that it was silently downgraded in the 2026-08-31 package.

    § Worker registry holds 9 rows to the other three sources' 10, and the gap is deliberate:
    it lists the workers orchestrator dispatches, and orchestrator does not dispatch itself.
    That single absence is exempted BY NAME with its reason, so every other missing row stays a
    FAIL — which is what makes deleting a row from any of the three tables turn the gate red.

    A value may carry a suffix after a `·` (none does since the engine clause was removed),
    so the model token is cut at the `·`; `**opus**` loses its emphasis the
    same way. A source that parses to no rows at all is a FAIL, never a pass: that is the way
    this check would otherwise go quietly green after someone reformats a table.

    The FLOW.md §1 diagram is guarded here, and the guard is SLICED to the §1 fence. A whole-file
    grep for a model token hits 12 lines, 11 of them the §2 table this same check REQUIRES, so a
    whole-file guard would forbid what the rest of the check demands; the 12th is prose (measured
    2026-09-20 at FLOW.md:505, and recorded at :507 before an edit moved it, which
    is why the guard slices rather than counts). The fence holds no model tokens because a
    diagram naming a model is a fifth source nobody compares — this keeps it empty."""
    try:
        import yaml
    except ImportError:
        return (False, "pyyaml not installed", "pyyaml importable")
    EXEMPT = ('registry', 'orchestrator',
              'the registry lists the workers orchestrator dispatches, and it dispatches '
              'no orchestrator')
    src, bad = {}, []
    src['frontmatter'] = {os.path.basename(f)[:-3]:
                          (yaml.safe_load(read(f).split('---')[1]) or {}).get('model')
                          for f in files('agents/*.md')}
    for label, path, head in (('CLAUDE.md§0', 'rules/core.md', r'^# 0\. '),
                              ('FLOW.md§2', 'rules/FLOW.md', r'^## 2\. '),
                              ('registry', 'agents/orchestrator.md', r'^## Worker registry')):
        got, err = model_table(read(path), head, label)
        src[label] = got or {}
        if err:
            bad.append(err)
    for a, want in sorted(src['frontmatter'].items()):
        row = {k: (want if (k, a) == EXEMPT[:2] and m.get(a) is None else m.get(a))
               for k, m in src.items()}
        if want is None or any(v != want for v in row.values()):
            bad.append(f"{a}: " + ' '.join(f"{k}={v}" for k, v in row.items()))
    bad += [f"{a}: a row in {k}, but no agents/{a}.md"
            for k, m in src.items() for a in sorted(m) if a not in src['frontmatter'] and a not in NOT_SHIPPED]
    fence = re.search(r'```\n(.*?)```', section(read('rules/FLOW.md'), r'^## 1\. ') or '', re.S)
    in_fence = sorted(set(re.findall(r'(?i)\b(?:opus|sonnet|haiku)\b', fence.group(1) if fence else '')))
    if fence is None:
        bad.append("FLOW.md §1: no fenced diagram to read")
    elif in_fence:
        bad.append(f"FLOW.md §1 fence names {in_fence}")
    return (not bad,
            f"{len(src['frontmatter'])} agents, rows per source: "
            + ', '.join(f"{k}={len(v)}" for k, v in src.items())
            + f", §1 fence={in_fence} | off={bad}",
            f"one model per agent across all four sources; {EXEMPT[0]} carries no "
            f"{EXEMPT[1]} row because {EXEMPT[2]}; the FLOW.md §1 fence names no model")

@check
def no_bak_suffix_files():
    """No version suffix in a filename anywhere in the tree. CLAUDE.md §19.4 bans eight of
    them — `final`, `new`, `v2`, `latest`, `copy`, `backup`, `bak`, `test` — and on a rule file
    any of them is worse than litter: a `*.md.bak` answers every `grep -rn agents/`, so a
    reviewer draws a conclusion from the old content, which is how 3 phantom
    `spec_debt_missing` hits. Git keeps history; filenames do not.

    Scope is every `.bak`, not only `.md.bak`, because a review counted 13 such files
    against §19.4: while this check read markdown alone it could never notice the other 12, and
    its green sat next to that finding reading as though the tree were clean. It read one of
    the eight for the same reason, so `code-style/typescript-v2.md` passed it.

    The eight are matched as suffixes, never as substrings. A substring match reports every
    file with `test` or `copy` anywhere in its name, which is most of the test tree in any repo
    this check later covers. So the word is separator-delimited, must have a real name in front
    of it — `agents/test.md` and `templates/test` are names, not versioned copies of something
    — and may carry a trailing date, which is how the kept `settings.json.bak.20260506_230431`
    is spelled. The dot branch is SPLIT, because the convention that justifies it covers one
    word and not eight: `foo.test.ts` is the JS spelling of a test file, so `test` alone has to
    come last, while a dot-delimited `v2`, `bak`, `copy`, `final`, `new`, `latest` or `backup`
    may carry a trailing extension exactly as a `-`/`_` delimited one does. While all eight had
    to come last, `typescript.v2.md` and `foo.bak.js` passed — one character away from the
    `typescript-v2.md` this widening exists to catch, measured by the W9 review. `handler.test.ts`
    and `planner.md.test.md` stay green; that remainder is declared, not closed.

    KEEP is by path pattern with a reason per entry, never by count: these are on an
    explicit "do not touch" list — they are the user's own config backups, and a check that
    reports them pushes the next session into deleting one to get to green. A count would go
    green again the next time an unrelated file appeared.

    A KEEP entry matching NOTHING is printed as dead, and does not fail: the file it names is the
    user's own backup, so deleting one is legitimate and a FAIL would turn the gate red on a user
    action rather than on a rule breach — the same pressure the do-not-touch list exists to
    remove. Printing it keeps the entry visible to prune, which is what the measured line could
    not show before: an exemption that guards nothing reads exactly like one that guards a file."""
    WORDS = r'final|new|v\d+|latest|copy|backup|bak|test'
    NOT_TEST = r'final|new|v\d+|latest|copy|backup|bak'
    DATED = r'(?:[-._]\d[\d_-]*)?'
    SUFFIX = re.compile(rf'(?<=[^-._])(?:[-_](?:{WORDS}){DATED}(?:\.[A-Za-z0-9]+)?'
                        rf'|\.(?:{NOT_TEST}){DATED}(?:\.[A-Za-z0-9]+)?'
                        rf'|\.test{DATED})$', re.I)
    KEEP = {
        'memory/MEMORY.md.bak':          'user config backup, on the do-not-touch list',
        'settings.json.bak*':            'harness config backups the user chose to keep',
        'settings.json.empty-bak':       'the same harness config backup, spelled with a '
                                         'hyphen; a `.bak` substring never saw it',
        'gitlab-user.txt.bak.20260901':  'commit-identity backup the user chose to keep',
        'hooks/*.bak':                   'hook backups the user chose to keep',
        'hooks/*.bak.*':                 'dated hook backups the user chose to keep',
        'scripts/error-stats.sh.bak-20260907-162500':
            'evidence that an in-tree copy answers a grep with a wrong file:line',
    }
    hits = [f for f in (rel(q) for q in glob.glob(os.path.join(ROOT, '**/*'), recursive=True))
            if SUFFIX.search(os.path.basename(f)) and not any(s in f + '/' for s in SKIP)]
    kept = [f for f in hits if any(fnmatch.fnmatchcase(f, k) for k in KEEP)]
    bad = [f for f in hits if f not in kept]
    dead = [k for k in KEEP if not any(fnmatch.fnmatchcase(f, k) for f in hits)]
    return (not bad, f"{len(bad)} stray: {bad} | {len(kept)} kept by path: {kept}"
            f" | {len(dead)} dead keep: {dead}",
            "0 stray across all eight §19.4 suffixes, each matched as a suffix; deliberate "
            "keeps excluded by path pattern with a reason, never by count, and a keep that "
            "matches nothing printed as dead rather than failed")

@check
def no_eager_imports():
    """No `@file` eager import in the ruleset. SDD.md and UI_RULES.md cost 6,415 tokens in
    every session while eager, including the work that never opens a spec."""
    hits = [f"{f}:{i}" for f in ruleset()
            for i, l in enumerate(lines(f), 1) if re.match(r'^@[A-Za-z~./]', l)]
    return (not hits, f"{len(hits)}: {hits}", "0")

@check
def artifact_rows_agree():
    """CLAUDE.md §19.1 and FLOW.md §8 list the same write-allowed paths, in the same order, with
    the same Who column. The Who column is compared because it is the column that decides who may
    write: while only the paths were compared, either table could hand `specs/` or the ADR folder to
    a different agent and this check stayed green on identical paths. The failure names the column
    that disagrees, so the reader is not left diffing two 24-row tables by eye.

    norm() translates NOTHING — not a placeholder, not a path prefix — because every difference it
    could forgive is a real divergence: FLOW.md §8 spells the adhoc date `{YYYY-MM-DD}` exactly as
    §19.1 does per CLAUDE.md §19.4 § Naming, and both tables carry the design-library row's
    home-config prefix verbatim. Two mappings were removed for that reason. A localized date placeholder ->
    `{YYYY-MM-DD}` mapping reported 22/22 while FLOW.md §8 spelled dates two ways in one block
    (W8H-T1). A home-config prefix strip beside it was dead but not inert (W8K-T2): measured on a copy,
    dropping that prefix from FLOW.md §8 kept this check at 22/22 exit 0 with the strip, and
    failed row 15 without it. Re-adding either re-blinds the check to the divergence it exists
    to catch.

    The Vietnamese phrase for "any agent" -> `any` is the ONE mapping the Who column takes, and it is a word rather than a
    path: FLOW.md is the Vietnamese mirror, so §8 writes that column in Vietnamese by design.
    FLOW.md §8 is a code block with no column rules, so the Who is read left to right — the first
    token whose `·`-separated parts are all known writers — never by column position, which an
    aligned code block does not actually keep."""
    WRITERS = {os.path.basename(f)[:-3] for f in files('agents/*.md')} | {'any', '/codestyle'} | NOT_SHIPPED
    def norm(p):
        p = p.strip().strip('`')
        return p.split(' ')[0].split('·')[0].strip().strip('`')
    def who(cell):
        return frozenset(x for x in (p.strip().strip('`') for p in cell.split('·')) if x)
    def who_in(line):
        # the Vietnamese phrase for "any agent" is two tokens, so the one mapping is applied to the line, before tokenising.
        for tok in line.replace('mọi agent', 'any').split()[1:]:  # scrub-allow: legacy FLOW.md Who-column phrase read when present
            s = who(tok)
            if s and s <= WRITERS:
                return s
        return frozenset()
    a = []
    for l in (section(read('refs/artifact-layout.md'), r'^## 19\.1 ') or '').splitlines():
        l = l.strip()
        if l.startswith('|') and l.count('|') >= 3:
            c = [x.strip() for x in l.strip('|').split('|')]
            if set(''.join(c)) <= set('-: ') or c[0] == 'Path':
                continue
            a.append((norm(c[0]), who(c[1])))
    blk = re.search(r'```\n(.*?)```', section(read('rules/FLOW.md'), r'^## 8\. ') or '', re.S)
    b = [(norm(l.split()[0]), who_in(l))
         for l in (blk.group(1).splitlines() if blk else []) if l.strip()]
    BLANK = ('', frozenset())
    diff = []
    for i, (x, y) in enumerate(zip(a + [BLANK] * len(b), b + [BLANK] * len(a))):
        cols = [n for n, j in (('path', 0), ('Who', 1)) if x[j] != y[j]]
        if cols:
            diff.append(f"row {i} {'+'.join(cols)} differs: "
                        f"19.1=({x[0]!r}, {sorted(x[1])}) flow=({y[0]!r}, {sorted(y[1])})")
    return (a == b and bool(a), f"19.1={len(a)} rows, FLOW8={len(b)} rows, mismatches={diff[:3]}",
            "equal counts, identical order, and the same Who column on every row")

@check
def budgets_and_self_counts_agree():
    """Two hand-written numbers that had no gate, both of one shape: a figure copied or
    counted by hand, living far from the thing it describes.

    CLAUDE.md §6 sets the per-class context budgets and two paragraphs restate them —
    CLAUDE.md §22 and FLOW.md §6. The FLOW copy listed five of the eight classes and said
    nothing about being partial, so an agent reading FLOW had no budget at all for
    problem-solving, infra and docs; it is complete now. A restatement passes one of two
    ways: class for class and number for number against §6, or by calling itself abridged
    and pointing at §6. Silence is the failure this catches.

    A paragraph is a restatement at MIN_CLASSES classes or more, never at one. One is a
    citation inside an argument — agents/orchestrator.md's hotfix row cites the ≤12k figure
    while explaining why that row carries no intake stage — and gating a citation as a
    partial copy would force it to repeat all eight.

    §19.1's opening sentence counts its own exceptions in words, and that count has already
    changed more than once. It is compared against the rows, never against a second written
    number: every path in that table resolves from {workspace_root} except the ones under
    another root, so a row whose path starts with no WORKSPACE prefix is an exception.

    Both halves fail loudly on a rewording rather than passing on an empty parse. The fence
    is required to yield MIN_SOURCE classes first, and falling short of that returns early:
    the §19.1 half is preempted and reported on the run after the source parses again."""
    BUDGET = re.compile(r'`?([a-z][a-z-]{2,})`?\s*≤\s*(\d+)k')
    ABRIDGED = ('abridged', 'rút gọn')  # scrub-allow: legacy abridged marker read when present
    POINTS_AT = '§6'
    MIN_CLASSES = 2
    MIN_SOURCE = 5
    WORKSPACE = ('docs/', '.cm-tmp/', '{plan_dir}/')  # {plan_dir} resolves under docs/ (refs/plan-files.md § Where a plan lives)
    WORDS = {'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
    doc = read('refs/context-policy.md')
    fence = re.search(r'```\n(.*?)\n```', section(doc, r'^# 6\. ') or '', re.S)
    src = dict(BUDGET.findall(fence.group(1))) if fence else {}
    if len(src) < MIN_SOURCE:
        return (False, f"refs/context-policy.md §6 budget fence parsed to {len(src)} classes: {sorted(src)}",
                f"the §6 fence parses to at least {MIN_SOURCE} classes")
    lo = doc[:doc.index(fence.group(1))].count('\n') + 1
    hi = lo + fence.group(1).count('\n')

    def paragraphs(f):
        buf, start = [], 0
        for i, l in enumerate(lines(f) + ['']):
            if l.strip():
                start = start if buf else i + 1
                buf.append(l)
            elif buf:
                yield start, start + len(buf) - 1, '\n'.join(buf)
                buf = []

    bad, seen = [], []
    for f in ruleset():
        for a, b, para in paragraphs(f):
            hits = BUDGET.findall(para)
            if sum(1 for n, _ in hits if n in src) < MIN_CLASSES:
                continue
            if f == 'refs/context-policy.md' and a <= hi and b >= lo:
                continue
            got = dict(hits)
            if got == src:
                verdict = 'complete'
            elif any(w in para for w in ABRIDGED) and POINTS_AT in para:
                verdict = 'abridged'
            else:
                verdict = 'silent'
                bad.append(f"{f}:{a} restates §6 without saying it is abridged: "
                           f"missing={sorted(set(src) - set(got))}, "
                           f"extra={sorted(set(got) - set(src))}, "
                           f"differing={sorted(k for k in set(src) & set(got) if src[k] != got[k])}")
            seen.append(f"{f}:{a}={verdict}")

    sec = section(read('refs/artifact-layout.md'), r'^## 19\.1 ') or ''
    rows = []
    for l in sec.splitlines():
        l = l.strip()
        if l.startswith('|') and l.count('|') >= 3:
            c = [x.strip() for x in l.strip('|').split('|')]
            if set(''.join(c)) <= set('-: ') or c[0] == 'Path':
                continue
            rows.append(c[0].strip('`').split(' ')[0].split('·')[0].strip().strip('`'))
    other = [p for p in rows if not p.startswith(WORKSPACE)]
    said = re.search(r'The ([a-z]+) that do not', sec)
    n = WORDS.get(said.group(1)) if said else None
    if n is None:
        bad.append("§19.1: no readable 'The <number> that do not' opening sentence")
    elif n != len(other):
        bad.append(f"§19.1 opening says {said.group(1)} ({n}) but {len(other)} rows "
                   f"name another root: {other}")
    return (not bad,
            f"source CLAUDE.md §6={len(src)} classes | restatements: "
            f"{', '.join(seen) or 'none'} | §19.1 opening="
            f"{said.group(1) if said else 'unreadable'} vs {len(other)} rows naming "
            f"another root | off={bad}",
            "every restatement of the §6 budgets matches it class for class and number for "
            "number, or declares itself abridged and points at §6; and the §19.1 opening "
            "number equals the rows whose path names a root other than {workspace_root}")

@check
def reviewer_categories_anchored():
    """Every `category` value reviewer can emit resolves to a section or a Raised-from row, and
    every category name cited OUTSIDE agents/reviewer.md still resolves back to that enum. A value
    with no anchor is not a category, and a taxonomy whose three totals only add up to each other
    passes its own arithmetic while every input is wrong.

    The outward half is the one a rename inside agents/reviewer.md cannot survive: enum, sections
    and totals all move together, so the file stays self-consistent while CLAUDE.md §19.5 still
    routes `artifact_litter` and agents/orchestrator.md still routes `spec_drift` — a name that
    now names nothing. Citations are read by the two shapes the ruleset actually writes,
    `` `category: x` `` and ``finding `x` ``; measured 2026-09-20 that is 7 citations across
    CLAUDE.md, SDD.md and agents/orchestrator.md.

    SCAN is the rule-source set rather than ruleset(), which walks every `.md` in the tree: the
    harness-owned `projects/` transcripts are inside that walk and would put this check at the
    mercy of a session log quoting a category name, for no gain — a citation can only route an
    agent from a rule file."""
    CITE = r'`category:\s*([a-z_]+)`|\bfindings?\s+`([a-z_]+)`'
    SCAN = (files('*.md') + files('refs/*.md') + files('agents/*.md')
            + files('skills/*/SKILL.md') + files('commands/*.md') + files('code-style/*.md') + files('rules/code-style/*.md'))
    t = read('agents/reviewer.md')
    enum = re.search(r'"category"\s*:\s*"([^"]+)"', t).group(1).split('|')
    tax = section(read('refs/roles/reviewer/taxonomy.md'), r'^# Findings taxonomy') or ''
    anchors = set(re.findall(r'^## `([a-z_]+)`', tax, re.M))
    raised = {x for l in tax.splitlines() if l.count('|') > 1
              for x in re.findall(r'`([a-z_]+)`', l.split('|')[1])}
    orphan = [e for e in enum if e not in anchors | raised]
    cited = {}
    for f in SCAN:
        if f == 'agents/reviewer.md':
            continue
        for i, l in enumerate(lines(f), 1):
            for m in re.finditer(CITE, l):
                cited.setdefault(m.group(1) or m.group(2), []).append(f"{f}:{i}")
    dangling = [f"{c} cited at {v}, not in the enum" for c, v in sorted(cited.items())
                if c not in set(enum)]
    return (not orphan and not dangling and len(anchors) == 14 and len(enum) == 27,
            f"enum={len(enum)}, sections={len(anchors)}, raised-from={len(enum) - len(anchors)},"
            f" orphans={orphan}, cited elsewhere={sum(len(v) for v in cited.values())} in"
            f" {len(cited)} names, dangling={dangling}",
            "27 values = 14 sections + 13 raised-from, 0 orphans, and every category cited "
            "outside agents/reviewer.md still in the enum")

@check
def status_enum_matches_router():
    """CLAUDE.md §2.1A routes a blocking status per agent; the agent's own § Output enum must
    be able to return it. A status the file cannot emit forces the agent onto `failed`, which
    §2.1A routes somewhere else entirely."""
    router, extra = router_table(), {'completed', 'in_progress'}
    bad = []
    for f in files('agents/*.md'):
        name = os.path.basename(f)[:-3]
        m = re.search(r'"status"\s*:\s*"([^"]+)"', read(f))
        if not m:
            owed = [s for s, who in router.items() if name in who]
            if owed:
                bad.append(f"{f}: no status field, §2.1A owes it {owed}")
            continue
        own = set(m.group(1).split('|'))
        for s, who in router.items():
            if (name in who or who == ['any']) and s not in own:
                bad.append(f"{f}: §2.1A routes {s} from {name}, enum lacks it")
        for s in own - set(router) - extra:
            bad.append(f"{f}: emits {s}, §2.1A does not route it")
    return (not bad, f"{len(bad)} mismatches: {bad}", "every routed status in its agent's enum")

@check
def status_imperative_in_enum():
    """A `status: X` order inside an agent file must be a value that file's § Output can
    carry. Lines attributing the status to a different agent are description, not an order.

    Attribution is read from WHERE the other agent's name sits, not from whether it appears
    at all. Only a mention inside GOVERNS_WITHIN characters before the token attributes it;
    a name anywhere else on the line leaves the order in scope. The whole-line test this
    replaces skipped 11 of 33 tokens — 33% — and SQ7 defeated it by adding one more agent
    name to a line the check had just caught, which hid it again.

    GOVERNS_WITHIN is pinned from the measurement, and is a constraint of the prose rather
    than of the code: over the 11 skipped tokens measured 2026-09-19, every real attribution
    sits at most 11 characters before its token (`Analyst returning `), while the nearest
    mention after a token is 92 characters away, so 24 has margin in both directions."""
    GOVERNS_WITHIN = 24
    others = [os.path.basename(f)[:-3] for f in files('agents/*.md')]
    vocab = set()
    for f in files('agents/*.md'):
        m = re.search(r'"status"\s*:\s*"([^"]+)"', read(f))
        if m:
            vocab |= set(m.group(1).split('|'))
    vocab |= set(router_table())
    bad, skipped, total = [], 0, 0
    for f in files('agents/*.md'):
        me = os.path.basename(f)[:-3]
        m = re.search(r'"status"\s*:\s*"([^"]+)"', read(f))
        own = set(m.group(1).split('|')) if m else set()
        names = [o for o in others if o != me]
        for i, l in enumerate(lines(f), 1):
            for m in re.finditer(r'`?status:\s*([a-z_]+)`?', l):
                total += 1
                near = l[max(0, m.start() - GOVERNS_WITHIN):m.start()]
                if any(re.search(r'\b%s\b' % o, near, re.I) for o in names):
                    skipped += 1
                    continue
                if m.group(1) in vocab and m.group(1) not in own:
                    bad.append(f"{f}:{i} orders status: {m.group(1)}")
    return (not bad,
            f"{len(bad)}: {bad} | skipped {skipped}/{total} "
            f"({100 * skipped // total if total else 0}%) as attributed to another agent",
            "0 orders outside the file's own enum")

@check
def command_modes_exist():
    """A `mode=` a slash command asks for must exist in some agent's mode enum."""
    known = set()
    for f in files('agents/*.md'):
        for e in re.findall(r'"mode"\s*:\s*"([^"]+)"', read(f)):
            known |= {x for x in e.split('|') if x != 'string'}
    bad = [f"{f}: {m}" for f in files('commands/*.md')
           for m in sorted(set(re.findall(r'mode=([a-z-]+)', read(f)))) if m not in known]
    return (not bad, f"{len(bad)} unknown: {bad}", "every command mode= in an agent enum")

@check
def severity_enum_live():
    """`blocking|warning|suggestion` is the LIVE value set of `findings[].severity`, not a
    retired scale: reviewer § Severity maps CLAUDE.md §16's four tags onto exactly these
    three. Absence is the failure — a session that read it as retired nearly deleted it.

    The literal is required IN § Output, which is the block every consumer reads, and the section
    is located first: the fallback this replaces matched the string anywhere in the file, so the
    expected line "present in both § Output blocks" stayed green while the value sat in a Forbidden
    bullet, a docstring, or an HTML comment — anywhere but the enum it claims to measure. A file
    whose § Output cannot be located is a FAIL and says so, never a silent whole-file search."""
    NEED = r'"severity"\s*:\s*"blocking\|warning\|suggestion"'
    SRC = ('agents/reviewer.md', 'agents/implement.md')
    ok, miss = [], []
    for f in SRC:
        out = section(read(f), r'^# Output')
        if out is None:
            miss.append(f"{f}: no § Output section to read")
        elif re.search(NEED, out):
            ok.append(f)
        else:
            miss.append(f"{f}: not in § Output")
    return (not miss, f"present in {ok}, absent from {miss}", "present in both § Output blocks")

@check
def plan_template_keys():
    """Three kinds of key set, one assertion per set: the top level has 26 keys, a task file 25,
    each index entry 4. INDEX is the second copy of `refs/plan-files.md § The index` on purpose, as TOP is.

    The top level is compared against TOP, pinned here: a length test passed any rename, since
    a renamed key is still one key. TOP is the second copy on purpose, and the only way a
    rename shows as one added and one missing rather than as nothing at all.

    The task keys are NOT pinned — they are read from templates/plan/task-template.yaml and compared
    against the set skills/planning-dag/SKILL.md names, so the expectation cannot drift from
    the template. planning_dag_no_invented_keys sees only a key the skill invented, never one
    it left out: `blocker` and `design_brief_ref` were both missing from that list, and
    `design_brief_ref` is the only path by which implement receives DESIGN.md."""
    TOP = {'test_schema', 'lang', 'plan_id', 'objective', 'tldr', 'research_confidence', 'context_budget',
           'non_goals', 'assumptions', 'confirmed_values', 'user_actions', 'target_layout', 'requirements', 'affected_surfaces', 'plan_metrics', 'recommended_approach',
           'approach_variants', 'pre_mortem', 'contracts', 'deviations_from_analysis',
           'waves', 'tasks', 'validation_strategy', 'rollback_strategy',
           'context_budget_breakdown', 'approval'}
    tpl = yaml.safe_load(read('templates/plan/plan-template.yaml'))
    task = yaml.safe_load(read('templates/plan/task-template.yaml'))
    sec = section(read('skills/planning-dag/SKILL.md'), r'^## Task schema') or ''
    named = [set(re.findall(r'`([a-z_]+)`', b))
             for b in sec.split('\n\n') if '`id` · `title`' in b]
    if len(named) != 1:
        return (False, f"{len(named)} key-list paragraphs in § Task schema",
                "exactly one paragraph listing the task keys")
    off = []
    INDEX = {'id', 'wave', 'file', 'depends_on'}   # legacy split-plan index entry
    FULLT = set(task) | {'wave', 'depends_on'}     # a full task entry
    SENT = {'id', 'wave', 'depends_on', 'owner'}   # closeout sentinel: refs/plan-files.md states no shape, so the template's own
    def shapes(e):
        k = set(e)
        return next((w for w in (FULLT, SENT, INDEX) if k == w), FULLT)
    entries = [(f"tasks entry {e.get('id')}", set(e), shapes(e)) for e in tpl['tasks']]
    for label, got, want in (('top-level', set(tpl), TOP),
                             ('planning-dag task', named[0], set(task)), *entries):
        added, missing = sorted(got - want), sorted(want - got)
        if added or missing:
            off.append(f"{label}: added={added}, missing={missing}")
    return (not off,
            f"top-level={len(tpl)}, task={len(task)}, tasks entries={len(entries)}, "
            f"planning-dag names={len(named[0])}, off={off}",
            f"top-level set == the {len(TOP)} names pinned here, "
            "and planning-dag names exactly the task-template set, "
            "and every tasks entry is exactly the task-template keys plus wave and depends_on, or the closeout sentinel id, wave, depends_on, owner (legacy split index id, wave, file, depends_on also accepted)")

@check
def comment_rule_no_quota():
    """rules/code-style/_discipline.md §5 carries no count, ratio or cap — a comment quota produced
    comments written for the linter, not the reader, which is why it was removed. Where the
    five categories are stated is counted by single_statement_invariants, not here.

    All THREE shapes its own sentence names are measured. Only the count shapes were, so the two
    §5 names out loud went through: a ratio ("comments under 10% of the lines") and a cap ("the
    comment budget for a file"), both of which are quotas by any reading of the rule they would
    reinstate."""
    # Shape, not digits: a digit test fails in both directions at once — the word-form
    # quota "Never more than one comment per function." carries no digit and passed, while the
    # `UC-042 / AC-3` a category is required to cite would have failed. §5's `UC-XXX / AC-N`
    # placeholder is the workaround that was already sitting in the text to dodge it.
    NUM = r'(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a single)'
    CAPW = r'(?:cap|caps|capped|capping|budget|budgets|budgeted|quota|quotas|ceiling|allowance)'
    SHAPES = {
        'count': rf'\b{NUM}[\s-]+comments?\b',
        'operator': r'\b(?:at most|no more than|not more than|never more than|up to'
                    r'|maximum(?: of)?)\b[^.\n]{0,30}\bcomments?\b',
        'ratio': r'\bcomments?\b[^.\n]{0,30}(?:\b(?:ratio|density|percent)\b|\d+\s*%)'
                 r'|\b(?:ratio|density)\b[^.\n]{0,30}\bcomments?\b',
        'cap': rf'\bcomments?\b[^.\n]{{0,30}}\b{CAPW}\b'
               rf'|\b{CAPW}\b[^.\n]{{0,30}}\bcomments?\b',
    }
    # §5 states the three shapes in order to forbid them, so an affirmative quota is told from
    # the sentence banning one by the words AROUND the match, never inside it: "no more than one
    # comment" is a quota and stays caught, while "A comment quota was removed" does not. The
    # window is the GOVERNS_WITHIN idea of status_imperative_in_enum, and 24 covers the widest
    # real gap in §5 (`, without ` before `capping`, ` was removed` after `comment quota`).
    NEGATED, NEG_WITHIN = r'\b(?:no|not|never|without|removed|forbidden)\b', 24
    sec = section(read('rules/code-style/_discipline.md'), r'^## 5\. ') or ''
    body = sec.split('\n', 1)[1] if '\n' in sec else ''
    quota = []
    for name, pat in SHAPES.items():
        for m in re.finditer(pat, body, re.I):
            around = (body[max(0, m.start() - NEG_WITHIN):m.start()]
                      + ' | ' + body[m.end():m.end() + NEG_WITHIN])
            if not re.search(NEGATED, around, re.I):
                quota.append(f"{name}: {m.group(0).strip()!r}")
    bullets = len(re.findall(r'^- \*\*', body, re.M))
    return (not quota and bullets == 5, f"bullets={bullets}, quota-shaped phrases={quota}",
            "5 bullets, and no count-, operator-, ratio- or cap-shaped phrase stated "
            "affirmatively")

@check
def single_statement_invariants():
    """Each of these is deliberately written down exactly once; a second copy is what drifts.

    Three assertions, because a heading with pointers is a different shape from a needle.
    ONCE counts a needle across the tree and demands exactly one hit; a pointer is supposed to
    name its home more than once — measured 2026-09-19, three CLAUDE.md lines name § Hard rules
    (§7, §11's foreign-text row, §22) — so a ONCE needle for it would go red against the correct
    state. That section is the only never-compress list, so it is asserted as one
    heading plus one pointer per citing section, reported separately: a rename then reads as a
    heading failure and a dropped pointer as a pointer failure, not as one blurred count.

    The pointer is matched as path-then-section rather than as the sentence around it, so a
    reworded pointer still passes and only a dangling one fails. Bare "Hard rules" is not
    enough — CLAUDE.md §0.5 opens "Hard rules for any code-writing agent".

    The fourth needle guards the diff-line counting rule that lives only in
    agents/planner.md § Workflow step 3. It is drawn from that statement's own enumeration and
    from no pointer's wording: a pointer to step 3 may name the rule without restating it, and
    a needle built from such a pointer would count a legitimate pointer as a second copy. Like
    the other three it catches a verbatim copy and
    not a rephrasing; SQ7 recorded that limitation and it is not fixed here. A needle at 0 and
    a needle at 2 are therefore different events -- a home reworded out from under the needle,
    against a second copy of it -- and each says which, rather than sharing one count-shaped
    message that reads as a duplicate either way.

    The fifth and sixth needles guard the language rule, collapsed into agents/planner.md
    § Language, and the spawn topology, collapsed into agents/orchestrator.md § Worker
    registry. Each is that statement's own opening clause and shares no wording with the
    pointers to it, which read "the only statement of that rule", "the single home of that
    rule" and "states why". The language needle stops at "each" because the rule sentence
    beneath it wraps, and a needle spanning a newline goes red on a reflow that changed
    nothing.

    The third assertion is the heading shape again, for "# Evidence storage" in agents/test.md:
    it owns the evidence tree, the closed viewport enum and the baseline path, and is named
    from five other places, so a rename dangles all of them while every needle above stays
    green — the W6 review demonstrated exactly that on a copy. The citing files are named
    rather than counted: the number of occurrences moves whenever a line is added, the set of
    files that depend on the name does not."""
    ONCE = {'viewport enum': '320 · 768 · 1024 · 1366 · 1440',
            'memory discovery walk': 'Discovery order (HARD) — the only statement of it',
            'comment categories': 'A decision other code depends on',
            'diff-line counting rule': 'three kinds of line fall outside them',
            'language rule': 'Two audiences, one file each',
            'spawn topology': 'a Claude Code platform limit, not a policy choice'}
    HEAD = '## Hard rules (apply to all modes)'
    POINTER = r'context-compression/SKILL\.md[^\n]{0,40}§ Hard rules'
    CITERS = {'§7': ('rules/core.md', r'^# 7\. '),
              '§22': ('refs/context-policy.md', r'^# 22\. ')}
    EV_HEAD = r'^#{1,6} Evidence storage\s*$'
    EV_POINTER = '§ Evidence storage'
    EV_CITERS = ('agents/test.md', 'skills/design-ui/SKILL.md', 'skills/review-checklist/references/design.md',
                 'skills/testing-e2e/SKILL.md')
    counts, bad = {}, []
    for label, needle in ONCE.items():
        hits = {f: read(f).count(needle) for f in ruleset() if needle in read(f)}
        counts[label] = sum(hits.values())
        if counts[label] == 0:
            bad.append(f"{label}: needle not found -- the home may have been reworded: "
                       f"{needle!r}")
        elif counts[label] != 1:
            bad.append(f"{label}: {counts[label]} copies in {hits}")
    heads = read('skills/context-compression/SKILL.md').count(HEAD)
    if heads != 1:
        bad.append(f"never-compress heading: {heads} copies of {HEAD!r}, expected 1")
    dangling = [s for s, (f, head_re) in CITERS.items()
                if not re.search(POINTER, section(read(f), head_re) or '')]
    if dangling:
        bad.append(f"never-compress pointer: missing from {[CITERS[s][0] + ' ' + s for s in dangling]}")
    ev_heads = len(re.findall(EV_HEAD, read('agents/test.md'), re.M))
    if ev_heads != 1:
        bad.append(f"evidence-storage heading: {ev_heads} in agents/test.md, expected 1")
    ev_dangling = [f for f in EV_CITERS if EV_POINTER not in read(f)]
    if ev_dangling:
        bad.append(f"evidence-storage pointer: missing from {ev_dangling}")
    return (not bad,
            f"{counts}, never-compress heading={heads}, "
            f"pointers={len(CITERS) - len(dangling)}/{len(CITERS)}, "
            f"evidence heading={ev_heads}, "
            f"evidence pointers={len(EV_CITERS) - len(ev_dangling)}/{len(EV_CITERS)}, off={bad}",
            "each stated exactly once, the never-compress heading stated once with a pointer "
            "to it in each of CLAUDE.md §7 and refs/context-policy.md §22, and the "
            "evidence-storage heading stated once in agents/test.md with its pointer intact in each of the 4 files citing it")

@check
def test_modes_in_description():
    """agents/test.md `description` is what the router matches on; all three modes belong."""
    d = re.search(r'^description:.*$', read('agents/test.md'), re.M).group(0)
    miss = [m for m in ('browser', 'mobile', 'characterization') if m not in d]
    return (not miss, f"missing={miss}", "browser, mobile, characterization all named")

@check
def planning_dag_no_invented_keys():
    """Six task keys planning-dag invented; a plan built on them fails planner's own
    pre-write validation, then implement rejects it at task intake."""
    INVENTED = ('estimated_files', 'estimated_lines', 'files_hint', 'failure_modes',
                'priority', 'conflicts_with')
    t = read('skills/planning-dag/SKILL.md')
    hits = [k for k in INVENTED if re.search(r'^\s*[-|`]?\s*%s\b' % k, t, re.M)]
    return (not hits, f"{len(hits)}: {hits}", "0 of the 6 invented keys")

@check
def skills_prose_english():
    """Language by file group. A rule, agent, skill or command file is English
    (agents/planner.md § Language, the single home); an artifact a person reads is Vietnamese
    with diacritics (CLAUDE.md §19.4). Both directions are asserted here, group by group,
    against the policy measured in
    the SQ7B prose-gate policy note of the consistency sweep, §2 and §6. Until
    2026-09-20 this looked at `skills/*/SKILL.md` alone -- one of the five English groups the
    rule names, and none of the Vietnamese ones. The tree it was not reading measured
    1,143 Vietnamese lines across 40 files.

    The name still says `skills` although it now covers seven groups. Four verification
    commands in three other plans pipe this run through `grep skills_prose_english` and branch
    on PASS -- docs/plan/claude-designer-codex-routing/plan.yaml:1083 and :1448,
    docs/plan/ruleset-skills-agents-consistency/plan.yaml:17532 and :19266. A rename empties
    that grep, and each of them then takes its failure branch while measuring nothing, which is
    the defect recorded at ruleset-skills-agents-consistency/plan.yaml:17701.

    HELD_OUT is named rather than left unmatched. FLOW.md is deliberately Vietnamese by the
    decision at docs/plan/claude-ruleset-consistency-sweep/plan.yaml:570; no rule file states
    that exemption, and SQ7B-PROSE-GATE-POLICY.md §7 records the gap. The two plan YAML
    templates belong to contract C3, where the assertion follows a `lang` key
    rather than a hard-coded direction -- every glob here ends in `.md`, which is what keeps
    them out of reach, so a glob that does not is reported instead of being allowed to widen
    scope quietly. The last three templates measure zero Vietnamese lines and no evidence
    points either way, so asserting a direction on them would invent work.

    The literal exclusion is span state carried across ONE line wrap, not three regexes.
    Three shapes slipped past the per-line regex -- `**bold**` instead of backticks,
    a double-quoted string broken across a wrap (structurally unmatchable per line), and a
    double backtick wrapping a single one. All three are the same defect, a marked span the
    line boundary cuts in half, so one carry fixes all three and the italic case nobody
    named. The carry is dropped if the closing mark is not on the next line: an unbalanced mark
    then costs one line of blindness instead of swallowing the rest of the file.

    ALLOW pins the phrases no shape can exclude, per file and verbatim, because they are
    unmarked: CLAUDE.md §17's per-option names, which §17 requires agents to print; the
    language name used as a value in agents/planner.md; a proper noun in SDD.md.
    A pin matching nothing is printed as dead so the rotted entry is named. For an ALLOW pin
    that print accompanies a failure rather than replacing one -- the line it stopped covering
    reports in the same run -- and only a dead ENGLISH_MEMORY entry, a file since translated,
    passes on the print alone, as no_bak_suffix_files does in this file.
    Two pins rotted and were deleted rather than retargeted, because the line each covered
    moved under refs/roles/, which no English glob reached until X68 added refs/roles/**:
    agents/reviewer.md's the Vietnamese Given/When/Then labels (which it forbids
    replacing, X60), now a marked span, and agents/orchestrator.md's the Vietnamese word for overview (X66), now
    'overview'. Both are recorded in docs/plan/ruleset-refactor/EXCEPTIONS-vs-v1.1.md.

    ENGLISH_MEMORY is the same debt on the Vietnamese side: four project memory files written
    in English. They are pinned by path, never by a count, so a fifth reads as a failure. The
    measurement found 16 Vietnamese files in that group and never these four, so the reversed
    assertion runs over the group with them named.

    The unaccented detector is a NET, not a gate. Recall re-measured here on 2026-09-20 at
    62.5% -- 815 of 1,305 real Vietnamese lines are still caught after their diacritics are
    stripped -- so it proves a violation is present and never that none is. It reports and does
    not fail, and a green run says nothing about unaccented Vietnamese."""
    VN = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ')  # scrub-allow: legacy Vietnamese character set the gate looks for
    ENGLISH = ('skills/*/SKILL.md', 'code-style/*.md', 'rules/code-style/*.md', 'agents/*.md', 'commands/*.md',
               'refs/*.md', '*.md', 'refs/roles/**/*.md', 'templates/analysis/*.md',
               'templates/spec/spec-delta-template.md', 'templates/plan/plan.lang*-template.md')
    VIETNAMESE = ('templates/plan/plan.vi*-template.md',)   # scrub-allow: legacy glob, read only when present
    HELD_OUT = ('rules/FLOW.md', 'templates/plan/plan-template.yaml',
                'templates/plan/plan-lite-template.yaml', 'templates/SERVER-INFO.md',
                'templates/commit/EXAMPLE-commit.md', 'templates/test/FAILURE-report-template.md')
    ALLOW = {'refs/option-explanation.md': ('Giải pháp', 'Cách làm', 'các bước', 'Tác động',  # scrub-allow: legacy allowed Vietnamese words
                                            'Khi nào chọn', '1-2 câu'),  # scrub-allow: legacy allowed Vietnamese words
             'agents/planner.md': ('tiếng Việt',)}  # scrub-allow: legacy allowed Vietnamese words
    ENGLISH_MEMORY = ()   # the project memory files of the old tree are not part of the package
    MARKS = ('``', '`', '"', '**', '*')
    MARKER = ('khong nguoi duoc nhung cua tieng hoac phai thuc hien viec nhat trong truoc moi '
              'luon chua dang theo giua cung cang tren duoi ngoai ket qua thanh cong loi minh '
              'rieng chinh sai buoc diem nhieu truong luong thuong quyet dinh phuong nghia '
              'khac').split()

    def vn(s):
        return any(c in VN for c in s.lower())

    def outside(l, carry):
        """Prose left after every marked span is dropped, plus the mark still open. A mark
        left open is carried to the next line only -- see the docstring."""
        if carry:
            i = l.find(carry)
            if i < 0:
                return '', ''
            l, carry = l[i + len(carry):], ''
        for d in MARKS:
            while d in l:
                i = l.find(d)
                j = l.find(d, i + len(d))
                if j < 0:
                    return l[:i], d
                l = l[:i] + l[j + len(d):]
        return l, ''

    def unaccented(l):
        """The prose net: link targets, backticked literals and kebab slugs are dropped
        first, because every one of them carries English tokens that are not prose."""
        s = re.sub(r'\]\([^)]*\)', '', l)
        s = re.sub(r'`[^`]*`', '', s)
        s = re.sub(r'[\w./-]*-[\w./-]*', '', s)
        t = re.findall(r'[A-Za-z]+', s.lower())
        return len(t) >= 4 and any(w in MARKER for w in t)

    fenced = literal = pinned = 0
    bad, noprose, net, asserted = [], [], [], set()
    for pat in ENGLISH:
        for f in files(pat):
            if f in HELD_OUT:
                continue
            asserted.add(f)
            infence, carry = False, ''
            for i, l in enumerate(lines(f), 1):
                if l.lstrip().startswith('```'):
                    infence, carry = not infence, ''
                    continue
                rest, carry = outside(l, carry)
                if not vn(l):
                    continue
                if infence:
                    fenced += 1
                elif not vn(rest):
                    literal += 1
                else:
                    for p in ALLOW.get(f, ()):
                        rest = rest.replace(p, '')
                    if vn(rest):
                        bad.append(f'{f}:{i}')
                    else:
                        pinned += 1
    for pat in VIETNAMESE:
        for f in files(pat):
            if f in HELD_OUT or f in asserted:
                continue
            asserted.add(f)
            ls = lines(f)
            if not any(vn(l) for l in ls) and f not in ENGLISH_MEMORY:
                noprose.append(f)
            infence = False
            for i, l in enumerate(ls, 1):
                if l.lstrip().startswith('```'):
                    infence = not infence
                elif not infence and not vn(l) and unaccented(l):
                    net.append(f'{f}:{i}')
    dead = [f'{f} {p!r}' for f, ps in ALLOW.items() for p in ps
            if f not in asserted or p not in read(f)]
    dead += [f for f in ENGLISH_MEMORY if f not in asserted or any(vn(l) for l in lines(f))]
    leak = sorted(set(HELD_OUT) & asserted)
    leak += [p for p in ENGLISH + VIETNAMESE if not p.endswith('.md')]
    return (not (bad or noprose or leak),
            f"{len(asserted)} files in {len(ENGLISH) + len(VIETNAMESE)} groups | "
            f"{len(bad)} prose lines: {bad} | "
            f"{len(noprose)} Vietnamese-group files with none: {noprose} | held out: {leak} | "
            f"excluded {fenced} fenced-block + {literal} marked-span + {pinned} pinned-phrase "
            f"lines, {len(dead)} dead pin: {dead} | unaccented net, reports only, recall "
            f"calibrated 62.5%: {len(net)} {net}",
            f"0 Vietnamese outside a fenced block, a marked span or a pinned phrase in the "
            f"{len(ENGLISH)} English groups; >=1 Vietnamese line in every file of the "
            f"{len(VIETNAMESE)} Vietnamese groups outside the {len(ENGLISH_MEMORY)} pinned "
            f"English ones; and nothing held out for FLOW.md or the plan YAML templates reachable by a glob here")

@check
def bootstrap_floor_current():
    r"""CLAUDE.md §6's bootstrap floors against the live files. A floor is
    `agents/<role>.md` + `CLAUDE.md` + every skill in that role's frontmatter `skills:`
    list, which `skills/agent-bootstrap/SKILL.md` § Order step 1 loads eagerly.
    An agent whose frontmatter sets `omitClaudeMd: true` counts no `CLAUDE.md` bytes.

    The ratio and the tolerance are parsed out of §6 instead of hardcoded here: a second
    copy would keep asserting the old value after someone edits the rule, and this script
    is the thing that runs. Unparseable is a FAIL, never a built-in default.

    Bytes come from os.path.getsize — open().read() counts characters, and §6 carries `§`
    and `—` (RTK.md § Commands that exit 0 with a wrong result). The frontmatter is read
    with yaml, not a regex: `^skills:\s*(.*)$` matches across the newline and swallows the
    first list item, which hid agent-bootstrap's 5,604 B from all nine floors on 2026-09-08.
    """
    try:
        import yaml
    except ImportError:
        return (False, "pyyaml not installed", "pyyaml importable")
    seg = section(read('refs/context-policy.md'), r'^# 6\. Context Policy')
    if seg is None:
        return (False, "refs/context-policy.md §6 not found", "§6 slices")
    ratio = re.findall(r'dividing it by ([\d.]+) B/token', seg)
    tol = re.findall(r'Treat every figure as \*\*±([\d.]+)%\*\*', seg)
    if len(ratio) != 1 or len(tol) != 1:
        return (False, f"ratio={ratio}, tolerance={tol}",
                "exactly one ratio and one tolerance parsed from §6")
    ratio, tol = float(ratio[0]), float(tol[0])

    printed = {}
    for l in (x for x in seg.splitlines() if '≈' in x):
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        for i in range(0, len(c) - 1, 2):
            if c[i] and c[i + 1].startswith('≈'):
                printed[c[i]] = int(c[i + 1].lstrip('≈').replace(',', ''))

    drift, missing = {}, []
    for role, want in printed.items():
        if not os.path.exists(os.path.join(ROOT, f'agents/{role}.md')):
            continue   # a role the package does not ship
        fm = yaml.safe_load(read(f'agents/{role}.md').split('---')[1]) or {}
        paths = [f'agents/{role}.md'] + ([] if fm.get('omitClaudeMd') is True else ['rules/core.md'])
        for s in (fm.get('skills') or []):
            q = f'skills/{s}/SKILL.md'
            if os.path.exists(os.path.join(ROOT, q)):
                paths.append(q)
            else:
                missing.append(f'{role} -> {q}')
        got = round(sum(os.path.getsize(os.path.join(ROOT, q)) for q in paths) / ratio)
        drift[role] = (want, got, 100.0 * (got - want) / want)

    norow = [os.path.basename(f)[:-3] for f in files('agents/*.md')
             if os.path.basename(f)[:-3] not in printed]
    over = [f"{r} printed {w:,} live {g:,} ({d:+.1f}%)"
            for r, (w, g, d) in sorted(drift.items()) if abs(d) > tol]
    worst = max(drift.items(), key=lambda kv: abs(kv[1][2]), default=('-', (0, 0, 0.0)))
    return (not (over or missing or norow),
            f"{len(drift)} floors, ratio={ratio}, tol=+/-{tol}% | worst={worst[0]} "
            f"{worst[1][2]:+.1f}% (printed {worst[1][0]:,}, live {worst[1][1]:,}) | "
            f"over={over} | missing skills={missing} | roles with no row={norow}",
            f"every floor within +/-{tol}% of its live byte count / {ratio}")

@check
def header_format_identical():
    """CLAUDE.md states the extended agent-header format twice — §2.1 Spawn rules and §13
    Model Display — and a handoff flagged the gap this closes: "there is no automatic check
    keeping the two copies identical". Both copies are cut with the SAME expression;
    two expressions would rebuild the drift the check exists to catch.

    Leading whitespace is stripped per line before comparing. The §2.1 copy sits inside a
    bullet list, so two of its continuation lines carry the 2-space indent markdown needs
    to keep them in the bullet, and the top-level §13 copy does not: measured 2026-09-24 at
    316 B against 312 B, identical once that indent is normalised. A raw-byte comparison
    could only be made to pass by breaking the list. Every other difference — a word, a
    backtick, punctuation — still trips this.
    """
    t = read('rules/core.md')
    SENT = r'Every agent opens with.*?byte-for-byte\.'
    got = {}
    for label, head in (('2.1', r'^## 2\.1 Spawn rules'), ('13', r'^# 13\. Model Display')):
        seg = section(t, head)
        m = re.search(SENT, seg, re.S) if seg else None
        got[label] = m.group(0) if m else None
    missing = sorted(k for k, v in got.items() if v is None)
    if missing:
        return (False, f"format sentence not found in section(s) {missing}",
                "the format sentence present in both 2.1 and 13")
    norm = {k: '\n'.join(l.strip() for l in v.splitlines()) for k, v in got.items()}
    same = norm['2.1'] == norm['13']
    return (same,
            f"2.1={len(got['2.1'].encode())} B, 13={len(got['13'].encode())} B, "
            f"identical after normalising indent={same}",
            "both copies identical character for character, leading indent aside")

@check
def agent_enum_matches_registry():
    """The `agent` enum in orchestrator's routing JSON is a second hand-written copy of the
    § Worker registry list in the same file. `analyst-intake` and `reviewer-codex` were added
    to both by hand, and nothing caught the two disagreeing.

    `auditor` is the ONLY legitimate gap, and the registry row states the reason: "Daily fleet
    effectiveness audit (read-only). Scheduled, not spawned mid-task." — it never appears as a
    `next_spawns[].agent` value, so the enum must not carry it. Any other difference is a FAIL,
    in either direction; the exception is one named row with a reason, not a skip-list.

    Rows are read from the `| Agent | Model |` header down, not from the whole section:
    § Worker registry also holds the permission-mode table, whose first column added `auto`
    and `accept-and-edit` to a section-wide slice measured 2026-09-10.
    """
    t = read('agents/orchestrator.md')
    ls = t.splitlines()
    hdr = [i for i, l in enumerate(ls) if re.match(r'^\|\s*Agent\s*\|\s*Model\s*\|', l)]
    enum = [set(v.split('|')) for v in re.findall(r'"agent"\s*:\s*"([^"]+)"', t) if '|' in v]
    if len(hdr) != 1 or len(enum) != 1:
        return (False, f"registry tables={len(hdr)}, agent enum literals={len(enum)}",
                "exactly one registry table and one agent enum")
    rows = set()
    for l in ls[hdr[0] + 2:]:
        if not l.startswith('|'):
            break
        hit = re.findall(r'`([a-z-]+)`', l.strip().strip('|').split('|')[0])
        if hit:
            rows.add(hit[0])
    diff = rows ^ enum[0]
    return (diff == {'auditor'} and 'auditor' in rows,
            f"registry={len(rows)}, enum={len(enum[0])}, symmetric difference={sorted(diff)}",
            "difference is exactly auditor, present in the registry and absent from the enum")

@check
def routing_rows_are_legal_workflows():
    """CLAUDE.md §3 claims the class list, the routing rows and the `workflow` enum are checked
    against each other. Two of those directions were a claim and not a check: measured
    2026-09-20, `plan-only` was a routing row in § Workflows and not a legal value of the enum,
    and 22 passing checks said nothing about it; nothing read the §3 class list at all.

    Rows come from the `| Class | Pipeline |` table, which § Workflows itself calls the routing
    source of truth, never from a hand-written list here. The backticked tokens in a Class cell
    are the values: `complex` / `refactor` is two of them in one cell, and a parenthesised
    qualifier -- `bug` (small), `docs` (a documentation diff) -- names a variant of the token
    beside it rather than a class of its own. Enum values are reduced the same way, so
    `bug (small)` and `bug` are one token on both sides and the two compare like to like.

    Rows and enum are asserted EQUAL, both directions. A floor stood here until 2026-09-20 --
    `MIN_ROWS = 10` against 12 real rows -- and the W10 reviewer deleted the `plan-only` row,
    the row this check was written for, with the gate still reading 23/23 and exit 0. A floor
    cannot catch a deletion; an equality against a second hand-written source can, and carries
    no number of its own to go stale. The row count is printed, never asserted.

    The §3 class list is that second source for its own half of the sentence: every class named
    there must have a routing row. Its extras are printed and not asserted -- §3 claims every
    class has a row, never that every row is a class, and `plan-only` is a routing row for a run
    that produces no diff rather than a class anything classifies to.

    Every parse fails loudly rather than passing on nothing: a renamed table header, a missing
    enum literal, a row with no backticked token and a §3 opening that no longer lists classes
    each report their own empty parse by name.

    Shape B is asserted as a subset of Shape A rather than re-listed, which is exactly what its
    own inline note claims of it."""
    def unqualified(v):
        return re.sub(r'\s*\(.*$', '', v).strip()

    t = read('agents/orchestrator.md')
    ls = (section(read('refs/roles/orchestrator/workflows.md'), r'^# Workflows') or '').splitlines()
    enums = [v for v in re.findall(r'"workflow"\s*:\s*"([^"]+)"', t) if '|' in v]
    hdr = [i for i, l in enumerate(ls) if re.match(r'^\|\s*Class\s*\|\s*Pipeline\s*\|', l)]
    if len(hdr) != 1 or len(enums) != 2:
        return (False, f"routing tables={len(hdr)}, workflow enum literals={len(enums)}",
                "exactly one `| Class | Pipeline |` table and two workflow enum literals")
    legal, subset = {unqualified(v) for v in enums[0].split('|')}, set(enums[1].split('|'))
    para = re.split(r'\n\s*\n', section(read('refs/workflow-routing.md'), r'^# 3\. ') or '\n\n')
    classes = set(re.findall(r'`([a-z][a-z-]*)`', para[1] if len(para) > 1 else ''))
    rows, bad = [], []
    for l in ls[hdr[0] + 2:]:
        if not l.startswith('|'):
            break
        cell = l.strip().strip('|').split('|')[0].strip()
        tok = re.findall(r'`([a-z][a-z -]*)`', cell)
        rows.append(tok)
        bad += [f"{cell}: {v!r} not a legal `workflow` value" for v in tok if v not in legal]
        if not tok:
            bad.append(f"{cell}: no backticked class")
    named = {v for tok in rows for v in tok}
    bad += [f"`{v}`: a legal `workflow` value with no routing row" for v in sorted(legal - named)]
    if not classes:
        bad.append("CLAUDE.md §3 opening paragraph lists no backticked class")
    bad += [f"`{v}`: a CLAUDE.md §3 class with no routing row" for v in sorted(classes - named)]
    if not subset <= legal:
        bad.append(f"Shape B outside Shape A: {sorted(subset - legal)}")
    return (not bad,
            f"{len(rows)} routing rows naming {len(named)} classes, Shape A enum={len(legal)} "
            f"unqualified, Shape B={len(subset)}, CLAUDE.md §3={len(classes)} classes, "
            f"rows outside §3={sorted(named - classes)}, off={bad}",
            "the routing rows and the `workflow` enum name the same classes, every CLAUDE.md "
            "§3 class has a routing row, and Shape B a subset of Shape A")


@check
def pin_resolves():
    """Every `file:line` pin opens and lands where it claims -- in a rule file and in a record.

    This does TWO jobs, and only one of them belongs on a record.

    JOB 1, DOES THE PIN RESOLVE: the target exists, the line is in range, the range holds a
    non-blank line, and where the citation quotes the pinned line, the quotation still
    matches. A pin that drifted is wrong wherever it is written, so this runs over
    `scanned()`. A record is where it drifts unseen: measured 2026-09-22 the check reported
    `38 pins checked, 0 off` while `SPEC-DEVIATIONS.md` held pins that had drifted twice,
    by +9 and again by +10, onto the wrong row and onto a blank line.

    A target resolves against ROOT and THEN against the citing file's own directory, because
    a record pins its sibling by bare name -- `SPEC-DEVIATIONS.md` pins `SPEC.md:375`, which
    is not `{ROOT}/SPEC.md`. Against ROOT alone all 42 such pins fell into the "not
    resolvable from here" bucket and were never checked, which is why that file could say
    "the check does not see it, and not because it is valid" and be right. No rule-file pin resolves
    that way -- 0 of 38 on 2026-09-23 -- so the second candidate cannot weaken this side.

    The quotation clause fires on ONE shape: the pin, a colon, then a quotation running to
    the end of the line because it wraps. That is narrow on purpose. Any `"..."` after a pin
    is usually a quoted TERM and not a quotation of the target -- measured 2026-09-23, the
    loose marker fired 97 times for 6 matches, so it would report 91 non-defects and bury the
    real ones underneath. The shapes it does not reach are declared, not closed; the count it
    fired is printed so its reach is readable rather than assumed.

    JOB 2, IS THE PIN THE RIGHT FORM: QT-3 bans a line pin into a `.md` rule file outright,
    because a rule file moves under its own pins while code files do not. That is a rule
    about how the RULESET cites itself, so it runs over `ruleset()` alone. Over records it
    reports 677 form breaches in closed plans -- the user chose on 2026-09-23 to scope the
    ban rather than convert 677 pins by hand, so a record is held to job 1 and not to job 2.

    SCOPE: `pointer_lines` -- in a record, fenced blocks, quoted spans and the v1.1 copy
    `SPEC.md` are quoted text, not pins, and are skipped (user decision 2026-09-24, X67).
    Rule files are read in full.
    """
    PIN = re.compile(r'`([A-Za-z0-9_./-]+\.(?:md|sh|mjs|cjs|js|ts|py|yaml|json)):(\d+)(?:-(\d+))?`')
    QUOTED = re.compile(r'^[`*)\]]*\s*:\s+[*_]*"([^"\n]{12,})$')

    def resolved(target, citing):
        near = os.path.normpath(os.path.join(os.path.dirname(citing), target)).replace(os.sep, '/')
        for c in (target, near):
            if os.path.exists(os.path.join(ROOT, c)):
                return c
        return None

    rules = set(ruleset())
    bad, checked, quoted = [], 0, 0
    for f in scanned():
        for i, l, in_quote in pointer_lines(f):
            for m in PIN.finditer(l):
                if in_quote(m.start()):
                    continue          # quoted text in a record, not a pin (pointer_lines)
                target, a, b = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
                checked += 1
                if target.endswith('.md') and f in rules:
                    bad.append(f"{f}:{i} pins a rule file by line ({target}:{a}) "
                               f"-- use `{target} § Section`")
                    continue
                p = resolved(target, f)
                if p is None:
                    continue          # product-repo path, not resolvable from here
                body = lines(p)
                if a < 1 or b > len(body):
                    bad.append(f"{f}:{i} -> {target}:{a}-{b} out of range "
                               f"(file has {len(body)} lines)")
                    continue
                if not any(body[n - 1].strip() for n in range(a, b + 1)):
                    bad.append(f"{f}:{i} -> {target}:{a}-{b} is blank")
                    continue
                q = QUOTED.match(l[m.end():])
                if q:
                    quoted += 1
                    if q.group(1).strip() not in '\n'.join(body[a - 1:b]):
                        bad.append(f"{f}:{i} -> {target}:{a}-{b} no longer holds the "
                                   f"quotation beside it: {q.group(1).strip()[:60]!r}")
    return (not bad,
            f"{checked} pins checked over {len(rules)} rule files + {len(records())} records, "
            f"{quoted} carrying a quotation, {len(bad)} off: {bad}",
            "no line pin into a .md rule file FROM a rule file (QT-3, rule files only); and "
            "every pin that resolves, in a rule file or a record, in range, non-blank, and "
            "still holding the quotation written beside it")


@check
def section_ref_exists():
    """Every `CLAUDE.md §N` reference names a section CLAUDE.md actually has.

    Measured 2026-09-22: agents/reviewer.md cited `CLAUDE.md §16.1` twice; CLAUDE.md has §16
    and no §16.1, and CLAUDE.md §16 in turn pointed back at agents/reviewer.md for the same
    structure -- a cycle with no owner. All 23 checks passed against that state.

    When §6 moves to refs/context-policy.md in W3 this check keeps reading CLAUDE.md, so a
    reference left behind pointing at a moved section fails here rather than silently
    resolving to nothing.

    Citing side is `scanned()`, not `ruleset()`. A record citing a section CLAUDE.md no
    longer has misroutes its reader exactly as a rule file does, and the refactor that
    dissolved §16.1 and §20.2 into `refs/` left those citations behind in plans nobody
    re-reads. The section list still comes from CLAUDE.md alone: records do not define
    sections, they cite them.

    SCOPE: `pointer_lines` -- in a record, fenced blocks, quoted spans and the v1.1 copy
    `SPEC.md` are skipped (user decision 2026-09-24, X67). Rule files are read in full.
    """
    txt = read('rules/core.md')
    have = {m.group(1) for m in re.finditer(r'^#{1,3} (\d+(?:\.\d+)?)\.?\s', txt, re.M)}
    REF = re.compile(r'CLAUDE\.md[^\n]{0,12}?§\s?(\d+(?:\.\d+)?)')
    bad = []
    for f in scanned():
        for i, l, in_quote in pointer_lines(f):
            for m in REF.finditer(l):
                if in_quote(m.start()):
                    continue          # quoted text in a record (pointer_lines)
                if m.group(1) not in have:
                    bad.append(f"{f}:{i} -> CLAUDE.md §{m.group(1)}")
    return (not bad,
            f"CLAUDE.md has {len(have)} sections, cited from {len(ruleset())} rule files + "
            f"{len(records())} records, {len(bad)} dangling: {bad}",
            "every CLAUDE.md §N reference resolves, from a rule file or a record")

@check
def named_section_ref_exists():
    """Every `file.md § Section name` pointer names a heading that file actually has.

    W1 converted 31 `.md` line pins into section-name pointers, because a pin drifts when
    anything above it is edited and a name does not. That traded one silent break for
    another: `pin_resolves` bans the line pin and `section_ref_exists` resolves only
    `CLAUDE.md §N`, so on 2026-09-22 the tree carried 100+ named pointers with nothing
    reading them. W2-W5 rewrite the very files holding those headings, and a rename would
    break every pointer into it without a single check going red -- which is E1 again.

    Matching is longest-first, because a heading routinely carries a suffix the citation
    drops: `§ Scope` names `## Scope (HARD)` in agents/implement.md, `§ Test cases`
    names `# Test cases (HARD)`. So the cited name must PREFIX a heading at a word boundary,
    never equal it. Longest-first plus exact-before-prefix is what keeps that from being
    sloppy: where agents/test.md has both `# Output` and `# Output discipline -- failures
    only (HARD)`, `§ Output` takes the exact heading and `§ Output discipline -- failures
    only` takes the longer one. A heading's leading number is stripped before matching, so
    `CLAUDE.md § Language` resolves against `# 1. Language + Final Output` and
    `CLAUDE.md § Global Agent Rules` against the H1.

    Scope is named pointers only. A numeric `§N` into any file other than CLAUDE.md --
    `FLOW.md §4`, `SDD.md §11.1`, `rules/code-style/_discipline.md §5` -- is checked by nothing
    here and by nothing in `section_ref_exists`, which reads CLAUDE.md alone.

    Citing side AND target side are `scanned()`. A record's pointer dangles the same way a
    rule file's does, and a record is also a legitimate TARGET -- `SPEC-DEVIATIONS.md` is
    where `SPEC.md § …` and its own `§ 16.9` are cited from. Adding records to the target
    set cannot weaken the rule-file side: `target_of` returns a basename match only when it
    is unique, so a name that records make ambiguous falls to off-scope rather than to a
    wrong file, and 0 of the rule-file pointers moved when they were added (2026-09-23).

    SCOPE (user decision 2026-09-24, X67): in a RECORD only, `pointer_lines` skips fenced
    blocks, quoted spans and the v1.1 copy `SPEC.md`, and a PLACEHOLDER section name (`§N`,
    `§N.N`, `§ <name>`) is a pattern and is skipped. Rule files are read in full: a placeholder
    in a rule file still fails.
    """
    REF  = re.compile(r'([~A-Za-z0-9_./-]+\.md)`?[ \t]*§[ \t]*(?=\S)')
    HEAD = re.compile(r'^#{1,6}[ \t]+(.+?)[ \t]*$', re.M)
    NUM  = re.compile(r'^\d+(?:\.\d+)*\.?[ \t]+')
    # A placeholder in the section slot: a literal `N` / `N.N` or an `<angle-bracketed>` name,
    # followed by no letter or digit. `§ Naming` and `§ Notation` are not placeholders.
    PLACEHOLDER = re.compile(r'(?:N(?:\.N)*|<[^<>\n]+>)(?![A-Za-z0-9])')

    def clean(s):
        return s.replace('**', '').strip()

    scope = set(scanned())
    base  = {}
    for r in scope:
        base.setdefault(r.rsplit('/', 1)[-1], []).append(r)

    heads = {}
    def headings(p):
        if p not in heads:
            out = set()
            for m in HEAD.finditer(read(p)):
                h = clean(m.group(1))
                out.add(h)
                out.add(NUM.sub('', h))
            heads[p] = out
        return heads[p]

    def target_of(ref, citing):
        t = ref.lstrip('~').lstrip('/')
        t = t[len('.claude/'):] if t.startswith('.claude/') else t
        near = os.path.normpath(os.path.join(os.path.dirname(citing), ref)).replace(os.sep, '/')
        for c in (t, near):
            if c in scope:
                return c
        hit = base.get(ref.rsplit('/', 1)[-1], [])
        return hit[0] if len(hit) == 1 else None

    bad, checked, offscope = [], 0, 0
    recs = set(records())
    for f in scanned():
        for i, l, in_quote in pointer_lines(f):
            for m in REF.finditer(l):
                if in_quote(m.start()):
                    continue          # quoted text in a record (pointer_lines)
                tail = clean(l[m.end():].split('§')[0])
                if not tail or tail[0].isdigit():
                    continue          # `§N` -- section_ref_exists owns CLAUDE.md's
                if f in recs and PLACEHOLDER.match(tail):
                    continue          # `§N`, `§N.N`, `§ <name>` in a record -- a pattern
                p = target_of(m.group(1), f)
                if p is None:
                    offscope += 1     # product-repo or record path, not a rule file here
                    continue
                hs, hit = headings(p), None
                for end in range(len(tail), 0, -1):
                    if end < len(tail) and tail[end].isalnum() and tail[end - 1].isalnum():
                        continue      # mid-word, not a boundary
                    cand = tail[:end].strip().rstrip('.,;:*—-').strip()
                    if not cand:
                        continue
                    if cand in hs:
                        hit = cand; break
                    if any(h.startswith(cand) and not h[len(cand):len(cand) + 1].isalnum()
                           for h in hs):
                        hit = cand; break
                checked += 1
                if hit is None:
                    bad.append(f"{f}:{i} -> {p} § {tail[:48]}")
    return (not bad,
            f"{checked} named pointers checked from {len(ruleset())} rule files + "
            f"{len(records())} records, across {len(heads)} target files, "
            f"{offscope} off-scope, {len(bad)} dangling: {bad}",
            "every `file.md § Section` pointer names a heading that file has, cited from a "
            "rule file or a record")

@check
def test_case_template_shape():
    """The test-case vocabulary the four plan templates show agrees with test-cases.md.

    The layer enum E is read from its one line in § Layers, never pinned here: `type: browser`
    and a lite enum missing `api` and `a11y` both drifted while nothing checked test_cases.
    The kinds are pinned, as § Kinds states them in prose. The driver catches nothing, so
    every read, parse and key below lands in off[] instead of raising."""
    K, off, E = {'happy', 'edge', 'error', 'fallback', 'timeout', 'retry', 'security', 'partial_failure', 'concurrency'}, [], None
    FULL, LITE = 'templates/plan/task-template.yaml', 'templates/plan/plan-lite-template.yaml'
    AT = {FULL: 'the task', LITE: 'tasks[0]'}   # the full template is one task; lite keeps a tasks list
    sec = ''
    try:
        sec = section(read('refs/roles/planner/test-cases.md'), r'^## Layers$') or ''
    except OSError as e:
        off.append(f"test-cases.md: {type(e).__name__}")
    enum = [l for l in sec.splitlines() if re.fullmatch(r'`[a-z0-9_]+`( · `[a-z0-9_]+`)+', l)]
    if len(enum) == 1:
        E = set(re.findall(r'`([a-z0-9_]+)`', enum[0]))
    else:
        off.append(f"{len(enum)} enum paragraphs in test-cases.md § Layers, expected 1")
    t0 = {}
    for p in (FULL, LITE):
        try:
            doc = yaml.safe_load(read(p))
            t0[p] = doc if p == FULL else doc['tasks'][0]
        except (OSError, yaml.YAMLError, TypeError, KeyError, IndexError) as e:
            off.append(f"{p}: {AT[p]} unreadable ({type(e).__name__})")
            continue
        if not isinstance(t0[p], dict):
            off.append(f"{p}: {AT[p]} is not a mapping")
            del t0[p]
            continue
        w = t0[p].get('case_kind_waivers')
        if not isinstance(w, list):
            off.append(f"{p}: case_kind_waivers of {AT[p]} is not a list ({type(w).__name__})")
    cases = {}
    for p, t in t0.items():
        tc = t.get('test_cases')
        if isinstance(tc, list):
            off += [f"{p}: test_cases[{i}] is not a mapping" for i, c in enumerate(tc) if not isinstance(c, dict)]
        cases[p] = [c for c in tc if isinstance(c, dict)] if isinstance(tc, list) else []
        if not cases[p]:
            off.append(f"{p}: test_cases of {AT[p]} has no case mapping")
    for c in cases.get(LITE, []):
        for key, want in (('layer', E), ('kind', K)):
            v = c.get(key)
            got = set(v.split('|')) if isinstance(v, str) else None
            if want is not None and got != want:
                off.append(f"lite {key} enum {sorted(got or [])} != {sorted(want)}")
    full_kinds = set()
    for c in cases.get(FULL, []):
        cid, t, k = c.get('id'), c.get('layer'), c.get('kind')
        if E is not None and not (isinstance(t, str) and t in E):
            off.append(f"full {cid}: layer {t!r} not in E")
        if not (isinstance(k, str) and k in K):
            off.append(f"full {cid}: kind {k!r} not in {sorted(K)}")
        full_kinds.add(str(k))
    if FULL in cases:
        w = t0[FULL].get('case_kind_waivers')
        w = w if isinstance(w, list) else []
        waived = {str(x.get('kind')) for x in w if isinstance(x, dict)}
        if K - full_kinds - waived:
            off.append(f"{FULL}: the task is missing kind {sorted(K - full_kinds - waived)}, no waiver")
    for p in ('templates/plan/plan.lang-template.md', 'templates/plan/plan.lang-lite-template.md'):
        rows = []
        try:
            rows = [l for l in lines(p) if l.startswith('| Id |')]  # scrub-allow: legacy plan.vi table header read when present
        except OSError as e:
            off.append(f"{p}: {type(e).__name__}")
        if not any({'Layer', 'Kind'} <= {x.strip() for x in r.split('|')} for r in rows):
            off.append(f"{p}: no `| Id |` row with Layer and Kind")
    return (not off,
            f"E={sorted(E or [])}, cases full={len(cases.get(FULL, []))} "
            f"lite={len(cases.get(LITE, []))}, off={off}",
            "one enum line in § Layers; lite layer enum == E and kind enum == the nine of K; "
            "every full case layer in E and kind in K, all nine covered or waived; "
            "case_kind_waivers a list on the task template and on lite tasks[0]; a plan.lang `| Id |` row with Layer and Kind")

def tier3_refs():      return files('refs/*.md') + files('refs/roles/**/*.md')

@check
def rule_file_headings():
    """Every agents/*.md has the seven '# ' headings below, in order ('Output' may carry a
    suffix); every tier-3 ref has an owner line and a 'Read when:' line in its first 8 lines.

    A recorded decision made the shape in use a rule. Measured 2026-09-27 (plan
    claude-test-kinds-and-done-checks A3): 13/13 agents in shape, six with 'Output (...)'; of
    51 refs, 34 carry '<Owner:' + '<Read when:', 9 plain 'Owner:' + 'Read when:', 7 'Tier 3
    of' + plain 'Read when:', and refs/review-trail.md neither. All three forms pass. Only the
    first 8 lines count, so a body line cannot stand in for the header; a '# ' line inside a
    ``` fence is a shell comment, not a heading."""
    SHAPE = ['Role', 'Inputs', 'Workflow', 'Gates', 'Output', 'Forbidden', 'References']
    OWNER, READ = re.compile(r'<Owner:|Owner:|Tier 3 of '), re.compile(r'<?Read when:')
    off = []
    agents = files('agents/*.md')
    for f in agents:
        heads, fence = [], False
        for l in lines(f):
            if l.startswith('```'):
                fence = not fence
            elif not fence and l.startswith('# '):
                heads.append(re.sub(r'^Output .*', 'Output', l[2:]))
        if heads != SHAPE:
            off.append(f"{f}: {heads}")
    refs = tier3_refs()
    for f in refs:
        head = lines(f)[:8]
        miss = [n for n, rx in (('owner', OWNER), ('Read when', READ)) if not any(rx.match(l) for l in head)]
        if miss:
            off.append(f"{f}: no {' or '.join(miss)} line in lines 1-8")
    return (not off, f"agents={len(agents)}, refs={len(refs)}, off={len(off)} {off}",
            f"agents in '# ' order {SHAPE}; each ref: '<Owner:'|'Owner:'|'Tier 3 of' and "
            "'<Read when:'|'Read when:' in lines 1-8")

EFFORT_VARIANT = re.compile(r'^agents/([a-z-]+)-(?:low|medium|high|xhigh|max)\.md$')

def is_variant(f):
    """agents/<role>-<effort>.md beside an agents/<role>.md: an effort variant, refs/effort-routing.md
    § Variants. files() skips it, so only effort_variants_match_base reads one. A hyphenated role
    name that ends in no effort word is not a variant."""
    m = EFFORT_VARIANT.match(f)
    return bool(m) and os.path.exists(os.path.join(ROOT, f'agents/{m.group(1)}.md'))

@check
def plan_steps_shape():
    """A plan written after steps[] existed carries them, and its plan.vi.md renders them
    (the pilot plan claude-openspec-pilot).

    One validator runs over the two template pairs first, as the positive control, then over
    every plan folder under docs/plan/, docs/specs/changes/ and docs/changes/ (archive included) that holds a
    plan.yaml and is not in OLD. OLD names the 25 folders under docs/plan/ when
    claude-plan-format-b3 closed; none carries steps[] (0 of 95 task files, 2026-10-07). A name
    is the selector, not a date or a key, so a new plan cannot leave the check by omitting
    something. CHECK_PLAN_DIRS, colon-separated folders, adds plans to validate, which is how a
    malformed fixture under .cm-tmp/ proves the check fails. The driver catches nothing, so
    every read and parse below lands in off[] instead of raising. A run step also carries an
    expect opening exit N or rc=N, the output that proves it (review F1, folded into this pilot by the
    the user, to fold the seven mandatory points into the pilot plan)."""
    OLD = {'agent-workflow-fix-20260605', 'claude-adaptive-effort-routing', 'claude-cmtmp-autoclean',
           'claude-designer-codex-routing', 'claude-final-audit-fixes', 'claude-final-pass',
           'claude-fleet-codex-multi-engine', 'claude-open-items-sweep', 'claude-plan-format-b3',
           'claude-plan-task-folders', 'claude-planner-test-case-coverage', 'claude-process-speedup',
           'claude-review-system-full-adoption', 'claude-ruleset-consistency-sweep',
           'claude-test-case-followups', 'claude-test-kinds-and-done-checks',
           'claude-test-resume-analyst-design', 'claude-test-two-pass', 'claude-workflow-cuts',
           'config-bundle-v2', 'ruleset-open-findings-r2-r5-r6-r7', 'ruleset-refactor',
           'ruleset-scout-agent', 'ruleset-scout-hybrid', 'ruleset-skills-agents-consistency'}
    HEAD = re.compile(r'^### (\d+)\. (\S+) · ', re.M)
    TICK = re.compile(r'^- \[([ x])\] (\d+)\.(\d+) ', re.M)
    off, keys = [], set()
    try:
        keys = set(yaml.safe_load(read('templates/plan/task-template.yaml'))['steps'][0])
    except (OSError, yaml.YAMLError, TypeError, KeyError, IndexError) as e:
        off.append(f"task-template.yaml: steps[0] unreadable ({type(e).__name__})")

    def shape(label, tasks, vi, split):
        bad, num, ticks = [], {}, {}
        for n, tid in HEAD.findall(vi):
            if tid in num or n in num.values():
                bad.append(f"{label}: heading {n}. {tid} repeats a task id or a number")
            num[tid] = n
        for x, n, m in TICK.findall(vi):
            ticks.setdefault(n, []).append((m, x))
        if split:
            bad += [f"{label}: the mirror has no '## {h[0]}'" for h in (('Proposal', 'Đề xuất'), ('Design', 'Thiết kế'))  # scrub-allow: legacy mirror headings accepted
                    if not re.search(rf'^## ({h[0]}|{h[1]})$', vi, re.M)]
        ids = set()
        for t in tasks:
            tid = t.get('id') if isinstance(t, dict) else None
            ids.add(tid)
            st = t.get('steps') if isinstance(t, dict) else None
            if not isinstance(st, list) or not st:
                bad.append(f"{label}: {tid} has no steps[]")
                continue
            wrong = [i for i, s in enumerate(st) if not isinstance(s, dict) or set(s) != keys
                     or s.get('action') not in ('edit', 'create', 'delete', 'run')]
            if wrong:
                bad.append(f"{label}: {tid} steps{wrong} differ from the template keys or action")
            noexp = [s.get('n') for s in st if isinstance(s, dict) and s.get('action') == 'run'
                     and not (isinstance(s.get('expect'), str) and re.match(r'(exit |rc=)\d+', s['expect'].strip()))]
            if noexp:
                bad.append(f"{label}: {tid} run steps n={noexp}: expect names no exit code")
            if tid not in num:
                bad.append(f"{label}: the mirror has no '### n. {tid} · ' heading")
                continue
            done = {str(s.get('n')): s.get('done') for s in st if isinstance(s, dict)}
            got = ticks.get(num[tid], [])
            if sorted(m for m, _ in got) != sorted(done):
                bad.append(f"{label}: {tid} steps n={sorted(done)} but plan.vi.md lines "
                           f"{num[tid]}.m m={sorted(m for m, _ in got)}")
            bad += [f"{label}: {num[tid]}.{m} is ticked but step {m} of {tid} is not done"
                    for m, x in got if x == 'x' and done.get(m) is not True]
        bad += [f"{label}: heading {tid} names no task" for tid in sorted(set(num) - ids)]
        return bad

    pairs = (('full template', 'templates/plan/task-template.yaml', None,
              'templates/plan/plan.lang-template.md', True),
             ('lite template', 'templates/plan/plan-lite-template.yaml', 0,
              'templates/plan/plan.lang-lite-template.md', False))
    for label, y, i, vi, split in pairs:
        try:
            doc = yaml.safe_load(read(y))
            off += shape(label, [doc if i is None else doc['tasks'][i]], read(vi), split)
        except (OSError, yaml.YAMLError, TypeError, KeyError, IndexError) as e:
            off.append(f"{label}: unreadable ({type(e).__name__})")
    found = [os.path.dirname(p) for r in ('docs/plan', 'docs/specs/changes', 'docs/specs/changes/archive', 'docs/changes', 'docs/changes/archive')
             for p in glob.glob(os.path.join(ROOT, r, '*', 'plan.yaml'))]
    plans = sorted(d for d in found if os.path.basename(d) not in OLD)
    exempt = len(found) - len(plans)
    plans += [d for d in os.environ.get('CHECK_PLAN_DIRS', '').split(':') if d]
    for d in plans:
        label = os.path.basename(d.rstrip('/'))
        try:
            idx = yaml.safe_load(open(os.path.join(d, 'plan.yaml'), encoding='utf-8'))['tasks']
            split = os.path.isdir(os.path.join(d, 'tasks'))
            tasks = ([yaml.safe_load(open(os.path.join(d, e['file']), encoding='utf-8')) for e in idx]
                     if split else idx)
            mirror = next((m for m in sorted(glob.glob(os.path.join(d, 'plan.*.md'))) if not m.endswith('.vi.md')),
                          os.path.join(d, 'plan.vi.md'))   # plan.<lang>.md; plan.vi.md only as the legacy fallback
            off += shape(label, tasks, open(mirror, encoding='utf-8').read(), split)
        except (OSError, UnicodeDecodeError, yaml.YAMLError, TypeError, KeyError) as e:
            off.append(f"{label}: unreadable ({type(e).__name__})")
    return (not off,
            f"2 template pairs, {len(plans)} plans checked {[os.path.basename(d.rstrip('/')) for d in plans]}, "
            f"{exempt} exempt by name, off={off}",
            "both template pairs and every plan outside OLD: non-empty steps[] with the template's step "
            "keys and an expect opening exit N or rc=N on every run step; one '### n. <id> · ' heading per task and one '- [ ] n.m' line per step, '[x]' only "
            "on a done step; '## Đề xuất' and '## Thiết kế' in a split plan's mirror (or '## Proposal' and '## Design')")  # scrub-allow: legacy mirror headings named in the message

@check
def touch_layer_agrees():
    """scripts/plan-verify.py LAYERS and TOUCH_LAYER equal the layer list and the touch rows of refs/roles/planner/test-cases.md."""
    got = {}
    for n in ast.parse(read('scripts/plan-verify.py')).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and getattr(n.targets[0], 'id', '') in ('LAYERS', 'TOUCH_LAYER'):
            got[n.targets[0].id] = ast.literal_eval(n.value)
    doc = lines('refs/roles/planner/test-cases.md')
    top = next((i for i, l in enumerate(doc) if l == '## Layers'), len(doc))
    enum = next((set(re.findall(r'`(\w+)`', l)) for l in doc[top:] if l.startswith('`unit` \u00b7')), set())
    start = next((i for i, l in enumerate(doc) if l.startswith('## Layers by what the task touches')), len(doc))
    rows = {}
    for l in doc[start + 1:]:
        if l.startswith('## '):
            break
        m = re.match(r'\| `(\w+)` \u2014 [^|]*\| \u22651 `(\w+)`', l)
        if m:
            rows[m.group(1)] = m.group(2)
    ok = bool(enum and rows) and set(got.get('LAYERS', ())) == enum and got.get('TOUCH_LAYER') == rows
    return (ok, f"plan-verify LAYERS={sorted(got.get('LAYERS', ()))} TOUCH_LAYER={got.get('TOUCH_LAYER')}; test-cases.md layers={sorted(enum)} touches={rows}",
            "LAYERS equals the layer list and TOUCH_LAYER equals the touch -> layer rows")

@check
def no_orphan_ref_files():
    """Every tier-3 ref and every own-skill sub-file (agents/refs, refs, skills/*/*) is named by a load line in another rule file."""
    cands = [f for f in files('refs/*.md') + files('refs/roles/**/*.md') + files('skills/*/**/*.md')
             if not f.startswith('skills/synced/') and not f.endswith('/SKILL.md')]
    texts = {r: read(r) for r in ruleset() + ['scripts/check-ruleset.sh']}
    orphans = []
    for c in cands:
        names = {c}
        if c.startswith('skills/'):
            names.add(c.split('/', 2)[2])
        if not any(n in t for r, t in texts.items() if r != c for n in names):
            orphans.append(c)
    return (not orphans, f"{len(cands)} ref files checked, orphans={orphans}",
            "0 orphans: every ref file path appears in at least one other rule file")

@check
def skill_shape():
    """Own skills: name equals the folder, description at most 1024 characters, opening "Use when", one outcome sentence and no step marker outside quoted triggers."""
    bad = []
    for f in files('skills/*/SKILL.md'):
        if f.startswith('skills/synced/'):
            continue
        try:
            fm = yaml.safe_load(read(f).split('---')[1]) or {}
        except Exception as e:
            bad.append(f"{f}: unparsable ({type(e).__name__})"); continue
        d = str(fm.get('description', ''))
        if fm.get('name') != f.split('/')[1]:
            bad.append(f"{f}: name={fm.get('name')!r}")
        if len(d) > 1024:
            bad.append(f"{f}: description {len(d)} chars")
        if not d.startswith('Use when'):
            bad.append(f"{f}: description does not open 'Use when'")
        if re.search(r'(?<![\w-])(first|then|next|step|after that)(?![\w-])|→|^\s*\d+\.', re.sub(r'"[^"]*"', '', d), re.I | re.M):
            bad.append(f"{f}: description narrates steps")
    return (not bad, f"off={bad}", "every own skill: name equals folder, description <= 1024 chars, opens 'Use when', no step marker outside quoted triggers")

# ---------------------------------------------------------------- N1-N2 (redundancy, not size)
# Q-R7-CAP: rule files carry no line or token ceiling; these two checks keep text from being
# stated twice (unreachable files stay no_orphan_ref_files' job). The prune test is not scriptable: it lives in
# refs/rule-authoring.md § Agent-file criteria and a reviewer applies it on every rule diff.
SHINGLE = 12                      # words; hit counts at 8, 12 and 16 are the threshold evidence, changing 12 is an analyst amend
N1_GLOBS = ('rules/core.md', 'rules/SDD.md', 'rules/UI_RULES.md', 'rules/FLOW.md', 'rules/RTK.md', 'refs/**/*.md', 'agents/*.md',
            'refs/roles/**/*.md', 'skills/*/SKILL.md', 'skills/*/references/**/*.md', 'commands/**/*.md')
N1_OUT = ('templates/', 'docs/', 'memory/', 'plugins/', '.cm-tmp/', '.original.md', 'skills/synced/')
DUP_BASELINE = [               # frozen from the first measured run on the package layout (2026-11-11): (fileA, fileB, first 12 words of the run); prune an entry when its duplicate is removed
    ('agents/brainstorm.md', 'refs/roles/brainstorm/intake.md', 'restate the problem in a paragraph list assumptions classify problem class and complexity'),
    ('agents/brainstorm.md', 'refs/roles/orchestrator/routing-contract.md', 'sub question file shortlist out of scope patterns doc sources scan round'),
    ('agents/brainstorm.md', 'refs/roles/orchestrator/spec-routing.md', 'has no stop of its own it is approved at the plan gate with the plan'),
    ('agents/devops.md', 'agents/implement.md', 'claude md 13 line 1 of the handback the json of output from line 2'),
    ('agents/devops.md', 'agents/scout.md', 'line 1 of the handback the json of output from line 2'),
    ('agents/implement.md', 'agents/orchestrator.md', "alone in the last wave's spawn and again at the end of"),
    ('agents/implement.md', 'agents/planner.md', 'design slug design md then claude plugin root rules ui rules md screens'),
    ('agents/implement.md', 'agents/reviewer.md', 'claude plugin root rules code-style discipline md then language md per language in'),
    ('agents/implement.md', 'agents/reviewer.md', 'plan dir design slug design md then claude plugin root rules ui rules md'),
    ('agents/implement.md', 'agents/reviewer.md', 'ranks 2 and 3 of claude plugin root rules code-style readme md precedence'),
    ('agents/implement.md', 'agents/reviewer.md', 'refs code-standards md coding principles think first simplicity surgical changes goal-driven checks'),
    ('agents/implement.md', 'agents/scout.md', 'line 1 of the handback the json of output from line 2'),
    ('agents/implement.md', 'refs/workflow-routing.md', 'one bypass record pattern fast-lane refs roles orchestrator gates md bypass record then'),
    ('agents/orchestrator.md', 'refs/roles/orchestrator/edge-cases.md', 'a diff ends with one closeout spawn agent implement task id closeout depends on every other task'),
    ('agents/orchestrator.md', 'refs/roles/orchestrator/spec-routing.md', 'a spec status blocked needs spec spec required misclassified spec drift bug spec class'),
    ('agents/planner.md', 'agents/reviewer.md', 'design slug design md then claude plugin root rules ui rules md'),
    ('agents/planner.md', 'skills/planning-dag/SKILL.md', 'new feature complex multi-module bug api socket db change cross-repo contract change high-risk infra or release'),
    ('agents/reviewer.md', 'refs/roles/reviewer/sources.md', "the live uc or the change's spec delta in covers uc refs change-files md"),
    ('agents/test.md', 'skills/testing-e2e/references/evidence-paths.md', 'only in a repo whose working tree would show the directory claude md 19 2'),
    ('commands/spec.md', 'refs/roles/brainstorm/modes.md', 'from code says what the code does not whether it is right'),
    ('refs/artifact-layout.md', 'refs/closeout.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/artifact-layout.md', 'refs/code-standards.md', 'the rules live here claude md keeps one pointer line per section read when writing'),
    ('refs/artifact-layout.md', 'refs/context-policy.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/artifact-layout.md', 'refs/final-response.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/artifact-layout.md', 'refs/option-explanation.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/artifact-layout.md', 'refs/workflow-routing.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/business-rule-testing.md', 'refs/roles/test/explore.md', 'a probe the system accepted where no recorded rule says whether it should'),
    ('refs/closeout.md', 'refs/code-standards.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/closeout.md', 'refs/context-policy.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/closeout.md', 'refs/final-response.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/closeout.md', 'refs/option-explanation.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/closeout.md', 'refs/roles/implement/close-task.md', 'a diff touching only claude records n a claude is never indexed skills gitnexus-flow rule 2'),
    ('refs/closeout.md', 'refs/roles/implement/close-task.md', 'unless that file exists so a resumed task keeps its first start'),
    ('refs/closeout.md', 'refs/roles/orchestrator/gates.md', 'agent-hub review-packet plan dir round round diff-only-out cm-tmp plan id r round independent diff-r round md'),
    ('refs/closeout.md', 'refs/workflow-routing.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/code-standards.md', 'refs/context-policy.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/code-standards.md', 'refs/final-response.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/code-standards.md', 'refs/option-explanation.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/code-standards.md', 'refs/roles/implement/craft.md', 'unless a measurement an acceptance criterion or known large data calls for an optimised algorithm'),
    ('refs/code-standards.md', 'refs/workflow-routing.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/commands/spec-check.md', 'rules/SDD.md', 'a labelled test exists but nobody wrote it back into the uc'),
    ('refs/context-policy.md', 'refs/final-response.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/context-policy.md', 'refs/option-explanation.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/context-policy.md', 'refs/workflow-routing.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/final-response.md', 'refs/option-explanation.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/final-response.md', 'refs/workflow-routing.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/option-explanation.md', 'refs/workflow-routing.md', 'the rules live here claude md keeps one pointer line per section read when'),
    ('refs/plan-files.md', 'refs/roles/planner/quality-gates.md', 'an expect opening exit n or rc n on every run step'),
    ('refs/roles/brainstorm/devops-boundary.md', 'refs/roles/orchestrator/edge-cases.md', 'inspection dns certificates host env or secrets migration backup restore against a deployed database'),
    ('refs/roles/brainstorm/devops-boundary.md', 'refs/roles/orchestrator/edge-cases.md', 'tree ssh scp rsync deploy rollback restart pm2 systemd nginx docker kubectl on a host'),
    ('refs/roles/brainstorm/modes.md', 'skills/testing-e2e/SKILL.md', 'change reaches a user a screen or an api a user calls'),
    ('refs/roles/devops/server-touching.md', 'refs/roles/implement/close-task.md', 'nothing at a sub-repo root or at workspace root outside the 19 1 folders nothing'),
    ('refs/roles/implement/sources.md', 'rules/SDD.md', 'a purely mechanical change rename format move records spec scope note and proceeds'),
    ('refs/roles/orchestrator/error-loop.md', 'refs/roles/orchestrator/gates.md', 'part a in full and part b per refs roles test retest-scope md'),
    ('refs/roles/orchestrator/gates.md', 'refs/workflow-routing.md', 'infra docs cli a logic bug with no visual change a copy-only edit'),
    ('refs/roles/reviewer/finding-bar.md', 'skills/review-checklist/SKILL.md', 'a convention true only in this workspace to the project memory file conventions'),
    ('refs/roles/reviewer/finding-bar.md', 'skills/review-checklist/references/security.md', 'and a non-destructive way to check a rejected candidate is still recorded'),
    ('refs/roles/reviewer/merge-policy.md', 'skills/review-checklist/references/merge.md', 'mcp mcp gitlab get merge request get merge request diffs list merge request changed files'),
    ('refs/roles/reviewer/taxonomy.md', 'rules/SDD.md', 'a migration or contract file in the diff a hardcoded business constant with no source'),
    ('refs/roles/reviewer/taxonomy.md', 'rules/SDD.md', 'four strong signals a new field column or business enum value a new route endpoint'),
    ('refs/roles/test/read-only.md', 'refs/roles/test/repro.md', 'on a copy under cm-tmp task id repro the real tree is'),
    ('refs/roles/test/retest-scope.md', 'refs/roles/test/two-pass.md', 'and step 3 over the one main flow it fixed a fix round does not widen step 3'),
    ('rules/UI_RULES.md', 'skills/design-ui/references/ux-rules-flow.md', 'exit duration as a share of enter and stagger per item group ux motion refs thresholds md'),
    ('skills/devops-deploy/SKILL.md', 'skills/devops-deploy/references/release.md', 'a rollback never run on this host is a plan not a guarantee'),
]
N2_BASELINE = []                  # frozen from the same run: no CLAUDE.md pointer section held more than its pointer (0 of 21)

N1_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
N1_UNIT_START = re.compile(r'^\s*(?:[-*+]\s|\d+[.)]\s|\|)')

def n1_files() -> list:
    out = set()
    for g in N1_GLOBS:
        out.update(files(g))
    return sorted(f for f in out if not any(o in f for o in N1_OUT))

def n1_units(f):
    """[(first line number, [words])] per paragraph, list item or table row of f, with fenced
    code and double-quoted text dropped (a verbatim quote is a citation) and markdown marks stripped."""
    units, cur, start, fence = [], [], 0, False
    def flush():
        if cur:
            text = N1_QUOTED.sub(' ', ' '.join(cur))
            words = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())
            if words:
                units.append((start, words))
        cur.clear()
    for i, l in enumerate(lines(f), 1):
        if l.lstrip().startswith('```'):
            flush(); fence = not fence; continue
        if fence:
            continue
        if not l.strip():
            flush(); continue
        if N1_UNIT_START.match(l) or not cur:
            flush(); start = i
        cur.append(l)
    flush()
    return units

def n1_hits(words: int) -> list:
    """[(fileA:line, fileB:line, run text)]: a `words`-word window found in two different files,
    adjacent windows of one unit pair merged into a maximal run."""
    index = {}
    for f in n1_files():
        for ln, ws in n1_units(f):
            for p in range(len(ws) - words + 1):
                index.setdefault(tuple(ws[p:p + words]), []).append((f, ln, p, ws))
    groups = {}
    for sh, occ in index.items():
        if len({o[0] for o in occ}) < 2:
            continue
        for a in range(len(occ)):
            for b in range(a + 1, len(occ)):
                x, y = occ[a], occ[b]
                if x[0] == y[0]:
                    continue
                if x[0] > y[0]:
                    x, y = y, x
                groups.setdefault((x[0], x[1], y[0], y[1], x[2] - y[2]), []).append((x[2], x[3]))
    hits = []
    for (fa, la, fb, lb, _d), ps in groups.items():
        ps.sort(key=lambda t: t[0])
        run = [ps[0]]
        for q in ps[1:] + [None]:
            if q is not None and q[0] == run[-1][0] + 1:
                run.append(q); continue
            ws = run[0][1]
            hits.append((f"{fa}:{la}", f"{fb}:{lb}", ' '.join(ws[run[0][0]:run[-1][0] + words])))
            run = [q] if q is not None else []
    return sorted(hits)

def n1_baselined(hit, baseline):
    fa, fb = hit[0].rsplit(':', 1)[0], hit[1].rsplit(':', 1)[0]
    return any(b[0] == fa and b[1] == fb and b[2] in hit[2] for b in baseline)

@check
def rule_no_duplicate_passage():
    """No 12-word run of prose appears in two different rule files, outside DUP_BASELINE."""
    h12 = n1_hits(SHINGLE)
    new = [h for h in h12 if not n1_baselined(h, DUP_BASELINE)]
    pairs = {(h[0].rsplit(':', 1)[0], h[1].rsplit(':', 1)[0]) for h in h12}
    stale = [b for b in DUP_BASELINE if not any(b[0] == fa and b[1] == fb and b[2] in h[2]
             for h in h12 for fa, fb in [(h[0].rsplit(':', 1)[0], h[1].rsplit(':', 1)[0])])]
    return (not new, f"files={len(n1_files())}, hits at 8/12/16 words={len(n1_hits(8))}/{len(h12)}/{len(n1_hits(16))}, "
            f"baselined={len(h12) - len(new)}, stale baseline entries={len(stale)} {[b[:2] for b in stale]}, new={[h[:2] + (h[2][:60],) for h in new]}",
            f"0 runs of >= {SHINGLE} words shared by two files outside DUP_BASELINE; quoted text and fenced code exempt")

@check
def pointer_section_one_line():
    """A CLAUDE.md section whose first body line is a backticked refs/ pointer holds that one line only (CLAUDE.md:3)."""
    secs, head, body = [], None, []
    for l in lines('rules/core.md') + ['# END']:
        if l.startswith('#'):
            if head is not None:
                secs.append((head, [x for x in body if x.strip()]))
            head, body = l.strip(), []
        else:
            body.append(l)
    ptr = [(h, b) for h, b in secs if b and re.match(r'^`refs/[^`]+`', b[0].strip())]
    bad = [h for h, b in ptr if len(b) != 1]
    new = [h for h in bad if h not in N2_BASELINE]
    stale = [h for h in N2_BASELINE if h not in bad]
    return (not new, f"{len(ptr)} pointer sections, {len(bad)} hold more than the pointer, baselined={len(bad) - len(new)}, "
            f"stale baseline entries={stale}, new={new}",
            "every CLAUDE.md section opening with a refs/ pointer holds that one line, outside N2_BASELINE")

# ---------------------------------------------------------------- driver

fails = 0
for fn in CHECKS:
    ok, measured, expected = fn()
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {fn.__name__:<24} measured: {measured}\n"
          f"{'':30}expected: {expected}")
print(f"\n{len(CHECKS) - fails}/{len(CHECKS)} checks passed")
sys.exit(1 if fails else 0)
PY
