# ide-jump — working rules

**Last Updated: 2026-08-24 09:45**

## Ask before writing anything public under Troy's name

**Never run `gh pr review`, `gh pr comment`, `gh issue create` or anything else
that posts text to GitHub without showing Troy the draft first and waiting for
his go-ahead.** Approval to merge is not approval to comment.

Keep those drafts short — a few sentences. Evidence belongs in the commit
message or `.claude/handoffs/`, not in a comment on someone else's PR. If detail
genuinely has to be public, link the commit instead of transcribing it.

## The working tree is the live plugin

This directory is what `herdr plugin link` points at, so **whatever is checked
out here is what Troy's `prefix+alt+c` and `ctrl+shift+w` run.** Never check out
a PR, a branch or an experiment here. Use a worktree:

```bash
git worktree add ../ide-jump-<topic> <branch>
```

Test there, and only merge to `main` once it is verified. `herdr plugin list`
shows which directory is linked.
