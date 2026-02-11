# MedMind API Testing Guide

This guide covers how to test the MedMind REST API.

## Prerequisites

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python 3.12**:
   ```bash
   uv python install 3.12.11
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Set up environment variables** (create `.env` file):
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

## Test Structure

```
tests/
├── api/                    # API-specific tests
│   ├── conftest.py        # Fixtures for API tests
│   ├── test_main.py       # Health and root endpoints
│   ├── test_auth.py       # Authentication tests
│   ├── test_chat.py       # Chat endpoint tests
│   ├── test_query.py      # Query endpoint tests
│   └── test_documents.py  # Document endpoint tests
├── conftest.py            # Global fixtures
└── ...                    # Other test files
```

## Running Tests

### Run All Tests

```bash
uv run pytest
```

### Run All API Tests

```bash
uv run pytest tests/api/ -v
```

### Run Specific Test File

```bash
uv run pytest tests/api/test_auth.py -v
uv run pytest tests/api/test_chat.py -v
uv run pytest tests/api/test_query.py -v
uv run pytest tests/api/test_documents.py -v
```

### Run with Coverage

```bash
uv run pytest --cov=physiology_rag --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

### Run Tests by Category

```bash
# Authentication tests only
uv run pytest tests/api/test_auth.py -v

# Chat tests only  
uv run pytest tests/api/test_chat.py -v

# Query tests only
uv run pytest tests/api/test_query.py -v

# Document tests only
uv run pytest tests/api/test_documents.py -v

# Skip integration tests
uv run pytest -m "not integration" -v

# Run only slow tests
uv run pytest -m slow -v
```

## Test Coverage

### Authentication (`test_auth.py`)
- ✅ Creating anonymous sessions
- ✅ Creating named sessions
- ✅ Token refresh
- ✅ Getting current user info
- ✅ Protected endpoint authorization
- ✅ Invalid token rejection
- ✅ Expired token rejection

### Chat (`test_chat.py`)
- ✅ Sending chat messages
- ✅ Authentication required
- ✅ Empty message validation
- ✅ Message length validation
- ✅ Getting chat history
- ✅ Streaming endpoint disabled

### Query (`test_query.py`)
- ✅ Performing RAG queries
- ✅ Search documents
- ✅ Parameter validation (n_results, limit)
- ✅ Authentication required

### Documents (`test_documents.py`)
- ✅ Listing documents
- ✅ Uploading PDFs
- ✅ Invalid file type rejection
- ✅ Path traversal protection
- ✅ Upload status checking
- ✅ Document deletion
- ✅ Document details

### Main API (`test_main.py`)
- ✅ Health check endpoint
- ✅ Root endpoint info
- ✅ OpenAPI schema accessibility

## Key Fixtures

### `client`
FastAPI TestClient instance with mocked settings and mock RAG system

### `auth_token`
Valid JWT token for authenticated requests (obtained via mock login)

### `auth_headers`
Authorization headers with Bearer token

### `mock_rag_system`
Mock RAG system that returns test data without making external API calls

### `test_settings_api`
Test-specific settings with temporary directories and test API key

## Mocking Strategy

The tests use mocking to avoid:
- External API calls (Gemini API)
- Database dependencies
- File system operations

This makes tests:
- **Fast** - no network calls (~8 seconds for 60 tests)
- **Isolated** - no external dependencies
- **Deterministic** - same results every time
- **Safe** - won't affect production data

## Writing New Tests

### Basic Test Pattern

```python
def test_endpoint(client, auth_headers):
    """Test description."""
    response = client.get("/endpoint", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "expected_field" in data
```

### Testing Authentication

```python
def test_protected_endpoint_requires_auth(client):
    """Test that auth is required."""
    response = client.get("/protected")
    assert response.status_code == 401

def test_protected_endpoint_with_auth(client, auth_headers):
    """Test with valid auth."""
    response = client.get("/protected", headers=auth_headers)
    assert response.status_code == 200
```

### Testing Validation

```python
def test_validation(client, auth_headers):
    """Test input validation."""
    response = client.post(
        "/endpoint",
        headers=auth_headers,
        json={"invalid": "data"}
    )
    assert response.status_code == 422  # Validation error
```

## Debugging Tests

### Run with Detailed Output

```bash
uv run pytest tests/api/test_chat.py -v -s --tb=short
```

### Run Single Test

```bash
uv run pytest tests/api/test_auth.py::test_login_anonymous -v
```

### Debug Mode

Add breakpoints in your test:

```python
def test_example(client):
    response = client.get("/endpoint")
    import pdb; pdb.set_trace()  # Debugger breakpoint
    assert response.status_code == 200
```

## Common Issues

### Import Errors
Make sure you've installed all dependencies:
```bash
uv sync
```

### Missing GEMINI_API_KEY
Create `.env` file with your API key:
```bash
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your-real-api-key
```

### Python Version Mismatch
Ensure Python 3.12 is installed:
```bash
uv python install 3.12.11
```

### RAG System Not Initialized
The test fixtures automatically initialize a mock RAG system. If you see "RAG system not initialized" errors, ensure you're using the `client` fixture from `conftest.py`.

## Integration Tests

For testing with real dependencies (not mocked):

1. Set up environment variables:
```bash
export GEMINI_API_KEY=your-real-api-key
```

2. Run with integration marker:
```bash
uv run pytest tests/api/ -m integration -v
```

Note: Integration tests make real API calls and may incur costs.

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Install UV
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install Python
  run: uv python install 3.12.11

- name: Install dependencies
  run: uv sync

- name: Run API tests
  run: uv run pytest tests/api/ -v --tb=short
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

## Performance Testing

For load testing:

```bash
uv add --dev locust

# Create locustfile.py
# Run: uv run locust -f locustfile.py
```

## Security Testing

The tests include security checks:
- ✅ Authentication bypass attempts
- ✅ Invalid token handling
- ✅ Path traversal protection
- ✅ File upload validation

Always run security tests before deployment.

## Migration from Pip to UV

If you're migrating from the old pip-based setup:

**Old way:**
```bash
pip install -r requirements.txt
pip install pytest pytest-cov
pytest tests/api/
```

**New way:**
```bash
uv sync
uv run pytest tests/api/
```

Key differences:
- No `requirements.txt` files needed (dependencies in `pyproject.toml`)
- `uv sync` installs all dependencies including dev dependencies
- `uv run pytest` runs tests in the managed virtual environment
- Lock file (`uv.lock`) ensures reproducible builds
