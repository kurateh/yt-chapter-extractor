# Textual Thread Workers Inside Screen Subclasses

**Extracted:** 2026-02-10
**Context:** Using `@work(thread=True)` inside a Textual `Screen` to run blocking I/O

## Problem 1: `call_from_thread` AttributeError

When using a thread worker (`@work(thread=True)`) inside a `Screen` subclass,
calling `self.call_from_thread()` raises:

```
AttributeError: 'MyScreen' object has no attribute 'call_from_thread'
```

`call_from_thread` is a method on `App`, not on `Screen` or `Widget`.

## Solution

Use `self.app.call_from_thread()` instead of `self.call_from_thread()`:

```python
class MyScreen(Screen):
    @work(thread=True)
    def do_work(self) -> None:
        result = blocking_operation()
        # WRONG: self.call_from_thread(self.update_ui, result)
        self.app.call_from_thread(self.update_ui, result)  # CORRECT
```

## Problem 2: Screen exit in push_screen_wait flow

When a screen is pushed via `push_screen_wait()`, calling `self.app.exit()` directly
from that screen leaves the awaiting coroutine dangling, potentially causing errors.

## Solution

Dismiss with a sentinel value (`None`) and let the caller handle exit:

```python
class MyScreen(Screen[MyResult | None]):
    def action_quit(self) -> None:
        self.dismiss(None)  # NOT self.app.exit()

# In the caller:
result = await self.push_screen_wait(MyScreen())
if result is None:
    self.exit()
    return
```

## When to Use

- Any time you write `@work(thread=True)` inside a Textual `Screen`
- Any time a screen needs to signal "cancel/quit" in a `push_screen_wait` flow
