## Purpose
<!-- New capability only: at least 50 characters on what the capability is for. Omit for an existing capability. -->

<!-- Rules checked by `openspec validate --strict`: requirement text uses SHALL or MUST and stays under 500 characters; scenario headings have exactly four hashes; each scenario uses `- **WHEN**` and `- **THEN**` lines (GIVEN allowed), never prose. -->

## ADDED Requirements

### Requirement: <name>
The system SHALL <the approved behaviour>.

#### Scenario: <name>
- **WHEN** <the approved trigger occurs>
- **THEN** <the approved outcome is observable>

## MODIFIED Requirements
<!-- Copy the whole existing requirement: its exact heading and every scenario, then change it. A finished delta holds no placeholder. -->

### Requirement: <the exact existing name>
The system SHALL <the new behaviour>.

#### Scenario: <name>
- **WHEN** <the trigger>
- **THEN** <the outcome>

## REMOVED Requirements

### Requirement: <the exact existing name>
**Reason**: <why it stops applying, with the user's words>
**Migration**: <what replaces it, or 'none'>

## RENAMED Requirements
- FROM: `### Requirement: <old name>`
- TO: `### Requirement: <new name>`
