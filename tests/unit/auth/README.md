# Remote Mode Authentication Test Suite

This test suite provides comprehensive testing for the remote mode authentication flow in the SingleStore MCP server. The tests cover the complete OAuth 2.0 + PKCE authentication workflow, token management, and API request authentication.

## Test Structure

### 📁 Test Files

#### `test_remote_auth_flow.py`
- **Purpose**: Tests the core OAuth provider implementation (`SingleStoreOAuthProvider`)
- **Coverage**:
  - OAuth provider initialization and configuration
  - Authorization code generation and exchange
  - Token storage and retrieval from database
  - Token validation and expiration handling
  - Complete end-to-end authentication flow
  - Error handling scenarios

#### `test_oauth_proxy_integration.py`
- **Purpose**: Tests the OAuth proxy integration with FastMCP (`SingleStoreOAuthProxy`)
- **Coverage**:
  - OpenID Connect discovery and configuration
  - JWT token verification with JWKS
  - Proxy provider initialization
  - Integration with RemoteSettings
  - Error handling for proxy scenarios

#### `test_remote_api_auth.py`
- **Purpose**: Tests how authentication is used in API requests
- **Coverage**:
  - Token retrieval from auth provider
  - API request building with authentication headers
  - Error handling for invalid/expired tokens
  - Session context management
  - Concurrent request handling

#### `conftest.py`
- **Purpose**: Shared test fixtures and utilities
- **Provides**:
  - Mock objects for settings, clients, tokens
  - Database connection mocks
  - HTTP request/response mocks
  - Common test data and utilities

## 🚀 Running Tests

### Run All Tests
```bash
# From the test directory
python test_runner.py

# Or using pytest directly
pytest tests/unit/auth/ -v
```

### Run Specific Test File
```bash
python test_runner.py --test test_remote_auth_flow
```

### Run Specific Test Method
```bash
python test_runner.py --test "test_provider_initialization"
```

### Run with Coverage
```bash
python test_runner.py --coverage
```

### Development Testing
```bash
# Watch mode (if pytest-watch is installed)
pytest tests/unit/auth/ --watch

# Run only failed tests
pytest tests/unit/auth/ --lf

# Run with debug output
pytest tests/unit/auth/ -v -s --tb=long
```

## 🔍 Test Scenarios Covered

### Authentication Flow Tests

1. **OAuth Provider Initialization**
   - Database schema creation
   - Settings validation
   - PKCE code generation

2. **Authorization Flow**
   - Client registration
   - Authorization URL generation
   - State management
   - Callback handling

3. **Token Exchange**
   - Authorization code validation
   - Token exchange with SingleStore
   - Token storage in database
   - Error handling for invalid codes

4. **Token Management**
   - Token retrieval and validation
   - Expiration handling
   - Token revocation
   - Database cleanup

### Proxy Integration Tests

1. **OpenID Connect Discovery**
   - Endpoint discovery
   - Configuration validation
   - Error handling for invalid configs

2. **JWT Token Verification**
   - JWKS retrieval and caching
   - Token signature validation
   - Expiration checking
   - Error handling for malformed tokens

3. **FastMCP Integration**
   - Auth provider setup
   - Route registration
   - Request handling

### API Authentication Tests

1. **Token Retrieval**
   - Remote mode token lookup
   - Local mode fallbacks
   - Error handling for missing tokens

2. **Request Authentication**
   - Authorization header handling
   - Token validation in requests
   - Error responses for unauthorized requests

3. **Concurrent Access**
   - Multiple simultaneous requests
   - Token sharing across requests
   - Race condition handling

## 🎯 Test Coverage Areas

### Components Tested
- `src.auth.provider.SingleStoreOAuthProvider`
- `src.auth.proxy_provider.SingleStoreOAuthProxy`
- `src.api.common.get_access_token`
- `src.api.common.build_request`
- `src.config.config.RemoteSettings`

### Authentication Scenarios
- ✅ Valid token authentication
- ✅ Expired token handling
- ✅ Invalid token rejection
- ✅ Missing token handling
- ✅ Authorization code flow
- ✅ Token refresh scenarios
- ✅ Database error handling
- ✅ Network error handling
- ✅ Malformed request handling

### Error Conditions
- ✅ Database connection failures
- ✅ SingleStore API errors
- ✅ Invalid OAuth configurations
- ✅ Network timeouts
- ✅ Malformed JWT tokens
- ✅ JWKS retrieval failures
- ✅ Concurrent access conflicts

## 🔧 Mock Strategy

### Database Mocking
```python
# Database connections and cursors are mocked
mock_conn, mock_cursor = mock_database_connection
mock_cursor.fetchone.return_value = [token_data]
```

### HTTP Request Mocking
```python
# External HTTP requests are mocked
@patch('src.auth.provider.create_mcp_http_client')
async def test_token_exchange(mock_http_client):
    mock_client.post.return_value = mock_token_response
```

### Settings Mocking
```python
# Configuration is mocked for isolated testing
mock_settings = mock_remote_settings()
mock_settings.client_id = "test-client-id"
```

## 📊 Test Metrics

### Coverage Goals
- **Unit Test Coverage**: >90% for authentication components
- **Integration Coverage**: >80% for auth flow scenarios
- **Error Handling**: 100% for critical error paths

### Performance Benchmarks
- Token validation: <10ms per request
- Authorization flow: <5 seconds end-to-end
- Database operations: <100ms per query

## 🐛 Debugging Tests

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure you're in the project root
   cd /path/to/mcp-server-singlestore
   python -m pytest tests/unit/auth/
   ```

2. **Mock Configuration**
   ```python
   # Check that mocks are properly configured
   assert mock_function.called
   assert mock_function.call_count == 1
   ```

3. **Async Test Issues**
   ```python
   # Make sure async tests are properly marked
   @pytest.mark.asyncio
   async def test_async_function():
       result = await async_function()
   ```

### Test Debugging Commands
```bash
# Run with maximum verbosity
pytest tests/unit/auth/ -vvv -s

# Run single test with debugging
pytest tests/unit/auth/test_remote_auth_flow.py::test_specific_function -vvv -s --tb=long

# Run with pdb debugger
pytest tests/unit/auth/ --pdb
```

## 🔄 Continuous Integration

### CI Pipeline Tests
```yaml
# Example GitHub Actions configuration
- name: Run Remote Auth Tests
  run: |
    python -m pytest tests/unit/auth/ \
      --cov=src.auth \
      --cov=src.api.common \
      --cov-report=xml \
      --junit-xml=test-results.xml
```

### Local Pre-commit Testing
```bash
# Run before committing changes
./tests/unit/auth/test_runner.py --coverage
```

## 📈 Extending Tests

### Adding New Test Cases

1. **Create test method in appropriate file**:
   ```python
   async def test_new_scenario(self, oauth_provider, sample_client):
       # Test implementation
       result = await oauth_provider.new_method()
       assert result.is_valid
   ```

2. **Add fixtures if needed**:
   ```python
   @pytest.fixture
   def new_test_fixture():
       return MockObject()
   ```

3. **Update test runner if new file created**:
   ```python
   test_files = [
       "test_remote_auth_flow.py",
       "test_oauth_proxy_integration.py",
       "test_remote_api_auth.py",
       "test_new_feature.py"  # Add new file
   ]
   ```

### Test Guidelines

1. **Use descriptive test names**
2. **Test one scenario per test method**
3. **Use fixtures for common setup**
4. **Mock external dependencies**
5. **Assert both positive and negative cases**
6. **Include error handling tests**

## 📚 Related Documentation

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [pytest Documentation](https://docs.pytest.org/)
