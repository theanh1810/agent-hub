# Design pitfalls: the lines a brief carries
<Owner: agents/brainstorm.md § Workflow, step 5>
<Read when: brainstorm synthesizes a change whose evidence names a file path, a parser, user input or UI state>

---

Copy into the implement brief (L3: the task's `Done when:`) every line below whose trigger the change's evidence shows, word for word; a line with no trigger in this change stays here. Each copied line is a test owed: implement writes its failing case before the code.

## A path that arrives from outside the code (argument, config value, upload, archive entry, environment)

- Symlink: decide follow or refuse, and test a link that points outside the allowed root.
- Canonicalise, then compare: resolve the real path first and check containment on the resolved value, with a `..` case and a sibling-prefix case (`/data/app` against `/data/app2`).
- Special files: refuse anything that is not a regular file before opening it (FIFO, device, socket, directory); opening a FIFO blocks until a writer appears.
- Temp files: create with an exclusive, unpredictable name at mode 0600 in the destination's directory, write, then rename; remove it on failure.
- Check, then use: act on the handle that was checked (open, then `fstat`), since a path checked and reopened can be swapped between the two.

## Input boundaries

- Text slicing: cut on character boundaries (grapheme clusters where a user sees the result), with a multibyte character placed on the cut.
- Numbers: state the range, then test below, at and above each end, plus zero, a negative, a non-number and an overflow.
- Size: cap what is read before reading it (bytes, lines, items, nesting depth) and test one unit over the cap.
- Encoding: empty input, invalid UTF-8 and a NUL byte each have a stated result.

## UI state

- Loading: data from the previous selection is never shown as current, and a slower earlier response does not overwrite a newer one.
- Shortcuts: a key binding fires only inside its scope, and stays silent while a text field or a dialog has focus.
- Focus: opening moves focus in and closing returns it to the opener; a state with every control disabled still has a focus target.
