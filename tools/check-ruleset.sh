#!/usr/bin/env bash
# Ruleset invariants as runnable checks. Every check prints the measured value and the
# expected one, so a PASS is evidence rather than an assertion. Exits 1 on any FAIL.
#
# Counting is done in python3 on purpose: `wc -l < f`, `diff a b` and
# `LC_ALL=C grep -c '[^[:print:]]'` all exit 0 with a wrong answer under a command-rewriting
# hook. A whole-file `grep -c` answers a different question than a per-section count, so every range is sliced before counting.
#
# Repo layout: ROOT is the plugin folder plugins/agent-hub; the injected core is rules/core.md.
# Run it as `python3 tools/check.py ruleset` or `bash tools/check-ruleset.sh [PLUGIN_ROOT]`.
# A check whose declared need is a package that has not landed prints PENDING <pkgs> instead of FAIL.
# `WP_DONE` (space-separated package letters, or ALL) says which packages have landed; unset it is ALL, so
# nothing is pending, a deleted rule file is a FAIL, and the acceptance line is the literal `N/N checks passed`.
# Only an explicit subset (WP_DONE="A B") keeps the PENDING path, and a pending check still exits non-zero.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${1:-$REPO/plugins/agent-hub}"
[ -d "$ROOT" ] || { echo "FATAL: no plugin root at $ROOT"; exit 2; }
exec python3 -B - "$ROOT" "$REPO" <<'PY'
import ast, os, re, sys, glob, fnmatch, subprocess
import yaml

ROOT = sys.argv[1]
REPO = sys.argv[2]
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

# Vendored blocks (upstream text kept byte-equal) are not owned text: the checks that read prose, pins and
# pointers skip them, because an upstream line cannot be edited to satisfy a rule of this package.
VEND_BEGIN = re.compile(r'^\s*<!--\s*vendored:begin\b')
VEND_END   = re.compile(r'^\s*<!--\s*vendored:end\b')

def owned_lines(f):
    """Yield `(line_no, line)` of f outside `<!-- vendored:begin ... -->` / `<!-- vendored:end ... -->`."""
    vend = False
    for i, l in enumerate(lines(f), 1):
        if VEND_BEGIN.match(l):
            vend = True
        elif VEND_END.match(l):
            vend = False
        elif not vend:
            yield i, l

# The manifest tells which package owns a path; `landed` is the PENDING rule's one question.
def _load_manifest():
    rows = []
    try:
        for l in open(os.path.join(REPO, 'tools', 'v2-manifest.tsv'), encoding='utf-8'):
            c = l.rstrip('\n').split('\t')
            if len(c) == 4:
                rows.append(c)
    except OSError:
        pass
    return rows

MANIFEST = _load_manifest()
PKG_OF = {r[0]: r[3] for r in MANIFEST}
PACKAGES = sorted({r[3] for r in MANIFEST})
PLUGIN_REL = os.path.relpath(os.path.abspath(ROOT), os.path.abspath(REPO)).replace(os.sep, '/')
_landed = {}

def landed(pkg):
    """pkg is landed when WP_DONE lists it or ALL; WP_DONE unset means ALL."""
    if pkg not in _landed:
        toks = os.environ.get('WP_DONE', 'ALL').split()
        _landed[pkg] = 'ALL' in toks or pkg in toks
    return _landed[pkg]

def unlanded(needs):
    """The needs that are not landed; `*` means every package of the manifest."""
    pk = PACKAGES if '*' in needs else needs
    return sorted(p for p in dict.fromkeys(pk) if not landed(p))

def pending_pkg(ref, citing=''):
    """The unlanded package that owns `ref` (a path as a pointer or pin writes it) when that file is absent and
    has a manifest row; None otherwise. `ref` resolves from ROOT, from the citing file's folder, or by a
    basename that names exactly one manifest row."""
    t0 = ref.lstrip('~').lstrip('/')
    t0 = t0[len('.claude/'):] if t0.startswith('.claude/') else t0
    near = os.path.normpath(os.path.join(os.path.dirname(citing), ref)).replace(os.sep, '/')
    cands = [t0, near]
    base = ref.rsplit('/', 1)[-1]
    same = [k[len(PLUGIN_REL) + 1:] for k in PKG_OF if k.startswith(PLUGIN_REL + '/') and k.rsplit('/', 1)[-1] == base]
    if len(same) == 1:
        cands.append(same[0])
    for c in cands:
        pk = PKG_OF.get(PLUGIN_REL + '/' + c)
        if pk and not os.path.exists(os.path.join(ROOT, c)) and not landed(pk):
            return pk
    return None

def files(pat):        return sorted(rel(p) for p in glob.glob(os.path.join(ROOT, pat), recursive=True))

def ruleset():
    """Every hand-written rule file -- a file that STATES a rule. Third-party and archived
    trees are out by path, and so are the records, which quote rules rather than state them."""
    out = []
    for p in glob.glob(os.path.join(ROOT, '**/*.md'), recursive=True):
        r = rel(p)
        if not any(s in r + '/' for s in SKIP):
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
VERBATIM_RECORDS = ()
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
    for i, l in owned_lines(f):
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
    shallower. Scoping before counting is the whole point — twelve plan `verification`
    commands once grepped a whole file and answered a different question."""
    m = re.search(head_re, text, re.M)
    if not m:
        return None
    depth = len(re.match(r'#*', m.group(0)).group(0))
    tail = text[m.end():]
    nxt = re.search(r'^#{1,%d} ' % depth, tail, re.M)
    return m.group(0) + (tail[:nxt.start()] if nxt else tail)

def router_table():
    """refs/gates.md § A table A: {blocking status -> the agents that may return it}."""
    seg = re.search(r'\*\*A\. Blocking `status`.*?\*\*B\. Booleans', read('refs/gates.md'), re.S)
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
    """{agent -> model} from the one table whose header row has the adjacent cells `Agent` and `Model`, under
    head_re (None: the whole text). Column pairs come from the header row, never from position. The model is the
    first lower-case word of the cell, so `sonnet (opus at L4)` reads `sonnet`."""
    ls = ((section(text, head_re) or '') if head_re else text).splitlines()
    hdr = [i for i, l in enumerate(ls) if re.match(r'^\|(?:[^|]*\|)*?\s*Agent\s*\|\s*Model\s*\|', l)]
    if len(hdr) != 1:
        return None, f"{label}: {len(hdr)} `Agent | Model` header rows, expected 1"
    head = [c.strip() for c in ls[hdr[0]].strip().strip('|').split('|')]
    pairs = [(i, i + 1) for i in range(len(head) - 1)
             if head[i] == 'Agent' and head[i + 1] == 'Model']
    out = {}
    for l in ls[hdr[0] + 2:]:
        if not l.startswith('|'):
            break
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        for a, m in pairs:
            if m < len(c) and re.fullmatch(r'`?(?:agent-hub:)?[a-z-]+`?', c[a]):
                w = re.search(r'[a-z]+', c[m].replace('*', ''))
                out[c[a].strip('`').replace('agent-hub:', '')] = w.group(0) if w else ''
    return (out, None) if out else (None, f"{label}: 0 rows parsed")


# Roles that live in an optional plugin or were removed: a row naming one is not a defect of this package.
NOT_SHIPPED = {'auditor'}

CHECKS = []
def check(*needs):
    """Register a check. `needs` are the packages whose files it cannot pass without (`*`: every package);
    while one is not landed a failure prints PENDING instead of FAIL."""
    def deco(fn):
        fn.needs = needs
        CHECKS.append(fn)
        return fn
    return deco


# ---------------------------------------------------------------- checks

@check('H', 'I', 'J')
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

@check('G', 'H')
def model_assignment_agrees():
    """The model an agent runs on is written in two places: the frontmatter `model:` of each agents/*.md
    (the only one the harness reads) and the one `| Agent | Model |` table of refs/effort-routing.md. They must
    agree in both directions: a row with no agent file, an agent file with no row. A source that parses to no
    rows is a FAIL, never a pass."""
    try:
        import yaml
    except ImportError:
        return (False, "pyyaml not installed", "pyyaml importable")
    fm = {os.path.basename(f)[:-3]: (yaml.safe_load(read(f).split('---')[1]) or {}).get('model')
          for f in files('agents/*.md')}
    table, err = model_table(read('refs/effort-routing.md'), None, 'refs/effort-routing.md')
    bad = [err] if err else []
    table = table or {}
    for a, want in sorted(fm.items()):
        if want is None or table.get(a) != want:
            bad.append(f"{a}: frontmatter={want} table={table.get(a)}")
    bad += [f"{a}: a row in refs/effort-routing.md, but no agents/{a}.md"
            for a in sorted(table) if a not in fm and a not in NOT_SHIPPED]
    return (not bad, f"{len(fm)} agents, {len(table)} table rows | off={bad}",
            "one model per agent: frontmatter equals the refs/effort-routing.md table, both directions")

@check()
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

@check()
def no_eager_imports():
    """No `@file` eager import in the ruleset. SDD.md and UI_RULES.md cost 6,415 tokens in
    every session while eager, including the work that never opens a spec."""
    hits = []
    for f in ruleset():
        fence = False
        for i, l in owned_lines(f):
            if l.lstrip().startswith('```'):
                fence = not fence
            elif not fence and re.match(r'^@[A-Za-z~./]', l):
                hits.append(f"{f}:{i}")
    return (not hits, f"{len(hits)}: {hits}", "0 outside vendored blocks and fences")

@check('F1')
def self_counts_agree():
    """§19.1's opening sentence counts its own exceptions in words, and that count has already
    changed more than once. It is compared against the rows, never against a second written
    number: every path in that table resolves from {workspace_root} except the ones under
    another root, so a row whose path starts with no WORKSPACE prefix is an exception.
    It fails loudly on a rewording rather than passing on an empty parse."""
    WORKSPACE = ('docs/', '.cm-tmp/', '{plan_dir}/')  # {plan_dir} resolves under docs/ (refs/plan-files.md § Where a plan lives)
    WORDS = {'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
    bad = []
    sec = section(read('refs/artifact-layout.md'), r'^#{1,2} (?:\d+(?:\.\d+)*\.? )?Where writing is allowed') or ''
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
        bad.append("Where writing is allowed: no readable 'The <number> that do not' opening sentence")
    elif n != len(other):
        bad.append(f"Where writing is allowed opening says {said.group(1)} ({n}) but {len(other)} rows "
                   f"name another root: {other}")
    return (not bad,
            f"Where writing is allowed opening={said.group(1) if said else 'unreadable'} vs "
            f"{len(other)} rows naming another root | off={bad}",
            "the opening number equals the rows whose path names a root other than {workspace_root}")

@check('H')
def reviewer_categories_anchored():
    """Every `category` value reviewer can emit resolves to a section or a Raised-from row, and
    every category name cited OUTSIDE agents/reviewer.md still resolves back to that enum. A value
    with no anchor is not a category, and a taxonomy whose three totals only add up to each other
    passes its own arithmetic while every input is wrong.

    The outward half is the one a rename inside agents/reviewer.md cannot survive: enum, sections
    and totals all move together, so the file stays self-consistent while another rule file still
    routes a name that now names nothing. Citations are read by the two shapes the ruleset
    actually writes, `` `category: x` `` and ``finding `x` ``; the core and orchestrator are not
    cited from any more.

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
    return (not orphan and not dangling and len(anchors) == 14 and len(enum) == 26,
            f"enum={len(enum)}, sections={len(anchors)}, raised-from={len(enum) - len(anchors)},"
            f" orphans={orphan}, cited elsewhere={sum(len(v) for v in cited.values())} in"
            f" {len(cited)} names, dangling={dangling}",
            "26 values = 14 sections + 12 raised-from, 0 orphans, and every category cited "
            "outside agents/reviewer.md still in the enum")

@check('F1', 'H')
def status_enum_matches_router():
    """refs/gates.md § A routes a blocking status per agent; the agent's own § Output enum must
    be able to return it. A status the file cannot emit forces the agent onto `failed`, which
    refs/gates.md § A routes somewhere else entirely."""
    router, extra = router_table(), {'completed', 'in_progress'}
    bad = []
    for f in files('agents/*.md'):
        name = os.path.basename(f)[:-3]
        m = re.search(r'"status"\s*:\s*"([^"]+)"', read(f))
        if not m:
            owed = [s for s, who in router.items() if name in who]
            if owed:
                bad.append(f"{f}: no status field, refs/gates.md § A owes it {owed}")
            continue
        own = set(m.group(1).split('|'))
        for s, who in router.items():
            if (name in who or who == ['any']) and s not in own:
                bad.append(f"{f}: refs/gates.md § A routes {s} from {name}, enum lacks it")
        for s in own - set(router) - extra:
            bad.append(f"{f}: emits {s}, refs/gates.md § A does not route it")
    return (not bad, f"{len(bad)} mismatches: {bad}", "every routed status in its agent's enum")

@check('H')
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

@check('H', 'I', 'J')
def command_modes_exist():
    """A `mode=` a slash command asks for must exist in some agent's mode enum."""
    known = set()
    for f in files('agents/*.md'):
        for e in re.findall(r'"mode"\s*:\s*"([^"]+)"', read(f)):
            known |= {x for x in e.split('|') if x != 'string'}
    bad = [f"{f}: {m}" for f in files('commands/*.md')
           for m in sorted(set(re.findall(r'mode=([a-z-]+)', read(f)))) if m not in known]
    return (not bad, f"{len(bad)} unknown: {bad}", "every command mode= in an agent enum")

@check('H')
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

@check()
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

@check('F1', 'F4', 'H', 'O')
def single_statement_invariants():
    """Each of these is deliberately written down exactly once; a second copy is what drifts.

    ONCE counts a needle across the ruleset and demands exactly one hit; a needle at 0 and a needle at 2 are
    different events (a home reworded out from under the needle, against a second copy) and each says which.
    The `header format` needle carries the guard of the dropped header_format_identical check.
    The never-compress list is one heading in skills/context-compression/SKILL.md plus a pointer in the
    `Context window` section of refs/context-policy.md. The `Evidence storage` heading is found by search,
    exactly one in the ruleset; the three other citers keep the pointer, and agents/test.md carries it too when
    the heading moved out of it."""
    ONCE = {'viewport enum': '320 · 768 · 1024 · 1366 · 1440',
            'memory discovery walk': 'Discovery order — the only statement of it',
            'comment categories': 'A decision other code depends on',
            'header format': '[<agent> · model: <haiku|sonnet|opus>]'}
    HEAD = '## Hard rules (apply to all modes)'
    POINTER = r'context-compression/SKILL\.md[^\n]{0,40}§ Hard rules'
    CITERS = {'Context window': ('refs/context-policy.md', r'^# (?:\d+\. )?Context window')}
    EV_HEAD = r'^#{1,6} Evidence storage\s*$'
    EV_POINTER = '§ Evidence storage'
    EV_CITERS = ['skills/design-ui/SKILL.md', 'skills/review-checklist/references/design.md',
                 'skills/testing-e2e/SKILL.md']
    counts, bad = {}, []
    for label, needle in ONCE.items():
        hits = {f: read(f).count(needle) for f in ruleset() if needle in read(f)}
        counts[label] = sum(hits.values())
        if counts[label] == 0:
            bad.append(f"{label}: needle not found -- the home may have been reworded: {needle!r}")
        elif counts[label] != 1:
            bad.append(f"{label}: {counts[label]} copies in {hits}")
    heads = read('skills/context-compression/SKILL.md').count(HEAD)
    if heads != 1:
        bad.append(f"never-compress heading: {heads} copies of {HEAD!r}, expected 1")
    dangling = [s for s, (f, head_re) in CITERS.items()
                if not re.search(POINTER, section(read(f), head_re) or '')]
    if dangling:
        bad.append(f"never-compress pointer: missing from {[CITERS[s][0] + ' ' + s for s in dangling]}")
    homes = {f: len(re.findall(EV_HEAD, read(f), re.M)) for f in ruleset()}
    homes = {f: n for f, n in homes.items() if n}
    if sum(homes.values()) != 1:
        bad.append(f"evidence-storage heading: {homes}, expected exactly one in the ruleset")
    if 'agents/test.md' not in homes:
        EV_CITERS.append('agents/test.md')
    ev_dangling = [f for f in EV_CITERS if EV_POINTER not in read(f)]
    if ev_dangling:
        bad.append(f"evidence-storage pointer: missing from {ev_dangling}")
    return (not bad,
            f"{counts}, never-compress heading={heads}, pointers={len(CITERS) - len(dangling)}/{len(CITERS)}, "
            f"evidence heading in {sorted(homes)}, "
            f"evidence pointers={len(EV_CITERS) - len(ev_dangling)}/{len(EV_CITERS)}, off={bad}",
            "each stated exactly once, the never-compress heading once with a pointer in the Context window "
            "section of refs/context-policy.md, and the evidence-storage heading once with its pointer in each citer")

@check('H')
def test_modes_in_description():
    """agents/test.md `description` is what the router matches on; every value of its `"mode"` enum belongs."""
    t = read('agents/test.md')
    m = re.search(r'"mode"\s*:\s*"([^"]+)"', t)
    modes = [x.strip() for x in m.group(1).split('|') if x.strip()] if m else []
    d = re.search(r'^description:.*$', t, re.M)
    miss = [x for x in modes if not d or x not in d.group(0)]
    return (bool(modes) and bool(d) and not miss, f"modes={modes}, missing={miss}",
            "at least one mode parsed from the enum, and each named in the description")

@check()
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

    HELD_OUT is named rather than left unmatched. The two plan YAML
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
               'refs/*.md', '*.md', 'refs/roles/**/*.md', 'refs/vendored/*.md', 'store/**/*.md',
               'templates/analysis/*.md', 'templates/spec/spec-delta-template.md',
               'templates/plan/tasks-template.md')
    VIETNAMESE = ('templates/plan/plan.vi-template.md',)   # scrub-allow: legacy glob, read only when present
    HELD_OUT = ('templates/SERVER-INFO.md',
                'templates/commit/EXAMPLE-commit.md', 'templates/test/FAILURE-report-template.md')
    ALLOW = {'refs/option-explanation.md': ('Giải pháp', 'Cách làm', 'các bước', 'Tác động',  # scrub-allow: legacy allowed Vietnamese words
                                            'Khi nào chọn', '1-2 câu')}  # scrub-allow: legacy allowed Vietnamese words
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
            f"English ones; and nothing held out reachable by a glob here")

@check('E', 'F1')
def lane_ids_agree():
    """The lane ids are written in two files: the lane table of rules/core.md (header `| Lane | ... |`, the
    `add-ons` row excluded) and the `## <lane id> ...` headings of refs/lanes.md. The table must name at least
    one id, name none twice, and cover every heading; a lane with no detail section is legal and only printed.
    Headings only, because a token scan would collide with the effort tiers `L0`-`L4`."""
    ls = lines('rules/core.md')
    hdr = [i for i, l in enumerate(ls) if re.match(r'^\|\s*Lane\s*\|', l)]
    if len(hdr) != 1:
        return (False, f"{len(hdr)} `| Lane |` header rows in rules/core.md", "exactly one lane table")
    C = []
    for l in ls[hdr[0] + 2:]:
        if not l.startswith('|'):
            break
        m = re.match(r'[`*\s]*([^\s`*|]+)', l.strip().strip('|').split('|')[0])
        if m and not m.group(1).lower().startswith('add-on'):
            C.append(m.group(1))
    R = [m.group(1) for m in (re.match(r'^## (L\d+|L-[a-z]+)\b', l) for l in lines('refs/lanes.md')) if m]
    bad = []
    if not C:
        bad.append("the lane table names no id")
    dup = sorted({c for c in C if C.count(c) > 1})
    if dup:
        bad.append(f"duplicate lane ids in the table: {dup}")
    bad += [f"{r}: a refs/lanes.md heading with no row in the lane table" for r in R if r not in C]
    return (not bad, f"table={C}, headings={R}, table without a heading={sorted(set(C) - set(R))} | off={bad}",
            "the table names >= 1 id, none twice, and every refs/lanes.md `## <lane id>` heading is in it")

@check()
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
    bad, checked, quoted, pend = [], 0, 0, set()
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
                    pk = pending_pkg(target, f)
                    if pk:
                        pend.add(pk)  # a planned file that has not landed: pending, not wrong
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
            f"{quoted} carrying a quotation, {len(bad)} off: {bad}"
            + (f" | pending items point at unlanded {sorted(pend)}" if pend else ''),
            "no line pin into a .md rule file FROM a rule file (QT-3, rule files only); and "
            "every pin that resolves, in a rule file or a record, in range, non-blank, and "
            "still holding the quotation written beside it; vendored blocks are skipped", pend)


@check()
def section_ref_exists():
    """The core is cited by heading, never by number: no owned text of `scanned()` matches
    `(CLAUDE.md|core.md)` then `§` then a digit within 12 characters (C1: the core has no numbered section).
    Vendored blocks are skipped by `pointer_lines`; in a record fenced blocks and quoted spans are too."""
    REF = re.compile(r'(?:CLAUDE\.md|core\.md)[^\n]{0,12}?§\s?\d')
    bad = []
    for f in scanned():
        for i, l, in_quote in pointer_lines(f):
            for m in REF.finditer(l):
                if not in_quote(m.start()):
                    bad.append(f"{f}:{i} {m.group(0)!r}")
    return (not bad, f"{len(scanned())} files scanned, {len(bad)} numbered citations of the core: {bad}",
            "0 numbered citations of CLAUDE.md or core.md in owned text")

@check()
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
    `SDD.md §11.1`, `rules/code-style/_discipline.md §5` -- is checked by nothing
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

    bad, checked, offscope, pend = [], 0, 0, set()
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
                    pk = pending_pkg(m.group(1), f)
                    if pk:
                        pend.add(pk)  # the file is a manifest row that has not landed
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
            f"{offscope} off-scope, {len(bad)} dangling: {bad}"
            + (f" | pending items point at unlanded {sorted(pend)}" if pend else ''),
            "every `file.md § Section` pointer names a heading that file has, cited from a "
            "rule file or a record; vendored blocks are skipped", pend)

def tier3_refs():      return files('refs/*.md') + files('refs/roles/**/*.md')

@check()
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

@check('*')
def no_orphan_ref_files():
    """Every tier-3 ref and every own-skill sub-file (agents/refs, refs, skills/*/*) is named by a load line in another rule file."""
    cands = [f for f in files('refs/*.md') + files('refs/roles/**/*.md') + files('refs/vendored/*.md')
             + files('skills/*/**/*.md') if not f.endswith('/SKILL.md')]
    texts = {r: read(r) for r in ruleset()}
    orphans = []
    for c in cands:
        names = {c}
        if c.startswith('skills/'):
            names.add(c.split('/', 2)[2])
        if not any(n in t for r, t in texts.items() if r != c for n in names):
            orphans.append(c)
    return (not orphans, f"{len(cands)} ref files checked, orphans={orphans}",
            "0 orphans: every ref file path appears in at least one other rule file")

@check()
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
N1_GLOBS = ('rules/core.md', 'rules/SDD.md', 'rules/UI_RULES.md', 'refs/**/*.md', 'agents/*.md',
            'refs/roles/**/*.md', 'skills/*/SKILL.md', 'skills/*/references/**/*.md', 'commands/**/*.md')
N1_OUT = ('templates/', 'docs/', 'memory/', 'plugins/', '.cm-tmp/', '.original.md', 'skills/synced/')
DUP_BASELINE = []              # starts empty; an entry is added only by name: (fileA, fileB, first 12 words of the run) with a reason, and listed in the WP-K report
N2_BASELINE = []                  # frozen from the same run: no CLAUDE.md pointer section held more than its pointer (0 of 21)

N1_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
N1_UNIT_START = re.compile(r'^\s*(?:[-*+]\s|\d+[.)]\s|\|)')

def n1_files() -> list:
    out = set()
    for g in N1_GLOBS:
        out.update(files(g))
    return sorted(f for f in out if not any(o in f for o in N1_OUT) and not f.startswith('store/'))

def n1_units(f):
    """[(first line number, [words])] per paragraph, list item or table row of f, with fenced
    code and double-quoted text dropped (a verbatim quote is a citation) and markdown marks stripped."""
    units, cur, start, fence, vend = [], [], 0, False, False
    def flush():
        if cur:
            text = N1_QUOTED.sub(' ', ' '.join(cur))
            words = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())
            if words:
                units.append((start, words))
        cur.clear()
    front = None   # None before line 1, True inside a leading `---` frontmatter, False after it
    for i, l in enumerate(lines(f), 1):
        if i == 1:
            front = l.strip() == '---'
        elif front and l.strip() == '---':
            front = False
            continue
        if front and re.match(r'^(?:disallowedTools|tools):', l):
            continue    # a deny/allow list is an identical value on purpose, not duplicated prose
        if VEND_BEGIN.match(l):
            flush(); vend = True; continue
        if VEND_END.match(l):
            vend = False; continue
        if vend:
            continue
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

@check()
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

COMMUNITY_GITLAB = ('merge_merge_request', 'approve_merge_request', 'unapprove_merge_request', 'get_merge_request_diffs',
    'list_merge_request_changed_files', 'get_merge_request_conflicts', 'get_merge_request_approval_state', 'create_merge_request',
    'create_merge_request_note', 'create_merge_request_discussion_note', 'create_draft_note', 'bulk_publish_draft_notes')

@check()
def gitlab_tool_names_official():
    """Every mcp__mcp_gitlab__ name under plugins/ is one of the 42 names of refs/gitlab-tools.yaml; no bare community-only name remains."""
    tools = yaml.safe_load(read('refs/gitlab-tools.yaml')).get('tools') or []
    names = {t['name'] for t in tools}
    list_ok = len(tools) == 42 and len(names) == 42 and sum(t['kind'] == 'write' for t in tools) == 11 and all(n.startswith('mcp__mcp_gitlab__') for n in names)
    parent = os.path.dirname(os.path.abspath(ROOT))
    base = parent if os.path.basename(parent) == 'plugins' else ROOT
    word = re.compile(r'\b(?:' + '|'.join(COMMUNITY_GITLAB) + r')\b')
    unofficial, bare = [], []
    for dp, _, fs in os.walk(base):
        for f in fs:
            p = os.path.join(dp, f)
            try:
                ls = open(p, encoding='utf-8').read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for i, l in enumerate(ls, 1):
                unofficial += [f'{p}:{i} {m}' for m in re.findall(r'mcp__mcp_gitlab__[a-z_]+', l) if m not in names]
                bare += [f'{p}:{i} {m}' for m in word.findall(l)]
    return (list_ok and not unofficial and not bare, f"official names={len(names)}, unofficial prefixed names={len(unofficial)} {unofficial[:3]}, bare community names={len(bare)} {bare[:3]}",
            "42 official names (11 write), 0 unofficial prefixed names and 0 bare community names under plugins/")

@check('E')
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

@check()
def tree_matches_manifest():
    """The files present (tracked plus untracked-not-ignored; no git: a walk) equal the rows of
    tools/v2-manifest.tsv, and every PORT row is byte-identical to its source at cc3a0ee. `extra:` and `differs:`
    are FAILs; `missing:` is pending while the row's package has not landed and a FAIL once it has. The PORT
    compare runs only when cc3a0ee is in this clone."""
    def git(*a):
        return subprocess.run(['git', '-C', REPO, *a], capture_output=True)
    rows = MANIFEST
    paths = {r[0] for r in rows}
    ls = git('ls-files', '-z', '--cached', '--others', '--exclude-standard')
    if ls.returncode == 0:
        present = {p for p in ls.stdout.decode('utf-8', 'replace').split('\0') if p and os.path.exists(os.path.join(REPO, p))}
    else:
        present = set()
        for dp, ds, fs in os.walk(REPO):
            ds[:] = [d for d in ds if d != '.git']
            present |= {os.path.relpath(os.path.join(dp, f), REPO).replace(os.sep, '/') for f in fs}
    real = ["extra: " + p for p in sorted(present - paths)]
    pend, missing = set(), []
    for p in sorted(paths - present):
        if landed(PKG_OF[p]):
            real.append("missing: " + p)
        else:
            pend.add(PKG_OF[p]); missing.append(p)
    compared, note = 0, ''
    if git('cat-file', '-e', 'cc3a0ee').returncode == 0:
        for p, disp, src, _ in rows:
            if disp != 'PORT' or p not in present:
                continue
            a = git('show', f'cc3a0ee:{src}')
            compared += 1
            if a.returncode != 0 or a.stdout != open(os.path.join(REPO, p), 'rb').read():
                real.append("differs: " + p)
    else:
        note = ' | PORT compare skipped: cc3a0ee not in this clone'
    return (not real, f"{len(rows)} rows, {len(present)} present, {len(missing)} not placed yet "
            f"(packages {sorted(pend)}), {compared} PORT rows compared{note} | off={real[:10]}"
            + (f" (+{len(real) - 10} more)" if len(real) > 10 else ''),
            "present files == manifest rows, every PORT row byte-identical to its source", pend)

@check('D')
def quoted_passages_attributed():
    """Package D's check (tools/attribution_check.py): every vendored block equals its pinned upstream lines and
    its origin is credited in THIRD_PARTY_NOTICES.md, and no run of 3 or more identical lines (at least 60 stripped characters) of a pinned upstream file stands
    uncredited outside markers. The module is imported when present."""
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import attribution_check
    except ImportError:
        return (False, "tools/attribution_check.py not found", "the module of package D")
    bad = attribution_check.quoted_passages_attributed(REPO)
    return (not bad, f"{len(bad)} problems: {bad[:5]}", "0 problems")

def _store_check(name, label):
    STORE = os.path.join(ROOT, 'store')
    if not os.path.isdir(STORE):
        return (False, "plugins/agent-hub/store is absent", label)
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import store_checks
    except ImportError:
        return (False, "tools/store_checks.py not found", label)
    fn = getattr(store_checks, name)
    bad = fn(STORE, os.path.join(REPO, 'THIRD_PARTY_NOTICES.md')) if name == 'store_licensed' else fn(STORE)
    return (not bad, f"{len(bad)} problems: {bad[:5]}", label)

@check('M1', 'M2')
def store_pinned():
    return _store_check('store_pinned', "sha256 of every listed store file equals the catalog")

@check('M1', 'M2')
def store_no_exec():
    return _store_check('store_no_exec', "no script file and no exec bit anywhere in the store")

@check('M1', 'M2')
def store_guard_present():
    return _store_check('store_guard_present', "a row with side effects has a guard and an owned head")

@check('M1', 'M2')
def store_licensed():
    return _store_check('store_licensed', "every store row carries an allowed licence credited in THIRD_PARTY_NOTICES.md")

# ---------------------------------------------------------------- driver

passed, fails, npend, pkgs = 0, 0, 0, set()
for fn in CHECKS:
    try:
        res = fn()
    except Exception as e:
        res = (False, f"{type(e).__name__}: {e}", "no exception")
    ok, measured, expected = res[:3]
    items = sorted(res[3]) if len(res) > 3 else []
    unl = unlanded(fn.needs)
    if ok and unl:
        tag = f"PASS (partial: {' '.join(unl)} not landed)"
        passed += 1
    elif ok and items:
        tag, npend = f"PENDING {' '.join(items)}", npend + 1
        pkgs.update(items)
    elif ok:
        tag = 'PASS'
        passed += 1
    elif unl:
        tag, npend = f"PENDING {' '.join(unl)}", npend + 1
        pkgs.update(unl)
    else:
        tag = 'FAIL'
        fails += 1
    print(f"{tag}  {fn.__name__:<24} measured: {measured}\n"
          f"{'':30}expected: {expected}")
print(f"\n{passed}/{len(CHECKS)} checks passed" + (f", {npend} pending ({' '.join(sorted(pkgs))})" if npend else ''))
sys.exit(1 if fails or npend else 0)
PY
