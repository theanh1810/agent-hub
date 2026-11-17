# Branch integration and worktrees

Load at the end of a plan, when integrating its branch, opening a PR or cleaning worktrees.

User decision 46: devops itself merges the branch, opens the PR and cleans the worktrees at the end of each plan. Implement keeps committing to the feature branch; devops otherwise stays on the feature branch and never commits to `main` or `develop` without the plan saying so. `hooks/git_guard.py` stands beside these rules (user decision 61).

1. **Green first.** Offer the integration choice (merge into the base branch locally / push and open a PR / keep as is) only after the full suite is green on the exact tree about to be integrated.
2. **Base branch.** Unsure of it → ask ("this branch split from X, correct?") before merging; a wrong base is very hard to undo.
3. **After a merge** run the tests on the merged result. Red → stop, keep the branch and worktree for investigation; never call it "probably flaky".
4. **PR.** Open and read merge requests through GitLab (`mcp__mcp_gitlab__*`). After push and PR keep the worktree: follow-up fixes happen there. Clean only worktrees devops created; finished agent worktrees are swept at closeout (`refs/artifact-layout.md` § 19.3).
5. **Worktree removal refused** because of uncommitted files: show the user the file list and offer three choices: commit to the branch, move into the main repo, delete permanently; never add `--force` on your own.
6. **Push rejected** means the remote changed: investigate, never force-push. Force-push only when the user names it explicitly.
