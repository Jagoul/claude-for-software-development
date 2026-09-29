---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
  - "**/conftest.py"
---

# Testing conventions

These apply whenever Claude reads or writes test code.

- Use the fixtures in `tests/conftest.py`: `client` (a `TestClient` on a fresh app),
  `service`, and `make_tasks(n)`. Don't build apps or repositories inline.
- Structure each test as arrange / act / assert, separated by blank lines. One behaviour per
  test; use `pytest.mark.parametrize` for input variations.
- API tests assert the status code **and** the body. For errors, assert
  `response.json()["error"]["code"]`, not the message text.
- No `time.sleep`, no real clock. Inject time (a callable returning a timestamp) wherever
  behaviour depends on it.
- A test that reproduces an open bug is marked
  `@pytest.mark.xfail(strict=True, reason="TB-###: <symptom>")`.
- Tests marked `live` call real services and are excluded by default. Never make a default
  test depend on the network.
- Keep test data minimal and local to the test. Never share mutable state between tests.
