#!/bin/bash

# run_tests.sh - Self-test script for warehouse FastAPI container

set -e  # Exit on any error

echo "ðŸ§ª Starting Warehouse API Self-Tests..."
echo "=================================="

# Function to wait for API to be ready
wait_for_api() {
    local max_attempts=30
    local attempt=1
    
    echo "â³ Waiting for API to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://warehouse-api:8000/health > /dev/null 2>&1; then
            echo "âœ… API is ready!"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts - API not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "âŒ API failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Function to run the HTTP-based test suite
run_http_tests() {
    echo "ðŸŒ Running HTTP-based test suite..."
    echo "-----------------------------------"
    
    # Run pytest with verbose output and short traceback
    python -m pytest test_warehouse_workflow.py -v --tb=short --color=yes
    
    local test_exit_code=$?
    
    if [ $test_exit_code -eq 0 ]; then
        echo "âœ… HTTP tests passed!"
        return 0
    else
        echo "âŒ HTTP tests failed (exit code: $test_exit_code)"
        return $test_exit_code
    fi
}

# Function to run the client-based test suite
run_client_tests() {
    echo "ðŸ”§ Running client-based test suite..."
    echo "-------------------------------------"
    
    # Run pytest with verbose output and short traceback
    python -m pytest test_warehouse_client.py -v --tb=short --color=yes
    
    local test_exit_code=$?
    
    if [ $test_exit_code -eq 0 ]; then
        echo "âœ… Client tests passed!"
        return 0
    else
        echo "âŒ Client tests failed (exit code: $test_exit_code)"
        return $test_exit_code
    fi
}

# Function to run both test suites
run_full_tests() {
    echo "ðŸ“‹ Running complete test suite..."
    echo "--------------------------------"
    
    local http_passed=true
    local client_passed=true
    
    # Run HTTP tests first
    if ! run_http_tests; then
        http_passed=false
    fi
    
    echo ""  # Add spacing between test suites
    
    # Run client tests
    if ! run_client_tests; then
        client_passed=false
    fi
    
    # Summary
    echo ""
    echo "ðŸ“Š Test Summary:"
    echo "================"
    if [ "$http_passed" = true ]; then
        echo "âœ… HTTP-based tests: PASSED"
    else
        echo "âŒ HTTP-based tests: FAILED"
    fi
    
    if [ "$client_passed" = true ]; then
        echo "âœ… Client-based tests: PASSED"
    else
        echo "âŒ Client-based tests: FAILED"
    fi
    
    # Return failure if either test suite failed
    if [ "$http_passed" = true ] && [ "$client_passed" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to run basic smoke tests
run_smoke_tests() {
    echo "ðŸ’¨ Running smoke tests..."
    echo "------------------------"
    
    # Basic health check
    echo "Testing health endpoint..."
    if ! curl -f -s http://warehouse-api:8000/health | grep -q '"ok":true'; then
        echo "âŒ Health check failed"
        return 1
    fi
    echo "âœ… Health check passed"
    
    # Test role-based access
    echo "Testing role-based access..."
    if ! curl -f -s -H "X-AGENT-ROLE: customer" http://warehouse-api:8000/orders > /dev/null; then
        echo "âŒ Customer role access failed"
        return 1
    fi
    echo "âœ… Role-based access working"
    
    # Test state machine info
    echo "Testing state machine endpoint..."
    if ! curl -f -s http://warehouse-api:8000/state-machine/info > /dev/null; then
        echo "âŒ State machine endpoint failed"
        return 1
    fi
    echo "âœ… State machine endpoint working"
    
    # Quick client import test
    echo "Testing client availability..."
    if python -c "from warehouse_client import create_customer_client, create_fulfillment_client; print('âœ… Client imports working')" 2>/dev/null; then
        echo "âœ… Client module available"
    else
        echo "âš ï¸  Client module not available (warehouse_client.py not found)"
    fi
    
    echo "âœ… All smoke tests passed!"
    return 0
}

# Function to run integration tests (subset of full tests)
run_integration_tests() {
    echo "ðŸ”— Running integration tests..."
    echo "------------------------------"
    
    # Run specific test classes that are most important
    local integration_passed=true
    
    echo "Running core HTTP workflow tests..."
    if ! python -m pytest test_warehouse_workflow.py::TestBasicWorkflow -v --tb=short --color=yes; then
        integration_passed=false
    fi
    
    echo ""
    echo "Running core client workflow tests..."
    if ! python -m pytest test_warehouse_client.py::TestClientBasicWorkflow -v --tb=short --color=yes; then
        integration_passed=false
    fi
    
    if [ "$integration_passed" = true ]; then
        echo "âœ… Integration tests passed!"
        return 0
    else
        echo "âŒ Integration tests failed!"
        return 1
    fi
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [test_type]"
    echo ""
    echo "Test Types:"
    echo "  smoke       - Basic functionality tests (fastest)"
    echo "  http        - HTTP-based test suite only"
    echo "  client      - Client-based test suite only"
    echo "  integration - Core workflow tests (HTTP + client)"
    echo "  full        - Complete test suite (default)"
    echo "  quick       - Same as smoke"
    echo ""
    echo "Examples:"
    echo "  $0              # Run full test suite"
    echo "  $0 smoke        # Quick smoke tests"
    echo "  $0 integration  # Core functionality tests"
    echo "  $0 client       # Only client tests"
}

# Main execution
main() {
    local test_type="${1:-full}"
    
    case $test_type in
        "smoke"|"quick")
            wait_for_api && run_smoke_tests
            ;;
        "http")
            wait_for_api && run_http_tests
            ;;
        "client")
            wait_for_api && run_client_tests
            ;;
        "integration")
            wait_for_api && run_integration_tests
            ;;
        "full")
            wait_for_api && run_full_tests
            ;;
        "help"|"-h"|"--help")
            show_usage
            exit 0
            ;;
        *)
            echo "âŒ Unknown test type: $test_type"
            echo ""
            show_usage
            exit 1
            ;;
    esac
    
    local exit_code=$?
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "ðŸŽ‰ Self-tests completed successfully!"
    else
        echo "ðŸ’¥ Self-tests failed!"
        echo "Check logs above for details."
    fi
    
    return $exit_code
}

# Run main function with all arguments
main "$@"