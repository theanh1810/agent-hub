# Third-party notices

## PyYAML

- Package: PyYAML 6.0.3, pure-Python package only (`lib/yaml/`), no `_yaml` C extension
- Vendored at: `plugins/agent-hub/lib/yaml/`
- Also vendored at: `plugins/agent-hub-local-services/lib/yaml/` (same files, unmodified)
- Source: https://pypi.org/project/PyYAML/6.0.3/ (sdist `pyyaml-6.0.3.tar.gz`)
- sdist sha256: `d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f`
- Modifications: unmodified (the files of the sdist's `lib/yaml/`, copied byte for byte)
- Licence: MIT

```
Copyright (c) 2017-2021 Ingy döt Net  (scrub-allow: licensor name)
Copyright (c) 2006-2016 Kirill Simonov

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


## Text carried from other projects

agent-hub v2 carries text from the projects below, word for word, with attribution. Each carried passage sits between `<!-- vendored:begin … -->` and `<!-- vendored:end … -->` markers that name the source, the pinned commit and the upstream lines, and a copy of the upstream file at that pin is kept under `tools/upstream/` with its sha256 in `tools/upstream/manifest.yaml`. The check `quoted_passages_attributed` (`tools/attribution_check.py`) fails when a marked block differs from its pinned lines by one byte, when its origin has no entry here, or when three or more consecutive lines of a pinned file appear outside markers. Passages that the repository quoted before the markers existed are credited through `quoted_in` in the manifest.

Licence texts are the upstream files, kept at `tools/upstream/<owner>-<repo>/LICENSE`; this file quotes the copyright line of each and states the licence by its SPDX identifier. Each entry is an engineering reading of the licence, not legal advice. Pins marked "tag" name a release whose commit was not dereferenced.

### obra/superpowers

- Repository: https://github.com/obra/superpowers, release v7.0.2 (commit 22f0b463e7a5e579904dd6211a520321035526f7)
- Licence: MIT. `Copyright (c) 2025 Jesse Vincent`
- Carried: the whole files `test-driven-development`, `systematic-debugging`, `verification-before-completion` and `receiving-code-review` (SKILL.md); `final-review.md` lines 35-42 (the "Rulings I made" list); the `Ruling:` line format quoted in `plugins/agent-hub/rules/core.md` (credited through `quoted_in`; `sdd.md` is not in the v7.0.2 tree, so no copy of it exists). Sibling text files that the carried skills link to travel with them under the same markers (pinned: `writing-plans`, `condition-based-waiting`, `defense-in-depth`, `root-cause-tracing`, `writing-good-tests`).
- Pinned reference copies, not yet carried as blocks: `fix-loop.md`, `implementer-prompt.md`, `task-reviewer-prompt.md`, `code-reviewer.md`.

### mattpocock/skills

- Repository: https://github.com/mattpocock/skills, all copies pinned at commit 5863806dd4e15c63174bee4e7515a4256792ecfa (release v1.3.2 is commit d1478fcb; the carried paths are byte-identical at both)
- Licence: MIT. `Copyright (c) 2026 Matt Pocock`
- Carried: `writing-for-agents` and `codebase-design` (SKILL.md, whole files, with their linked siblings); the process texts grilling, to-questionnaire, domain-modeling with GLOSSARY-FORMAT, prototype with its two siblings, improve-codebase-architecture, teach with its four format files, research, retro, handoff and wait-what (copies held).

### cloudflare/security-audit-skill

- Repository: https://github.com/cloudflare/security-audit-skill (commit c1c8a8c1471069fb0e188eeaff69b8e8db6564a8)
- Licence: MIT. `Copyright (c) 2025-2026 Cloudflare, Inc.`
- Carried: the structure and topic order of the security-audit rule and its web-protocol and auth domain file follow `skills/security-audit/SKILL.md` and `WEB-PROTOCOL-AND-AUTH.md` in near-paraphrase (scan H10 found at most one identical line). Pinned copies of both files are held so the check can see any later verbatim copy.

### addyosmani/agent-skills

- Repository: https://github.com/addyosmani/agent-skills (commit 39b723ceebf81474d0557c1fecd01eddab585563)
- Licence: MIT. `Copyright (c) 2025 Addy Osmani`
- Carried: blocks N1-N8 and N10 of the text merges: `debugging-and-error-recovery` lines 21-34 and 272-280; `test-driven-development` lines 144-187, 211-233 and 303-313; `code-review-and-quality` lines 88-101 and 273-282; `doubt-driven-development` lines 183-193; `planning-and-task-breakdown` lines 57-78 (block N10 only if scan H22c finds no vertical-slicing text in superpowers).

### DietrichGebert/ponytail

- Repository: https://github.com/DietrichGebert/ponytail (commit 96608e078b2d5ea607c5c3b8b5a54d1c1fba6846)
- Licence: MIT. `Copyright (c) 2026 DietrichGebert`
- Carried: blocks N11-N13: `skills/ponytail/SKILL.md` lines 23-44, `skills/ponytail-review/SKILL.md` lines 30-67, `skills/ponytail-debt/SKILL.md` lines 13-25.

### multica-ai/andrej-karpathy-skills

- Repository: https://github.com/multica-ai/andrej-karpathy-skills (commit 2c606141936f1eeef17fa3043a72095b4765b9c2)
- Licence: MIT per the SKILL.md frontmatter and the README; the repository has no LICENSE file and no copyright line. That statement is the only basis for carrying its text.
- Carried: the four working principles behind the coding standards, quoted from the README in `refs/code-standards.md` and the core rules (credited through `quoted_in`).

### anthropics/claude-code (code-review plugin)

- Repository: https://github.com/anthropics/claude-code, plugin `code-review`, file `commands/code-review.md`
- Licence: proprietary, `© Anthropic PBC. All rights reserved.` (LICENSE.md at commit eba1240d09fd468b984a2a317c77cb48e1e51d2f; earlier "Apache-2.0" here was wrong)
- Carried: nothing. The file is not vendored (`pointer_only` in the manifest); the reviewer's finding bar is written in this package's own words.

## Store: skills shipped as text-only files by path

The store ships the next five origins as text, selected by a signal in the user's project and never executed.

### Jeffallan/claude-skills

- Pin (commit 078a25cc5bfd8011459be7b91d004e900c1d02d3): MIT. The LICENSE reads `Copyright (c) 2025` with no holder named; the author is given in the skill frontmatter as github.com/Jeffallan. Carried: typescript-pro, laravel-specialist, vue-expert, wordpress-pro, websocket-engineer and architecture-designer (SKILL.md and references/, copies held).

### antfu/skills

- Pin (commit 4a6bb39e7b45e26402eb215393c51ccf5df1ca4c): MIT. `Copyright (c) 2025-PRESENT Anthony Fu <https://github.com/antfu>`. Carried: the pnpm, vite and vitest skills (SKILL.md copies held); their `references/` are not shipped (the licences of the upstream docs they quote are unchecked); `GENERATION.md` is not shipped.

### ironyjk/strategy-frameworks

- Pin (commit 146aa1c4dfe0eccc51a77c25a32f3e1958773f6c): MIT. `Copyright (c) 2026 ironyjk`. Carried: first-principles, ooda, systems-thinking (SKILL.md and references/, copies held).

### mattnowdev/thinking-partner

- Pin (commit ce95b6280660652d67bfc3fc36f8d7f941538f7f): MIT. `Copyright (c) 2026 mattnowdev`. Carried: thinking-partner (SKILL.md and references/, copies held).

### revfactory/harness

- Pin (commit 92d9f1b29e7af81acebf51a9fcd1832e739a1414): Apache-2.0. `Copyright 2025 robin`. Carried: harness and harness-evolve (SKILL.md copies held; `references/` later). The upstream text is Korean; the store file adds an English owned head and a guard line. Change statement (Apache-2.0 section 4(b)): the carried files were modified by adding that head and guard to the beginning of each file; the upstream text that follows is unchanged. The Apache-2.0 licence text and this notice travel with the files.


## Carried in the store (three origins)

The SKILL.md text of four skills from these origins sits in the vetted store (`plugins/agent-hub/store/`), word for word under markers, with copies held under `tools/upstream/`. Their `references/` are not shipped.

### vuejs-ai/skills

- Pin (commit 198f0cd8f7f9c0a3d9b566ccc16de6677519ee78): MIT. `Copyright (c) 2025 hyf0, SerKo`. Carried: vue-best-practices and vue-testing-best-practices (SKILL.md text only, copies held).

### ant-design/antd-skill

- Pin (commit e65d2d3da9a2a129885131f5aeffe2c9037f83cb): MIT. `Copyright (c) 2015-present Ant UED`. Carried: `skills/ant-design` as the store entry ant-design (SKILL.md text only, copy held).

### zhaoxuya520/reverse-skill

- Pin (commit b972ad0e90f26d8f044828f004da22a4a585da12): MIT. `Copyright (c) 2026 zhaoxuya520`. Carried: apk-reverse (SKILL.md text only, copy held).

## Pinned, not carried

No text of this one is in the package.

### Leonxlnx/taste-skill

- Pin (commit f6b76575f949707b4e3c37cd86cb44b0b98643e8): MIT. `Copyright (c) 2026 Leonxlnx`. Two checks of pattern only; no text of it is carried.


## Not carried

- WordPress/agent-skills (GPL-2.0-or-later) and project-vault: no text is carried. The store only points to the WordPress skills per project.

## Ideas only

No text, code or assets of the projects below are carried; their licences do not apply to this package. Each idea was rewritten in this package's own words.

- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill: UI checklist rows and the python launcher fallback order
- https://github.com/anthropics/skills: the skill format and one marketplace listing several plugins
- https://github.com/shanraisshan/claude-code-best-practice: size limits for rules and skill descriptions, and Python hooks with a platform switch (MIT, `Copyright (c) 2025-2026 Shayan Rais`)
- https://github.com/mksglu/context-mode: the large-read guard and the post-compaction resume lines (Elastic License 2.0; ideas only, no code or text copied)
- graphify: its rules need its own CLI; nothing carried
