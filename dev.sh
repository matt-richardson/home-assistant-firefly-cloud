#!/bin/bash

# Development helper script for Firefly Cloud Home Assistant integration

case "$1" in
    "test")
        echo "🧪 Running tests..."
        pytest tests/ -v
        ;;
    "test-cov")
        echo "🧪 Running tests with coverage..."
        pytest tests/ --cov=custom_components.firefly_cloud --cov-report=html --cov-report=term-missing --cov-fail-under=95
        ;;
    "node-setup")
        echo "📦 Installing Node 22 into the venv (nodeenv)..."
        nodeenv -p --node=22.23.5
        ;;
    "test-js")
        if ! command -v node >/dev/null 2>&1; then
            echo "❌ node not found. Activate the venv and run: ./dev.sh node-setup"
            exit 1
        fi
        echo "🧪 Running card JavaScript tests..."
        node --test "tests/js/**/*.test.mjs"
        ;;
    "test-single")
        if [ -z "$2" ]; then
            echo "Usage: ./dev.sh test-single <test_function>"
            echo "Example: ./dev.sh test-single test_get_auth_url"
            exit 1
        fi
        echo "🧪 Running single test: $2"
        pytest tests/ -v -k "$2"
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
    "ha-test")
        echo "🏠 Starting Home Assistant test instance..."
        cd /workspace/homeassistant_test
        echo "📝 Integration available at: http://localhost:8123"
        echo "📝 Add Firefly Cloud integration through Settings > Devices & Services"
        hass --config . --debug
        ;;
    "ha-check")
        echo "🏠 Checking Home Assistant configuration..."
        cd /workspace/homeassistant_test
        hass --config . --script check_config
        ;;
    "validate")
        echo "✅ Running full validation suite..."
        echo "🎨 Formatting code..."
        black custom_components/ tests/
        isort custom_components/ tests/
        echo "🔍 Running linting..."
        flake8 custom_components/ tests/
        pylint custom_components/
        echo "🧪 Running tests with coverage..."
        pytest tests/ --cov=custom_components.firefly_cloud --cov-report=html --cov-report=term-missing --cov-fail-under=95
        echo "🏠 Validating Home Assistant configuration..."
        cd /workspace/homeassistant_test && hass --config . --script check_config
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
        rm -rf /workspace/homeassistant_test/.storage 2>/dev/null || true
        rm -f /workspace/homeassistant_test/home-assistant.log* 2>/dev/null || true
        ;;
    "install")
        echo "📦 Installing integration for testing..."
        mkdir -p /workspace/homeassistant_test/custom_components
        ln -sf /workspace/custom_components/firefly_cloud /workspace/homeassistant_test/custom_components/firefly_cloud
        echo "✅ Integration installed in test Home Assistant instance"
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
        echo "  node-setup   - Install Node 22 into the venv (for test-js)"
        echo "  test-js      - Run the dashboard cards' JavaScript tests"
        echo "  lint         - Run all linting tools"
        echo "  format       - Format code with black and isort"
        echo "  ha-test      - Start Home Assistant test instance"
        echo "  ha-check     - Check Home Assistant configuration"
        echo "  validate     - Run full validation suite (format + lint + test + config)"
        echo "  clean        - Clean up temporary files and logs"
        echo "  install      - Install integration symlink for testing"
        echo "  help         - Show this help message"
        echo ""
        echo "🎯 Silver Tier Quality:"
        echo "  • Must achieve >95% test coverage"
        echo "  • All linting must pass"
        echo "  • Integration must load successfully in Home Assistant"
        echo ""
        echo "🔗 Firefly Cloud Integration Features:"
        echo "  • Today's Schedule sensor"
        echo "  • Week Schedule sensor" 
        echo "  • Upcoming Tasks sensor"
        echo "  • Tasks Due Today sensor"
        ;;
esac
