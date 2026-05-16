# Git Commit Rules

---

## Description

Concise rules for creating quality commits: single responsibility principle, commit messages following Conventional Commits specification, and staging practices.

---

## Commit Message Format

### Structure
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Length Requirements
- **Subject:** ≤ 50 characters
- **Body line:** ≤ 72 characters

### Formatting Rules
1. Use imperative mood (e.g., 'Add' not 'Adding', 'Fix' not 'Fixed')
2. Capitalize first word of description
3. No period at end of description
4. Focus on WHAT and WHY, not just HOW
5. Separate subject and body with blank line
6. Separate body and footer with blank line

---

## Single Responsibility Principle

**Principle:** One commit = one logical change

Each commit should address a single concern or solve one specific problem.

### Rules
- If changes serve different purposes, split into separate commits
- Unrelated fixes should be in different commits
- Use 'git add -p' for selective staging when needed
- One commit should be revertable without affecting other changes

### Examples

❌ **Wrong:**
```
fix(api): fix login bug, update docs, refactor utils
```

✅ **Correct:**
```
fix(api): resolve authentication timeout
docs(api): update login endpoint documentation
refactor(utils): simplify token validation logic
```

---

## Commit Types

### feat
- **Description:** New feature
- **SemVer:** MINOR
- **Example:** `feat(auth): add password reset functionality`

### fix
- **Description:** Bug fix
- **SemVer:** PATCH
- **Example:** `fix(api): handle null response in user endpoint`

### docs
- **Description:** Documentation changes
- **SemVer:** NONE
- **Example:** `docs(readme): update installation instructions`

### style
- **Description:** Code formatting (no logic changes)
- **SemVer:** NONE
- **Example:** `style: remove trailing whitespace`

### refactor
- **Description:** Code restructuring without behavior change
- **SemVer:** NONE
- **Example:** `refactor(utils): simplify date formatting logic`

### perf
- **Description:** Performance improvements
- **SemVer:** PATCH
- **Example:** `perf(cache): implement redis caching for queries`

### test
- **Description:** Add or update tests
- **SemVer:** NONE
- **Example:** `test(auth): add unit tests for login validation`

### chore
- **Description:** Maintenance, dependencies, build config
- **SemVer:** NONE
- **Example:** `chore(deps): update dependencies`

### ci
- **Description:** CI/CD configuration changes
- **SemVer:** NONE
- **Example:** `ci(github): add code coverage workflow`

### build
- **Description:** Build system changes
- **SemVer:** NONE
- **Example:** `build: update webpack configuration`

---

## Breaking Changes

**SemVer:** MAJOR

### Methods

1. Add '!' after type/scope: `feat!:` or `feat(scope)!:`
2. Add footer: `BREAKING CHANGE: <description>`

### Examples

**With exclamation mark:**
```
feat(api)!: change response format

BREAKING CHANGE: API response structure changed from array to object
```

**With footer:**
```
chore!: drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6
```

---

## Scope

**Optional:** Yes  
**Description:** Section of codebase affected  
**Format:** Enclosed in parentheses after type

### Examples
- `feat(auth)`
- `fix(database)`
- `refactor(utils)`

---

## Body

**Optional:** Yes  
**Description:** Detailed explanation of changes and context

### Guidelines
- Explain what was changed and why
- Describe the problem being solved
- Avoid explaining HOW code works (focus on WHY it's needed)
- Can be multiple paragraphs

### Example
```
The user import dialog now closes automatically after successful import.

Previously users had to manually close the dialog, which caused confusion
when multiple imports were performed in sequence.
```

---

## Footer

**Optional:** Yes  
**Format:** `token: value` or `token #value`

### Examples
- `Reviewed-by: John Doe`
- `Refs: #123, #456`
- `Co-authored-by: Jane Smith`
- `BREAKING CHANGE: description`

---

## Complete Examples

### Simple Feature
```
feat(search): add autocomplete for product names
```
Simple feature without body.

### Bug Fix with Scope
```
fix(cart): prevent duplicate items when clicking add quickly
```
Bug fix with clear scope.

### Detailed Change
```
feat(payment): add support for cryptocurrency payments

Implements Bitcoin and Ethereum payment processing using Stripe API.
Users can now select crypto as payment method during checkout.
Payment verification happens in real-time.
```
Feature with detailed body.

### Breaking Change (Simple)
```
feat!: redesign authentication API
```
Breaking change with exclamation mark.

### Breaking Change (Detailed)
```
feat(auth)!: switch from JWT to OAuth2

Migrating authentication from JWT tokens to OAuth2 standard.
This improves security and enables third-party integrations.

BREAKING CHANGE: all existing tokens are invalidated
Migration guide: https://docs.example.com/oauth2-migration
```
Complex breaking change with migration info.

---

## Agent Guidelines

### Priority Order

1. Verify single responsibility: one commit = one logical change
2. Determine commit type (feat, fix, etc.)
3. Identify affected scope (optional but recommended)
4. Write clear, concise description (≤50 chars)
5. Add body if context is needed (≤72 chars per line)
6. Check for breaking changes
7. Add relevant footers/references

### Decision Tree

**Is it a new feature?**
- ✅ Yes → Use 'feat' type
- ❌ No → Proceed to next check

**Is it a bug fix?**
- ✅ Yes → Use 'fix' type
- ❌ No → Proceed to next check

**Is it a non-code change?**
- Documentation → Use 'docs' type
- Tests → Use 'test' type
- Dependencies → Use 'chore' type
- Other → Use appropriate type (style, refactor, perf, ci, build)

### Anti-Patterns ❌

- `'fix stuff'` - too vague
- `'updates'` - meaningless
- `'Fixed bug in login'` - wrong mood (should be 'Fix bug in login')
- `'Subject exceeds 50 characters and makes it hard to read'` - too long
- `'Implementation of new feature with multiple parts'` - too broad, split into separate commits
- Mixing multiple unrelated changes in one commit

### Best Patterns ✅

- `'feat(api): add user profile endpoint'`
- `'fix(auth): resolve race condition in token refresh'`
- `'test(utils): add edge case tests for date parser'`
- `'refactor(database): simplify connection pooling'`
- Clear, specific, concise, lowercase type

---

## Tools and Standards

- **Specification:** Conventional Commits 1.0.0
- **Related to:** Semantic Versioning (SemVer)

### Supporting Tools

- **commitlint** - validates commit messages
- **commitizen** - interactive commit prompt
- **husky** - git hooks for quality checks
- **angular-changelog** - generates CHANGELOG automatically
