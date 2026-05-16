# DDD Architecture Rules

> **Version:** 1.3.0  
> **Purpose:** Python DDD reference for AI agent use. HTTP APIs, CLI tools, workers, libraries. Microservice-extraction ready.

---

## Layer Map

```
entry_points/ → application/ → domain/
                    ↑
             infrastructure/
```

Domain depends on nothing. Application orchestrates. Infrastructure implements. Each `<domain>` folder is a self-contained unit — extractable to a microservice with minimal effort.

---

## Project Structure

```
src/<package_name>/
├── config/
│   ├── settings.py              # Env vars, constants ONLY
│   └── logging.py               # Logging config ONLY
│
├── domains/<domain>/            # Pure business logic — no I/O, no orchestration
│   ├── models.py                # Entities + value objects (business rules)
│   ├── events.py                # Domain events (past-tense, frozen dataclasses)
│   └── exceptions.py            # Domain exceptions
│
├── application/<domain>/        # Orchestration — defines service boundary
│   ├── services.py              # Use cases (call domain + ports, no I/O directly)
│   ├── ports.py                 # All interfaces: IRepository, INotifier, IClient, etc.
│   ├── commands.py              # Input structs for write operations (optional)
│   └── queries.py               # Input structs for read operations (optional)
│
├── infrastructure/<domain>/     # Technical impl — implements application ports
│   ├── repositories.py          # Implements IRepository from application/ports.py
│   ├── database.py              # Engine, session, SQLAlchemy models
│   ├── clients.py               # External API adapters
│   ├── messaging.py             # Event bus, queue adapters
│   └── storage.py               # File system, cloud storage
│
└── entry_points/
    ├── main.py                  # Wiring root only — no logic
    ├── api/                     # HTTP endpoints
    ├── cli/                     # CLI commands
    ├── web/                     # Pages, static/, templates/
    └── workers/                 # Background workers
```

Include only layers you need: CLI tool → `cli/` + `main.py`; library → no `entry_points/`.

---

## Strict Rules

| Rule | Detail |
|------|--------|
| Domain purity | `domains/` imports: stdlib + Pydantic + `logging` only. No orchestration. |
| Application scope | `application/` calls domain + ports only. No direct I/O. |
| I/O boundary | DB, HTTP clients, queues, filesystem → `infrastructure/` only |
| Port contract | All interfaces defined in `application/<domain>/ports.py`; implemented in `infrastructure/<domain>/` |
| Port scope | One concern per interface; never mix unrelated methods in one port |
| Event flow | Domain fires event → application service or messaging adapter consumes it |
| Config boundary | `config/` has no DB engines, API clients, or technical impl of any kind |
| Entry point scope | I/O + input validation + service calls + side effects only |
| Bounded context | Never import entities across domain boundaries; use IDs or events |
| Aggregate boundary | Never reach into another entity cluster directly |
| Wiring only | `main.py` instantiates and injects — no logic |
| `__init__.py` | Every package dir requires one; docstrings only |
| File size | Max 300 lines per file |

---

## Patterns

**Entity (`domains/<domain>/models.py`)** — enforces rules, returns domain events:
```python
class Task(BaseModel):
    id: UUID; status: str; description: str

    def complete(self) -> TaskCompleted:
        if self.status != "ACTIVE": raise InvalidStatusError()
        self.status = "COMPLETED"
        return TaskCompleted(task_id=self.id)

    class Config: frozen = True
```

**Domain Event (`domains/<domain>/events.py`)** — past tense, frozen, plain data:
```python
@dataclass(frozen=True)
class TaskCompleted:
    task_id: UUID
    completed_at: datetime = field(default_factory=datetime.utcnow)
```

**Ports (`application/<domain>/ports.py`)** — all interfaces in one place:
```python
class ITaskRepository(ABC):
    @abstractmethod
    def save(self, task: Task) -> None: ...
    @abstractmethod
    def find_by_id(self, task_id: UUID) -> Task | None: ...

class INotifier(ABC):
    @abstractmethod
    def notify(self, user_id: UUID, message: str) -> None: ...
```

**Use Case (`application/<domain>/services.py`)** — orchestrates, no I/O:
```python
class TaskService:
    def __init__(self, repo: ITaskRepository, notifier: INotifier):
        self._repo = repo
        self._notifier = notifier

    def complete_task(self, task_id: UUID) -> TaskCompleted:
        task = self._repo.find_by_id(task_id)
        if not task: raise TaskNotFoundError(task_id)
        event = task.complete()
        self._repo.save(task)
        self._notifier.notify(task.owner_id, "Task completed")
        return event
```

**Infrastructure (`infrastructure/<domain>/repositories.py`)** — implements ports:
```python
class PostgresTaskRepository(ITaskRepository):
    def __init__(self, session): self._session = session
    def save(self, task: Task) -> None: ...       # SQLAlchemy here
    def find_by_id(self, task_id: UUID) -> Task | None: ...
```

**Wiring (`main.py`)**:
```python
def get_task_service() -> TaskService:
    return TaskService(
        repo=PostgresTaskRepository(get_db_session()),
        notifier=SendGridNotifier(get_settings().sendgrid_key),
    )
```

**Wiring order:** infrastructure → domain → application → entry_points. Never inject upward.

---

## Import Rules

| Layer | May Import |
|-------|-----------|
| config | stdlib only |
| domain | stdlib + Pydantic + `logging` |
| application | domain |
| infrastructure | domain + application (ports only) |
| entry_points | application + infrastructure |

---

## Microservice Extraction

Each `<domain>` folder triplet (`domains/`, `application/`, `infrastructure/`) is the extraction unit.

To extract domain X as a microservice:
1. Copy `domains/X/` → new service unchanged
2. Copy `application/X/` → new service unchanged
3. Rewrite `infrastructure/X/` → adapt to new service's DB/messaging
4. Add new `entry_points/` shell

Steps 1–2 require zero changes. Domain and application layers are fully portable by design.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Orchestration in domain (calling repos, firing side effects) | Move to `application/<domain>/services.py` |
| Business logic in application service | Move rule to entity method |
| Business logic in entry point | Move to entity or application service |
| SQLAlchemy/FastAPI import in domain or application | Infrastructure only |
| Anemic entity (data only, no methods) | Add business rule methods to entity |
| Ports defined in domain/ | Ports belong in `application/<domain>/ports.py` |
| Entity imported across domains | Reference by ID; communicate via domain events |
| Technical impl in config/ | Move to `infrastructure/` |

---

## Bounded Context

Each domain owns its language. `User` in `orders` ≠ `User` in `auth`. Cross-domain sharing: IDs only, or domain events, or an anti-corruption layer in `infrastructure/<domain>/`.

---

## When to Add Complexity

Start with: `models.py` + `services.py` + concrete repository (skip ports until needed).

| Add | When |
|-----|------|
| Port interfaces | Need mock for tests, multiple backends, or microservice extraction |
| `commands.py` / `queries.py` | CQRS needed or input structs are getting complex |
| Domain events | Side effects must decouple from business logic |
| Messaging adapter | Async event publishing |
| Anti-corruption layer | Two domains share a concept with different semantics |

YAGNI — add only when actually needed.

---

## Quick Checklist

- [ ] `domains/` has no I/O, no orchestration, no infrastructure imports
- [ ] `application/` has no direct I/O — calls ports only
- [ ] All interfaces in `application/<domain>/ports.py`; impls in `infrastructure/<domain>/`
- [ ] Domain events: past-tense, frozen dataclasses
- [ ] No entity shared across domain boundaries
- [ ] `config/` has no technical implementation
- [ ] `main.py` wires only — no logic
- [ ] Max 300 lines per file

---

> **Version**: 1.3.0 | **Updated**: 2026-05-16 | **Status**: Active  
> **Tags**: architecture, python, ddd, microservices
