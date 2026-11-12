# Release — pre-launch checks, gates, rollout, rollback

Load before a staging or production deploy, a CI/CD change, or a rollback plan.

Thresholds and timings here are **suggested starting values** from an external repo, not approved rules (user decision 45); a plan or `SERVER-INFO.md` may override them. The numbers themselves are read from group rollout of `templates/thresholds/thresholds.yaml` (`refs/thresholds.md`); this file names the rule, not the figure.

## Pre-launch checks

By six groups: code quality · security · performance · accessibility · infrastructure (env vars, migrations, DNS/SSL, health check) · documentation.
- No secret in code or history; dependency scan has no critical or high finding; CORS names specific origins, never a wildcard; rate limiting on login.
- No CI gate is skipped and no lint rule is switched off or test skipped to pass a gate; red means fix the code.

## CI/CD

- PR: lint → typecheck → unit → integration → preview deploy. Main merge: build → staging → smoke → production.
- Shift left: static checks before tests, tests before staging, staging before production.
- Small, frequent releases are safer than big ones.
- The gate also checks bundle size and dependency vulnerabilities; the integration job uses a throwaway database service with a health check and a password from the CI secret store.
- CI configuration is authorization code: state which event triggers it, whose code runs, which token or secret is present, and what it may release or change.
- Keep integrity across every hop: source → resolved input → build machine → artifact → test → signature → release. A checksum fetched from the same untrusted source as the artifact proves nothing.
- Beyond config files: a workload identity gets only the operations and resources it needs; a broad policy is a finding only when untrusted input can reach an action it must not.

## Strategies

- **Rolling** (default): gradual, zero downtime, needs backward compatibility.
- **Blue-green**: two environments, atomic switch, instant rollback, 2x infrastructure.
- **Canary**: a small share first; needs traffic splitting.

## Feature flags

Lifecycle: create → test → canary → 5% → 25% → 50% → 100% → remove the flag and dead code. Every flag has an owner, an expiry and a rollback trigger; clean up within 2 weeks of full rollout. Test both flag states in CI; never nest flags (combinations grow exponentially).

Suggested sequence: staging → production with flag off → internal on (watch 24 h) → canary 5% (24-48 h) → 25/50/100% → watch a week, then remove the flag. Each step can step back to the previous one.

## Git workflow

- One logical change per commit, message `<type>: <short description>` with a body that states why; formatting, refactor and feature changes are separate commits (addy git-workflow-and-versioning SKILL.md:48-146).
- Branches are short-lived and named `feature/`, `fix/`, `chore/` or `refactor/` plus a short description; delete after merge; prefer a feature flag over a long-lived branch.
- Version `MAJOR.MINOR.PATCH`: a break is major, an addition minor, a fix patch; when unsure whether a change breaks consumers, treat it as breaking (SKILL.md:274-312).
- The release is an annotated tag and the version is derived from it, never hand-edited in several files; the changelog (Added / Changed / Fixed / Deprecated / Removed / Security, newest first, phrased as user impact) is written in the same change that makes the difference.
- **A tag push is an approval step**: devops asks first, then pushes.

## Suggested advance / hold / roll-back thresholds

| Signal | Advance | Hold and investigate | Roll back |
|---|---|---|---|
| Error rate vs baseline | within 10% | 10-100% above | above 2x |
| P95 latency | within 20% | | above 50% |
| New client-side JS errors | | | above 0.1% of sessions |
| Business metric | | | down more than 5% |

Roll back at once on: errors above 2x, P95 up over 50%, a spike in user reports, a data-integrity problem, a security vulnerability found.

First hour after release: health returns 200; the error dashboard shows no new error type; latency and error rate against the previous baseline; the main path works.

## Rollback plan (written before the deploy)

- Trigger conditions, the steps (flag off, or deploy the previous version), how to verify, whom to tell.
- The database part: has the migration a tested down step; will data written by the new feature be kept or cleaned.
- Expected time per way: flag off under 1 min; redeploy previous version under 5 min; database rollback under 15 min (suggested).
- Platform commands: Kubernetes `kubectl rollout undo deployment/app` · Vercel `vercel rollback` · Docker `docker-compose up -d --no-deps --build web` (previous image) · EAS Update `eas update:rollback` · native mobile: revert to the previous `eas build` submission · App Store / Play: no direct rollback, reduce the phased release to 0%.
- A rollback never run on this host is a plan, not a guarantee.
