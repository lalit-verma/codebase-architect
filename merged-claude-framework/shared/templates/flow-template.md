# Template: `agent-docs/flows/{name}.md`

```markdown
# {Flow Name}

## Why This Flow Matters

{1 short paragraph: what architectural question this flow answers.}

## Trigger

- Initiator: {user/system/job/event}
- Entrypoint: `{file:line}`

## Preconditions

- {condition}
- {condition}

## Sequence

1. `{file:line}` receives or initiates {input/event}
2. `{file:line}` transforms, validates, or routes
3. `{file:line}` coordinates downstream work
4. `{file:line}` returns/emits/persists outcome

## Side Effects and State Changes

- {store/cache/event/output}

## Failure Handling

- {error source and propagation}
- {retry/fallback behavior}

## Trade-off Notes

- `Confirmed:` {directly evidenced property}
- `Inference:` {likely rationale}
- `UNCERTAIN:` {what cannot be confirmed statically}
```
