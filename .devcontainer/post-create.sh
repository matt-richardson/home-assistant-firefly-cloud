#!/bin/bash

# Post-create script for dev container setup
set -e

echo "🚀 Setting up Firefly Cloud Home Assistant integration development environment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get install -y curl wget git

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
python -m pip install --upgrade pip setuptools wheel

# Install Home Assistant and core dependencies
echo "🏠 Installing Home Assistant and core dependencies..."
pip install \
    homeassistant \
    aiohttp>=3.8.0 \
    lxml>=4.9.0 \
    python-dateutil>=2.8.0 \
    voluptuous \
    async-timeout

# Install development tools
echo "🔧 Installing development tools..."
pip install \
    black \
    flake8 \
    mypy \
    pylint \
    isort \
    yamllint \
    codespell \
    pytest>=6.2.5 \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-mock

# Create a basic Home Assistant config directory for testing
echo "🏠 Setting up Home Assistant test environment..."
mkdir -p /workspace/homeassistant_test
mkdir -p /workspace/homeassistant_test/custom_components

# Create a symlink to the integration
ln -sf /workspace/custom_components/firefly_cloud /workspace/homeassistant_test/custom_components/firefly_cloud

# Create a basic Home Assistant configuration
cat > /workspace/homeassistant_test/configuration.yaml << EOF
# Basic Home Assistant configuration for testing Firefly Cloud integration
default_config:

logger:
  default: info
  logs:
    custom_components.firefly_cloud: debug

# Firefly Cloud integration will be configured through the UI
EOF

# Create a basic secrets file
cat > /workspace/homeassistant_test/secrets.yaml << EOF
# Secrets for Home Assistant testing
# Add any required secrets here for Firefly Cloud integration
firefly_school_code: "your_school_code_here"
EOF

# Set proper permissions
chmod +x /workspace/.devcontainer/post-create.sh

# Create a helpful development script
cat > /workspace/dev.sh << 'EOF'
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
EOF

chmod +x /workspace/dev.sh

echo "✅ Development environment setup complete!"
echo ""
echo "🎉 You can now:"
echo "   • Run tests: ./dev.sh test"
echo "   • Run tests with coverage: ./dev.sh test-cov"
echo "   • Run single test: ./dev.sh test-single test_name"
echo "   • Lint code: ./dev.sh lint"
echo "   • Format code: ./dev.sh format"
echo "   • Start Home Assistant: ./dev.sh ha-test"
echo "   • Full validation: ./dev.sh validate"
echo "   • Clean temporary files: ./dev.sh clean"
echo ""
echo "📝 The integration is symlinked to /workspace/homeassistant_test/custom_components/firefly_cloud"
echo "🏠 You can test the integration by running Home Assistant from the homeassistant_test directory"
echo "🎯 Target: Silver tier quality with >95% test coverage"
echo ""
echo "🚀 Ready for Firefly Cloud integration development!"