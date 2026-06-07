
EXCLUDE_FILES=".venv*,*.ipynb,cache/*,dev/*"
ruff check . --line-length=180 --exclude "$EXCLUDE_FILES"
ruff format . --line-length=180 --exclude "$EXCLUDE_FILES"