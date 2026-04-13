# LLM Server Project Rules

> **Note**: This document contains project-specific guidelines for AI agents (including Claude, Cursor, and other LLM-powered tools) working on this codebase.

## Conventional Commits

All commits MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>
```

### Commit Types

| Type | Purpose | Version Bump |
|------|---------|--------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement | PATCH |
| `refactor` | Code refactoring (no behavior change) | No bump |
| `test` | Adding tests | No bump |
| `chore` | Maintenance tasks | No bump |
| `docs` | Documentation changes | No bump |
| `ci` | CI/CD changes | No bump |
| `revert` | Revert previous commit | Depends on reverted commit |

### Format Examples

✅ **Valid:**
- `feat: add new API endpoint`
- `feat(api): add user authentication`
- `fix: resolve memory leak in session manager`
- `fix(gpu): correct temperature reading for AMD GPUs`
- `perf: optimize GPU metrics polling`
- `refactor: simplify session state management`
- `test: add unit tests for GPU monitoring`
- `chore: update dependencies`
- `docs: add API reference documentation`
- `ci: add conventional commit validation`
- `revert: revert breaking change from v0.2.0`

❌ **Invalid:**
- `Update README` (missing type)
- `feat add new feature` (missing colon)
- `fix: bug fix` (no description after colon)
- `Fix bug in GPU monitoring` (wrong format)

### AI Agent Guidelines

1. **Always use conventional commit format** - Never commit without a type prefix
2. **Use lowercase** - `ci:` not `CI:`, `feat:` not `Feat:`
3. **Use parentheses for scope** - `feat(api):`, not `feat api:`
4. **Describe what changed** - Be specific about the change
5. **Chores don't bump version** - `chore:`, `refactor:`, `ci:`, `docs:` don't trigger version bumps
6. **feat and fix bump versions** - Only these types trigger semantic version increments

## Development Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit with conventional format
3. Push branch and create PR
4. Merge to `main` → **automatically versioned via conventional commits**

> **Note**: This project uses batch scripts (.cmd/.bat), not compiled binaries. Versioning is handled through git tags and conventional commit types.

## Code Quality Standards

### Python Code
- **Linting**: Run `ruff check .` before committing - no errors allowed
- **Formatting**: Run `black .` before committing - code must be formatted
- **Test before push**: Ensure all tests pass locally before pushing
- **Import order**: Standard library → third-party → local imports

### Python File Requirements
- All Python files must have a shebang: `#!/usr/bin/env python3`
- All Python files must have a module docstring
- Functions must have type hints and docstrings
- Use f-strings for string formatting (PEP 498)

### CI/CD Pipeline
- **Lint job**: Validates code style with Ruff and Black
- **Test job**: Runs pytest with coverage requirements
- **ShellCheck job**: Validates shell scripts
- **Dependabot**: Automatically creates PRs for dependency updates

### Pre-commit Checklist
Before creating a PR, ensure:
- [ ] All Ruff checks pass (`ruff check .`)
- [ ] All files formatted (`black .`)
- [ ] Tests pass (`pytest`)
- [ ] No hardcoded secrets or credentials
- [ ] Windows paths use raw strings (`r"..."`)
- [ ] Cross-platform paths use `Path.home()` and `Path.resolve()`

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_PORT` | Server port | `8081` |
| `LLM_CTX_SIZE` | Context window size | `65536` |

## Branch Naming Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New features | `feature/ai-tuning-v2` |
| `fix/` | Bug fixes | `fix/windows-path-handling` |
| `refactor/` | Code refactoring | `refactor/gpu-detection` |
| `docs/` | Documentation | `docs/api-endpoints` |
| `add/` | Adding new files | `add/labeler-config` |
| `update/` | Updating existing files | `update/github-setup` |

## PR Labels

PRs should be labeled appropriately:
- **bug**: Bug fixes
- **enhancement**: New features
- **ci**: CI/CD changes
- **docs**: Documentation updates
- **dependencies**: Dependency updates
- **github-actions**: GitHub Actions workflow changes
- **release**: Release preparation

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.x.x): Breaking changes
- **MINOR** (x.X.x): New features (backward compatible)
- **PATCH** (x.x.X): Bug fixes (backward compatible)

> **Note**: For batch scripts, version bumps are typically only needed for significant changes. Use `feat:` for new features and `fix:` for bug fixes to trigger version increments via git tags.