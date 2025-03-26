# Control Test Suite

This test suite provides comprehensive testing for the Control component, with a focus on simulating Cloud interactions and validating Control's behavior with workflow packages.

## Directory Structure

```
tests/
├── README.md                 # This file
├── __init__.py              # Makes tests importable
├── conftest.py              # pytest configuration and fixtures
├── data/                    # Test data directory
│   ├── workflows/           # Sample workflow packages
│   ├── screenshots/         # Test screenshots
│   └── configs/             # Test configurations
├── logs/                    # Test-specific logging
├── utils/                   # Test utilities
│   ├── __init__.py
│   ├── workflow_builder.py  # Workflow package builder
│   ├── cloud_simulator.py   # Cloud relay simulator
│   └── device_simulator.py  # Device simulator
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_binary.py      # Binary transfer tests
│   ├── test_workflow.py    # Workflow execution tests
│   └── test_device.py      # Device management tests
└── integration/             # Integration tests
    ├── __init__.py
    ├── test_cloud_comm.py  # Cloud communication tests
    └── test_e2e.py         # End-to-end workflow tests
```

## Key Components

### Workflow Builder
The `workflow_builder.py` utility helps create test workflow packages that match the expected format from Cloud. It provides:
- Functions to build workflow packages with various commands
- Support for both encrypted and unencrypted packages
- Validation of package structure
- Helper methods for common workflow patterns

### Cloud Simulator
The `cloud_simulator.py` utility simulates the Cloud relay service, allowing tests to:
- Send workflow packages to Control
- Receive and validate responses
- Test binary data transfer
- Simulate connection issues

### Device Simulator
The `device_simulator.py` utility provides a mock device interface that:
- Responds to ADB commands
- Returns simulated screenshots
- Simulates device states and errors

## Running Tests

### Prerequisites
1. Install test dependencies:
```bash
pip install -r tests/requirements.txt
```

2. Configure test environment:
```bash
cp tests/data/configs/test_config.example.json tests/data/configs/test_config.json
# Edit test_config.json as needed
```

### Running All Tests
```bash
pytest tests/
```

### Running Specific Test Categories
```bash
# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_binary.py
```

### Test Logging
All test runs create detailed logs in the `tests/logs` directory:
- `test_run_{timestamp}.log`: Complete test run log
- Individual test logs in test-specific subdirectories

## Writing Tests

### Unit Tests
Unit tests should:
- Test individual components in isolation
- Mock dependencies using fixtures
- Cover both success and error cases
- Validate specific behaviors

Example:
```python
def test_binary_transfer(binary_transfer):
    # Test creating and processing binary messages
    data = b"test data"
    message = binary_transfer.create_binary_message("pkg_1", "content_1", data)
    pkg_id, content_id, content = binary_transfer.process_binary_message(message)
    
    assert pkg_id == "pkg_1"
    assert content_id == "content_1"
    assert content == data
```

### Integration Tests
Integration tests should:
- Test component interactions
- Use the Cloud simulator
- Validate end-to-end workflows
- Test error recovery

Example:
```python
def test_workflow_execution(cloud_sim, device_sim):
    # Create and send test workflow
    workflow = create_test_workflow()
    cloud_sim.send_workflow(workflow)
    
    # Verify execution and responses
    responses = cloud_sim.get_responses()
    assert_workflow_success(responses)
```

## Adding New Tests

1. Create test file in appropriate directory (unit/ or integration/)
2. Add fixtures to conftest.py if needed
3. Follow existing patterns for similar tests
4. Include both positive and negative test cases
5. Add logging statements for debugging
6. Update this README if adding new patterns

## Best Practices

1. **Isolation**: Each test should be independent and clean up after itself
2. **Fixtures**: Use pytest fixtures for setup/teardown
3. **Logging**: Include detailed logging for debugging
4. **Documentation**: Document test purpose and requirements
5. **Coverage**: Aim for comprehensive coverage of features
6. **Validation**: Include assertions for all expected behaviors

## Troubleshooting

Common issues and solutions:

1. **Test Failures**
   - Check test logs in tests/logs/
   - Verify test configuration
   - Ensure clean test environment

2. **Simulator Issues**
   - Check simulator logs
   - Verify network settings
   - Reset simulator state

3. **Resource Cleanup**
   - Tests should clean up resources
   - Use cleanup fixtures
   - Check for leftover processes

## Contributing

1. Follow existing test patterns
2. Update documentation
3. Include logging
4. Clean up resources
5. Run full suite before submitting
