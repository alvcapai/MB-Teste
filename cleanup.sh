#!/usr/bin/env bash
# remove generated files and virtual environment for a clean commit
rm -rf venv quotes.db __pycache__
# optionally remove .DS_Store if present
find . -name '.DS_Store' -delete

echo "Workspace cleaned. You can now git add and commit the remaining files."
