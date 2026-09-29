---
paths:
  - "src/taskboard/models.py"
  - "src/taskboard/services/**/*.py"
  - "src/taskboard/storage/**/*.py"
---

# Domain models and services

These apply to the models, the service layer, and storage.

- Pydantic v2 only in new or touched code: `field_validator`, `model_validator`,
  `model_config = ConfigDict(...)`, `.model_dump()`, `.model_copy(update=...)`,
  `.model_validate()`, `Field(max_length=...)` for lists.
- A migrated validator must keep its behaviour: `@validator("tags", each_item=True)` becomes a
  `field_validator` that maps over the list.
- Status changes go through `ALLOWED_TRANSITIONS` in `services/tasks.py`. Never set `status`
  directly from a route.
- Services raise `TaskNotFound` or `InvalidTransition`, never `HTTPException`.
- Timestamps are timezone-aware UTC: `datetime.now(UTC)`. Never `datetime.utcnow()`.
- The repository is the only code that touches storage. It returns models, never dicts.
