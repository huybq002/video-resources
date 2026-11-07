# Morning reports

One file per night: `reports/YYYY-MM-DD.md`. The night job writes it at the **start** of its improvement
phase and appends after every finished item, so it is readable even when a usage limit ends the run
early. Read it first thing in the morning.

Improvement work on the pipeline never lands on `main` by itself. It goes to a branch
`improve/YYYY-MM-DD`, and the report starts with either the pull request or the compare link. You
read the diff, then merge or close it.

## Template

```markdown
# YYYY-MM-DD

**Pull request / branch:** <PR url, or https://github.com/huybq002/video-resources/compare/main...improve/YYYY-MM-DD?expand=1>
**Run:** <workflow run url> · started <time> · stopped <time> (<why: finished / time / usage limit>)

## Tonight's video
- <id> · <topic> · <keyword> · Release: <url>
- verify_bundle: bundle ok / video ok · policy_check: ok

## What the research found
- <3-6 bullets, each with a number or a title as evidence>

## Improvements (each is one commit on improve/YYYY-MM-DD)
### 1. <what changed, one line>
- why:
- evidence (before → after):
- files:
- commit:

## Tried and reverted
- <what, and why it did not hold up>

## Could not verify
- <anything you did not see working with your own eyes, said plainly>

## Decisions for the owner
- <only what the owner has to choose>

## Next steps suggested
- <1-3 items>
```
