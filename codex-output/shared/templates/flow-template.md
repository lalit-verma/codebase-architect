# Template: `docs/flows/<flow>.md`

```markdown
# {Flow Name}

## Why This Flow Matters

{1 short paragraph describing what architectural question this flow
answers.}

## Trigger

- initiator: {user/system/job/event/import}
- entrypoint: `{file:line}`

## Preconditions

- {condition}
- {condition}

## Sequence

1. `{file:line}` receives or initiates {input/event}
2. `{file:line}` transforms, validates, or routes it
3. `{file:line}` coordinates downstream work
4. `{file:line}` returns/emits/persists the outcome

## Side Effects And State Changes

- {store/cache/event/output}
- {store/cache/event/output}

## Failure Handling

- {error source and propagation}
- {retry/fallback/none}

## Trade-Off Notes

- `Confirmed:` {directly evidenced property}
- `Inference:` {likely rationale}
- `UNCERTAIN:` {what cannot be confirmed statically}
```
