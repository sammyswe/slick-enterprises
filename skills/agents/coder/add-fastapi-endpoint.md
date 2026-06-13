# Coder: add a FastAPI endpoint with tests

- Scope: agent (coder)
- Risk: low
- Status: approved

## Trigger
When a task needs a new gateway endpoint.

## Steps
1. Add a Pydantic schema in `packages/shared/slick_shared/schemas.py` (I/O decoupled
   from ORM models).
2. Add the route in the right router under `apps/gateway/gateway/routers/`.
3. Use `Depends(get_session)` for DB access; return schema models.
4. Add a test under `apps/gateway/tests/`.
5. Update `docs/02-architecture.md` if the API surface changed.

## Verify
```bash
make test
curl http://localhost:8000/docs   # new endpoint appears
```

## Anti-patterns
- Returning ORM objects directly; skipping tests; forgetting docs.
