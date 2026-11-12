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

## Credits

Ideas from these projects shaped agentHub. Each was rewritten in this package's own words: no text, code or assets were copied, so none of their licences apply to this package.

- https://github.com/addyosmani/agent-skills: performance, observability and expand/contract migration checklists
- https://github.com/leonxlnx/taste-skill: guidance on visual and copy tells, used only when there is no design source
- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill: UI checklist rows and the python launcher fallback order
- https://github.com/dietrichgebert/ponytail: the reuse-first, lean-code ladder
- https://github.com/anthropics/skills: the skill format and one marketplace listing several plugins
- https://github.com/multica-ai/andrej-karpathy-skills: the four working principles behind the coding standards
- https://github.com/mattpocock/skills: writing rules for agents, and git safety
- https://github.com/obra/superpowers: plugin build with session hooks, the writing-skills method, and stopping after repeated failed fixes
- https://github.com/shanraisshan/claude-code-best-practice: size limits for rules and skill descriptions, and Python hooks with a platform switch
- https://github.com/mksglu/context-mode: the large-read guard and the post-compaction resume lines (Elastic License 2.0; ideas only, no code or text copied)
