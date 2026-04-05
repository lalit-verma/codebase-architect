# Template: `agent-docs/flows/{flow-name}.md`

```markdown
# {Flow Name}

## Why This Flow Matters

{1 paragraph: what architectural question this flow answers.}

## Trigger

- Initiator: {user/system/job/event/import}
- Entrypoint: `{file:line}`

## Preconditions

- {condition}
- {condition}

## Sequence

1. `{file:line}` receives or initiates {input/event}
2. `{file:line}` transforms, validates, or routes it
3. `{file:line}` coordinates downstream work
4. `{file:line}` returns/emits/persists the outcome

## Side Effects and State Changes

- {store/cache/event/output}

## Failure Handling

- {error source and propagation}
- {retry/fallback/none}

## Trade-off Notes

- `Confirmed:` {directly evidenced property}
- `Inference:` {likely rationale}
- `UNCERTAIN:` {what cannot be confirmed statically}
- `NEEDS CLARIFICATION:` {what a human should verify}
```
