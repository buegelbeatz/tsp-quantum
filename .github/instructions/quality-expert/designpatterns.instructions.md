---
name: "Quality-expert / Designpatternss"
description: "Python Design Patterns Instructions (with Examples + Selection Guide)"
layer: digital-generic-team
---
# Python Design Patterns Instructions (with Examples + Selection Guide)


Use these patterns when they make the design clearer, more testable, or more maintainable.
Prefer simplicity first; do not over-engineer.

All examples assume:
- Python 3.11+
- Type hints on public APIs
- Small, focused modules and functions

---

# 0. General Design Rules

- Prefer composition over inheritance.
- Prefer dependency injection over global state.
- Avoid premature abstraction.
- Choose the smallest pattern that solves the problem.
- If a pattern increases complexity without clear benefit — do not use it.

---

# CREATIONAL PATTERNS

## Factory

Use when object creation varies by configuration or environment.

```python
from typing import Protocol


class Storage(Protocol):
    def save(self, data: str) -> None: ...


class FileStorage:
    def save(self, data: str) -> None:
        pass


class MemoryStorage:
    def save(self, data: str) -> None:
        pass


def create_storage(kind: str) -> Storage:
    if kind == "file":
        return FileStorage()
    if kind == "memory":
        return MemoryStorage()
    raise ValueError(f"Unknown storage: {kind}")
```

---

## Builder

Use when constructing complex objects step-by-step.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    debug: bool


class ConfigBuilder:
    def __init__(self) -> None:
        self._host = "localhost"
        self._port = 8080
        self._debug = False

    def host(self, host: str) -> "ConfigBuilder":
        self._host = host
        return self

    def debug(self, value: bool) -> "ConfigBuilder":
        self._debug = value
        return self

    def build(self) -> Config:
        return Config(self._host, self._port, self._debug)
```

---

# STRUCTURAL PATTERNS

## Adapter

Wrap incompatible interfaces.

```python
class LegacyLogger:
    def write(self, msg: str) -> None:
        pass


class LoggerAdapter:
    def __init__(self, legacy: LegacyLogger) -> None:
        self._legacy = legacy

    def log(self, message: str) -> None:
        self._legacy.write(message)
```

---

## Facade

Simplify complex subsystems.

```python
class Database:
    def connect(self) -> None: ...
    def query(self) -> None: ...


class Cache:
    def get(self) -> None: ...


class AppFacade:
    def __init__(self, db: Database, cache: Cache) -> None:
        self._db = db
        self._cache = cache

    def run(self) -> None:
        self._db.connect()
        self._cache.get()
```

---

## Decorator (Composition-based)

Add behavior without modifying the original class.

```python
class Service:
    def execute(self) -> None:
        pass


class LoggingDecorator:
    def __init__(self, inner: Service) -> None:
        self._inner = inner

    def execute(self) -> None:
        print("Before")
        self._inner.execute()
        print("After")
```

---

# BEHAVIORAL PATTERNS

## Strategy

Swap algorithms dynamically.

```python
from typing import Protocol


class SortStrategy(Protocol):
    def sort(self, data: list[int]) -> list[int]: ...


class Ascending:
    def sort(self, data: list[int]) -> list[int]:
        return sorted(data)


class Descending:
    def sort(self, data: list[int]) -> list[int]:
        return sorted(data, reverse=True)


class Sorter:
    def __init__(self, strategy: SortStrategy) -> None:
        self._strategy = strategy

    def execute(self, data: list[int]) -> list[int]:
        return self._strategy.sort(data)
```

---

## Observer

Event-driven updates.

```python
from typing import Callable


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[[str], None]]] = {}

    def subscribe(self, event: str, handler: Callable[[str], None]) -> None:
        self._subs.setdefault(event, []).append(handler)

    def publish(self, event: str, payload: str) -> None:
        for handler in self._subs.get(event, []):
            handler(payload)
```

---

## Command

Encapsulate actions as objects.

```python
from typing import Protocol


class Command(Protocol):
    def execute(self) -> None: ...


class PrintCommand:
    def __init__(self, message: str) -> None:
        self._message = message

    def execute(self) -> None:
        print(self._message)
```

---

# ARCHITECTURAL BOUNDARY PATTERNS

## Repository

Isolate persistence from business logic.

```python
from typing import Protocol


class UserRepo(Protocol):
    def get(self, user_id: str) -> str | None: ...


class InMemoryUserRepo:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, user_id: str) -> str | None:
        return self._data.get(user_id)
```

---

## Dependency Injection (Preferred)

Avoid global state.

```python
class Service:
    def __init__(self, repo: UserRepo) -> None:
        self._repo = repo

    def run(self, user_id: str) -> str | None:
        return self._repo.get(user_id)
```

---

# PATTERN SELECTION CHEATSHEET

## When to Use Which Pattern

| Problem | Use Pattern | Why |
|----------|------------|-----|
| Object creation depends on config | Factory | Centralizes instantiation |
| Complex object construction | Builder | Clear step-by-step creation |
| Swappable algorithm | Strategy | Runtime flexibility |
| Wrapping external library | Adapter | Interface compatibility |
| Too many subsystem calls | Facade | Simplified interface |
| Add logging/caching/retry | Decorator | Extend behavior safely |
| Multiple event listeners | Observer | Loose coupling |
| Encapsulate actions for queue/undo | Command | Action abstraction |
| Separate DB logic | Repository | Testable architecture |
| Avoid globals | Dependency Injection | Clean architecture |

---

## Anti-Pattern Warnings

- ❌ Using Singleton instead of dependency injection.
- ❌ Deep inheritance hierarchies.
- ❌ Factory for only one implementation.
- ❌ Overusing patterns in small scripts.
- ❌ Global mutable state.

---

# Final Guidance

- Start simple.
- Add patterns only when complexity requires them.
- Optimize for readability and testability.
- Prefer composition over inheritance.
- Prefer explicit over implicit.
- Always consider if a pattern adds value before implementing it.
