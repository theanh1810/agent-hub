## Purpose
<!-- Only when this delta introduces a new UC id: one line per new id saying what that use case does. -->

## ADDED Requirements

### Requirement: UC-XXX/AC-N - <observable behaviour>
The system SHALL <the approved behaviour>.

#### Scenario: <name>
- **WHEN** <the approved trigger occurs>
- **THEN** <the approved outcome is observable>

## MODIFIED Requirements
<!-- Copy the whole existing requirement: its exact heading and every scenario, then change it. A completed delta holds no placeholder. -->

### Requirement: UC-XXX/AC-N - <the exact existing name>
The system SHALL <the new behaviour>.

#### Scenario: <name>
- **WHEN** <the trigger>
- **THEN** <the outcome>

## REMOVED Requirements

### Requirement: UC-XXX/AC-N - <the exact existing name>
**Reason**: <why it stops applying, with the user's words>
**Migration**: <what replaces it, or 'none'>

## RENAMED Requirements
- FROM: `### Requirement: UC-XXX/AC-N - <old name>`
- TO: `### Requirement: UC-XXX/AC-N - <new name>`

## Flow Changes
<!-- One entry per step of the UC main flow (`3`) or per variant (`2a`), keyed by that number. A step inserted between 2 and 3 takes `2.1`; existing numbers and variant keys do not move (SDD.md §3.1 step 1). -->
- **ADDED 4a. <variant name>:** <what the system does differently>
- **MODIFIED 3:** <the whole new text> - **Before:** <the old text, verbatim> - **Why:** <the user's words, or the question id>
- **RETIRED 2a** - no longer applies because <reason, with the user's words>

## Exception Changes
<!-- One entry per exception, keyed by its E-n code; a new code is the next unused number in the UC. -->
- **ADDED E3. <situation>:** <how the system handles it and what the user sees>
- **MODIFIED E1:** <the whole new text> - **Before:** <the old text, verbatim> - **Why:** <the user's words, or the question id>
- **RETIRED E2** - no longer applies because <reason, with the user's words>
