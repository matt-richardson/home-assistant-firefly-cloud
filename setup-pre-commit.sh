#!/bin/bash
set -e

echo "Installing pre-commit hooks for Firefly Cloud integration..."
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "pre-commit is not installed. Installing..."
    pip install pre-commit
    echo ""
fi

# Install the git hooks
echo "Installing git hooks..."
pre-commit install

echo ""
echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "The following checks will run automatically on git commit:"
echo "  - black (code formatting)"
echo "  - isort (import sorting)"
echo "  - flake8 (style checking)"
echo "  - mypy (type checking)"
echo ""
echo "To run checks manually:"
echo "  pre-commit run --all-files"
echo ""
echo "To skip hooks on a specific commit (not recommended):"
echo "  git commit --no-verify"
