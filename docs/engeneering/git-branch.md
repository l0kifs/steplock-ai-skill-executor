# Git Branch Rules

---

## Description

Concise rules for naming and managing git branches: consistent naming conventions, branch types, and lifecycle practices.

---

## Branch Naming Format

### Structure
```
<type>/<short-description>
```

### Rules
1. Use lowercase letters only
2. Use hyphens (`-`) to separate words, not underscores or spaces
3. Keep names short and descriptive (≤ 50 characters total)
4. Include issue/ticket number when applicable: `<type>/<issue-id>-<short-description>`

### Examples
- `feat/user-authentication`
- `fix/42-login-timeout`
- `chore/update-dependencies`

---

## Branch Types

| Type | Purpose | Example |
|------|---------|---------|
| `feat/` | New feature | `feat/payment-integration` |
| `fix/` | Bug fix | `fix/null-pointer-crash` |
| `refactor/` | Code restructuring | `refactor/auth-module` |
| `chore/` | Maintenance, dependencies | `chore/upgrade-node` |
| `docs/` | Documentation only | `docs/api-reference` |
| `test/` | Add or update tests | `test/cart-unit-tests` |
| `ci/` | CI/CD changes | `ci/add-lint-step` |
| `hotfix/` | Urgent production fix | `hotfix/payment-failure` |
| `release/` | Release preparation | `release/1.2.0` |

---

## Lifecycle Rules

- Branch from the correct base: `feat/*` and `fix/*` branch from `main` (or `develop` if used)
- `hotfix/*` branches from the production branch (usually `main`)
- Delete branches after merging — do not keep stale branches
- One branch = one purpose; do not mix unrelated changes
- Keep branches short-lived; merge or rebase frequently to avoid drift

---

## Anti-Patterns ❌

- `my-branch` — no type prefix, not descriptive
- `fix_login` — underscores instead of hyphens
- `Feature/AddUser` — uppercase letters
- `johns-work` — named after a person, not a purpose
- `temp`, `test123`, `wip` — meaningless names
- Long-running branches accumulating many unrelated commits

## Best Patterns ✅

- `feat/23-user-profile-page`
- `fix/cart-duplicate-items`
- `hotfix/security-patch-xss`
- `chore/remove-deprecated-api`
