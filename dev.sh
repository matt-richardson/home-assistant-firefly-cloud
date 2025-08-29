#!/bin/bash

# Development helper script for Firefly Cloud Home Assistant integration

case "$1" in
    "test")
        echo "🧪 Running tests..."
        python -m pytest tests/ -v
        ;;
    "test-cov")
        echo "🧪 Running tests with coverage..."
        python -m pytest tests/ --cov=custom_components.firefly_cloud --cov-report=html --cov-report=term-missing --cov-fail-under=95
        ;;
    "test-single")
        if [ -z "$2" ]; then
            echo "Usage: ./dev.sh test-single <test_function>"
            echo "Example: ./dev.sh test-single test_get_auth_url"
            exit 1
        fi
        echo "🧪 Running single test: $2"
        python -m pytest tests/ -v -k "$2"
        ;;
    "lint")
        echo "🔍 Running linting..."
        echo "Running black..."
        black --check custom_components/ tests/
        echo "Running flake8..."
        flake8 custom_components/ tests/
        echo "Running mypy..."
        mypy custom_components/
        echo "Running pylint..."
        pylint custom_components/
        ;;
    "format")
        echo "🎨 Formatting code..."
        black custom_components/ tests/
        isort custom_components/ tests/
        ;;
    "validate")
        echo "✅ Running full validation suite..."
        echo "🎨 Formatting code..."
        black custom_components/ tests/
        isort custom_components/ tests/
        echo "🔍 Running linting..."
        flake8 custom_components/ tests/ --max-line-length=88 --extend-ignore=E203,W503
        echo "🧪 Running tests with coverage..."
        python -m pytest tests/ --cov=custom_components.firefly_cloud --cov-report=html --cov-report=term-missing --cov-fail-under=95
        ;;
    "clean")
        echo "🧹 Cleaning up..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        find . -type f -name ".coverage" -delete
        find . -type f -name "coverage.xml" -delete
        ;;
    "help"|*)
        echo "🚀 Firefly Cloud Home Assistant Integration Development Helper"
        echo ""
        echo "Usage: ./dev.sh <command>"
        echo ""
        echo "Commands:"
        echo "  test         - Run all tests"
        echo "  test-cov     - Run tests with coverage report (Silver tier: 95%+)"
        echo "  test-single  - Run a single test function"
        echo "  lint         - Run all linting tools"
        echo "  format       - Format code with black and isort"
        echo "  validate     - Run full validation suite (format + lint + test)"
        echo "  clean        - Clean up temporary files"
        echo "  help         - Show this help message"
        echo ""
        echo "🎯 Silver Tier Quality Requirements:"
        echo "  • Must achieve >95% test coverage"
        echo "  • All linting must pass"
        echo "  • Modern Python async patterns"
        echo ""
        echo "🔗 Firefly Cloud Integration Features:"
        echo "  • Today's Schedule sensor"
        echo "  • Week Schedule sensor" 
        echo "  • Upcoming Tasks sensor"
        echo "  • Tasks Due Today sensor"
        ;;
esac