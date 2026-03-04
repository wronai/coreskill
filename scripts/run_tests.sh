#!/bin/bash
# evo-engine Docker Test Runner
# Fully automated testing in isolated Docker environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
TEST_TYPE="all"
REBUILD=false
VERBOSE=false
CLEAN=false

# Help
show_help() {
    cat << EOF
evo-engine Docker Test Runner

Usage: $0 [OPTIONS] [TEST_TYPE]

TEST_TYPES:
  all         Run all tests (default)
  unit        Run unit tests only (fast)
  integration Run integration tests (slower)
  smoke       Quick smoke test
  e2e         End-to-end tests only

OPTIONS:
  -r, --rebuild   Rebuild Docker images before testing
  -v, --verbose   Verbose output
  -c, --clean     Clean test results and rebuild
  -h, --help      Show this help

EXAMPLES:
  $0                    # Run all tests
  $0 unit               # Run unit tests only
  $0 --rebuild all      # Rebuild and run all tests
  $0 -r -v integration   # Rebuild with verbose integration tests
  $0 --clean            # Clean everything and run

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        all|unit|integration|smoke|e2e)
            TEST_TYPE="$1"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Pre-flight checks
preflight() {
    log "Pre-flight checks..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    # Check if docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running."
        exit 1
    fi
    
    success "Docker environment OK"
}

# Clean up previous runs
clean_up() {
    log "Cleaning up previous test runs..."
    
    # Remove old containers
    docker-compose -f "$PROJECT_ROOT/docker-compose.test.yml" rm -f 2>/dev/null || true
    
    # Clean test results
    rm -rf "$PROJECT_ROOT/test-results"
    rm -rf "$PROJECT_ROOT/coverage"
    
    # Optionally remove images
    if [[ "$CLEAN" == "true" ]]; then
        docker rmi evo-engine-test 2>/dev/null || true
        log "Removed test images"
    fi
    
    success "Cleanup complete"
}

# Build test images
build_images() {
    log "Building test Docker images..."
    
    if [[ "$REBUILD" == "true" ]] || [[ "$CLEAN" == "true" ]]; then
        BUILD_FLAGS="--no-cache"
    else
        BUILD_FLAGS=""
    fi
    
    cd "$PROJECT_ROOT"
    
    if [[ "$VERBOSE" == "true" ]]; then
        docker-compose -f docker-compose.test.yml build $BUILD_FLAGS
    else
        docker-compose -f docker-compose.test.yml build $BUILD_FLAGS 2>&1 | grep -E "(Building|Successfully|ERROR|error)" || true
    fi
    
    success "Images built"
}

# Run tests based on type
run_tests() {
    log "Running tests: ${CYAN}$TEST_TYPE${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Create results directories
    mkdir -p test-results coverage
    
    case "$TEST_TYPE" in
        all)
            log "Running complete test suite..."
            if [[ "$VERBOSE" == "true" ]]; then
                docker-compose -f docker-compose.test.yml run --rm test
            else
                docker-compose -f docker-compose.test.yml run --rm test 2>&1 | tee test-results/output.log
            fi
            ;;
        unit)
            log "Running unit tests..."
            docker-compose -f docker-compose.test.yml run --rm test-unit
            ;;
        integration)
            log "Running integration tests..."
            docker-compose -f docker-compose.test.yml run --rm test-integration
            ;;
        smoke)
            log "Running smoke tests..."
            docker-compose -f docker-compose.test.yml run --rm test-smoke
            ;;
        e2e)
            log "Running E2E tests..."
            docker-compose -f docker-compose.test.yml run --rm test python -m pytest tests/test_e2e.py -v --timeout=120
            ;;
    esac
    
    TEST_EXIT_CODE=$?
    
    if [[ $TEST_EXIT_CODE -eq 0 ]]; then
        success "Tests passed!"
    else
        error "Tests failed with exit code $TEST_EXIT_CODE"
    fi
    
    return $TEST_EXIT_CODE
}

# Generate and display report
show_report() {
    log "Test Report"
    echo "===================="
    
    # Check if JUnit report exists
    if [[ -f "$PROJECT_ROOT/test-results/junit.xml" ]]; then
        # Count tests
        TOTAL=$(grep -oP 'tests="\K[0-9]+' "$PROJECT_ROOT/test-results/junit.xml" | head -1 || echo "0")
        FAILURES=$(grep -oP 'failures="\K[0-9]+' "$PROJECT_ROOT/test-results/junit.xml" | head -1 || echo "0")
        ERRORS=$(grep -oP 'errors="\K[0-9]+' "$PROJECT_ROOT/test-results/junit.xml" | head -1 || echo "0")
        
        echo -e "Total tests:   ${CYAN}$TOTAL${NC}"
        echo -e "Failures:      ${RED}$FAILURES${NC}"
        echo -e "Errors:        ${RED}$ERRORS${NC}"
        
        PASSED=$((TOTAL - FAILURES - ERRORS))
        echo -e "Passed:        ${GREEN}$PASSED${NC}"
    fi
    
    # Coverage report
    if [[ -f "$PROJECT_ROOT/coverage/coverage.xml" ]]; then
        COV_LINE=$(grep -oP 'line-rate="\K[0-9.]+' "$PROJECT_ROOT/coverage/coverage.xml" | head -1 || echo "0")
        COV_PCT=$(python3 -c "print(f'{float('$COV_LINE')*100:.1f}')" 2>/dev/null || echo "?")
        echo -e "Line coverage: ${CYAN}${COV_PCT}%${NC}"
    fi
    
    echo ""
    echo "Reports generated:"
    echo "  HTML:    test-results/report.html"
    echo "  JUnit:   test-results/junit.xml"
    echo "  Coverage: coverage/html/index.html"
}

# Main execution
main() {
    echo -e "${CYAN}╔════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   evo-engine Docker Test Suite    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════╝${NC}"
    echo ""
    
    preflight
    
    if [[ "$CLEAN" == "true" ]]; then
        clean_up
    fi
    
    build_images
    run_tests
    TEST_RESULT=$?
    
    show_report
    
    echo ""
    if [[ $TEST_RESULT -eq 0 ]]; then
        success "All tests completed successfully! ✓"
    else
        error "Some tests failed. Check logs above."
        exit 1
    fi
}

# Run main
main
