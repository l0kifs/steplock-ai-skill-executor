# GitHub Pull Request Rules

---

## Description

Concise rules for creating pull requests: clear titles, business-focused descriptions, small scopes, and review-ready practices.

---

## PR Title

### Rules
1. Use imperative mood (e.g., 'Add' not 'Adding', 'Fix' not 'Fixed')
2. Keep title ≤ 72 characters
3. Follow Conventional Commits format: `<type>(<scope>): <description>`
4. Be specific — describe what the PR does, not how

### Examples
- `feat(auth): add OAuth2 login support`
- `fix(cart): prevent duplicate items on rapid clicks`
- `docs(api): update authentication endpoint reference`

---

## PR Description

### Required Sections

1. **Business Value** — Why this change matters; what problem it solves for users or the business
2. **What Changed** — Brief summary of the technical changes made
3. **How to Test** — Steps to verify the changes work correctly

### Rules
- Always include the business value — explain the impact, not just the implementation
- Keep each section concise; use bullet points for lists
- Link to related issues or tickets: `Closes #123`

### Template
```
## Business Value
<!-- What value does this deliver? What problem does it solve? -->

## What Changed
<!-- Brief summary of technical changes -->

## How to Test
<!-- Steps to verify this works -->

Closes #<issue-number>
```

---

## Scope and Size

- One PR = one logical change; do not mix unrelated features or fixes
- Keep PRs small and focused — easier to review, easier to revert
- Split large changes into a sequence of smaller PRs when possible

---

## Readiness Checklist

Before opening a PR:
- [ ] Title follows naming convention
- [ ] Description includes business value
- [ ] All tests pass
- [ ] No unintended files included (build artifacts, secrets, debug code)
- [ ] PR is linked to the relevant issue or ticket

---

## Anti-Patterns ❌

- Opening a PR with no description
- PR description that only describes implementation with no business context
- Mixing unrelated changes in one PR
- `fix stuff`, `updates`, `WIP` — vague or incomplete titles
- PRs that are too large to review effectively

## Best Patterns ✅

- Clear title with type and scope
- Description that starts with business value
- Small, focused diffs
- All CI checks passing before requesting review
