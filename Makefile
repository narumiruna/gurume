lint:
	uv run ruff check .

type:
	uv run ty check .

test:
	uv run pytest -v -s --cov=src tests

docs:
	uv run mkdocs build --strict

docs-serve:
	uv run mkdocs serve

publish:
	uv build -f wheel
	uv publish

.PHONY: lint type test docs docs-serve publish
