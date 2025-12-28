# Contributing to Local Research Assistant

## Development setup
1. Clone the repo and check out a new `feature/<issue>-description` branch (see Branch Naming below).
2. Install dependencies via Conda or pip:
   ```bash
   conda env create -f environment.yml
   conda activate research_assistant
   pip install -r requirements.txt
   ```
3. Copy `.env.example` (or create a new `.env`) and set `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL` before running commands.

## Running tests
- Run `pytest` from the repository root. Include new tests whenever you add logic or adjust workflows.
- If you rely on mocked services, add fixtures or factories in dedicated test modules that live alongside the code they cover.

## Code style guidelines
- Follow the existing style: clear function names, concise docstrings, and typing hints where appropriate.
- Keep line lengths reasonable (≈88–100 characters) and prefer expressive logging over `print` statements.
- Use `logger` for structured diagnostics and avoid swallowing exceptions without context.
- Group related imports (stdlib, third-party, local) and keep alphabetical order within groups.

## Adding new features
1. Update `README.md`, `API_DOCS.md`, and other docs so users and developers understand the change.
2. Add or adjust automated checks (e.g., config validation, exports) to cover the feature.
3. Write or extend tests to defend the new behavior.
4. Run `pytest` and verify the new code passes before pushing.

## Branch naming conventions
- Base new work on `main` or the latest stable branch.
- Name feature branches like `feature/42-brief-description`.
- Use `fix/<issue>-description` for small bug fixes and `docs/<topic>` for documentation-only changes.

## Pull request process
1. Push your branch to the remote repository and open a PR against `main` (or the current release branch).
2. Describe what changed, why, and include testing steps (e.g., `pytest`).
3. Link related issues or discussions so reviewers have context.
4. Address review feedback, rebase if necessary, and squash commits when it simplifies history.
5. Merge once at least one approval and passing CI/tests exist.
