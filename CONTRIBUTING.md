# Contributing to Your FastMCP Server

This guide helps you customize and extend this boilerplate for your specific use case.

## Development Setup

### Initial Setup

1. **Clone the repository** (if you haven't already)
   ```bash
   cd qnagent
   ```

2. **Run setup script**
   ```bash
   ./scripts/setup.sh
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

### Development Workflow

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Make your changes** to the code

3. **Run code quality checks**
   ```bash
   # Format code
   black src/ tests/

   # Sort imports
   isort src/ tests/

   # Lint
   ruff check src/ tests/

   # Type check
   mypy src/
   ```

4. **Run tests**
   ```bash
   pytest
   ```

5. **Test manually**
   ```bash
   ./scripts/run.sh
   ```

## Adding New Tools

Tools are the primary way to expose functionality to LLMs through the MCP protocol.

### Creating a New Tool Module

1. **Create a new file** in `src/tools/`:
   ```bash
   touch src/tools/my_custom_tools.py
   ```

2. **Define your tools**:
   ```python
   """Custom tools for my specific business logic."""

   import logging
   from typing import Dict, Any
   from fastmcp import FastMCP
   from src.auth.provider import get_user_info_from_token

   logger = logging.getLogger(__name__)

   def register_my_tools(mcp: FastMCP) -> None:
       """Register custom tools with the MCP server."""

       @mcp.tool()
       async def my_business_function(
           input_param: str,
           optional_param: int = 10
       ) -> Dict[str, Any]:
           """
           Description of what this tool does.

           This docstring becomes the tool description that
           the LLM sees, so be clear and specific.

           Args:
               input_param: Description of this parameter
               optional_param: Description with default value

           Returns:
               Dictionary with results
           """
           logger.info(f"Tool called with: {input_param}")

           # Access authenticated user if needed
           user_info = get_user_info_from_token()
           user_email = user_info.get("email")

           # Your business logic here
           result = process_something(input_param, optional_param)

           return {
               "success": True,
               "result": result,
               "user": user_email
           }

       @mcp.tool()
       async def another_tool(data: list[str]) -> dict:
           """Another tool example."""
           # Implementation
           return {"processed": len(data)}

       logger.info("Custom tools registered")
   ```

3. **Register in server.py**:
   ```python
   # In src/server.py
   from src.tools.my_custom_tools import register_my_tools

   # In create_server() function:
   register_my_tools(mcp)
   ```

### Tool Best Practices

- **Clear docstrings**: LLMs use these to understand the tool
- **Type hints**: Always use type hints for parameters
- **Error handling**: Return structured error responses
- **Logging**: Log important operations
- **User context**: Use `get_user_info_from_token()` for user-specific operations

## Adding New Resources

Resources provide read-only data and context to LLMs.

### Creating a New Resource Module

1. **Create a new file** in `src/resources/`:
   ```bash
   touch src/resources/my_resources.py
   ```

2. **Define your resources**:
   ```python
   """Custom resources for my application."""

   import logging
   from typing import Dict, Any
   from fastmcp import FastMCP

   logger = logging.getLogger(__name__)

   def register_my_resources(mcp: FastMCP) -> None:
       """Register custom resources with the MCP server."""

       # Static resource
       @mcp.resource("myapp://config")
       async def get_app_config() -> str:
           """Provide application configuration information."""
           return """
           # Application Configuration

           **Version**: 1.0.0
           **Environment**: Production

           ## Features
           - Feature A: Enabled
           - Feature B: Disabled
           """

       # Dynamic resource with parameters
       @mcp.resource("myapp://user/{user_id}/profile")
       async def get_user_profile(user_id: str) -> Dict[str, Any]:
           """Get user profile by ID."""
           # Fetch from database
           profile = fetch_user_profile(user_id)

           return {
               "user_id": user_id,
               "profile": profile,
               "retrieved_at": datetime.utcnow().isoformat()
           }

       # Resource returning structured data
       @mcp.resource("myapp://data/summary")
       async def get_data_summary() -> dict:
           """Provide summary of application data."""
           return {
               "total_users": 1000,
               "active_sessions": 42,
               "data_version": "2.1.0"
           }

       logger.info("Custom resources registered")
   ```

3. **Register in server.py**:
   ```python
   from src.resources.my_resources import register_my_resources

   register_my_resources(mcp)
   ```

### Resource Best Practices

- **URI naming**: Use clear, hierarchical URIs (e.g., `myapp://section/resource`)
- **Documentation**: Include good docstrings
- **Caching**: Consider caching for expensive operations
- **Security**: Don't expose sensitive data without checking auth

## Extending Configuration

### Adding Custom Config Options

1. **Extend the config class** in `src/config.py`:
   ```python
   @dataclass
   class ServerConfig:
       # ... existing fields ...

       # Add your custom fields
       my_custom_setting: str = "default_value"
       my_api_key: Optional[str] = None

       @classmethod
       def from_env(cls) -> "ServerConfig":
           # ... existing code ...

           return cls(
               # ... existing fields ...
               my_custom_setting=os.getenv("MY_CUSTOM_SETTING", "default_value"),
               my_api_key=os.getenv("MY_API_KEY"),
           )
   ```

2. **Add to .env.example**:
   ```bash
   # Custom Settings
   MY_CUSTOM_SETTING=your_value
   MY_API_KEY=your-api-key
   ```

3. **Use in your code**:
   ```python
   from src.config import get_config

   config = get_config()
   api_key = config.my_api_key
   ```

## Adding External Dependencies

### Python Packages

1. **Add to requirements.txt**:
   ```bash
   # Add your dependency
   requests>=2.31.0
   sqlalchemy>=2.0.0
   ```

2. **Install**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Update pyproject.toml** if needed:
   ```toml
   dependencies = [
       "fastmcp>=0.2.0",
       # ... existing deps ...
       "requests>=2.31.0",
   ]
   ```

### Database Integration Example

1. **Add database dependencies**:
   ```bash
   # In requirements.txt
   sqlalchemy>=2.0.0
   psycopg2-binary>=2.9.0  # for PostgreSQL
   ```

2. **Create database module**:
   ```python
   # src/utils/database.py
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from src.config import get_config

   def get_db_engine():
       config = get_config()
       return create_engine(config.database_url)

   def get_db_session():
       engine = get_db_engine()
       Session = sessionmaker(bind=engine)
       return Session()
   ```

3. **Use in tools**:
   ```python
   from src.utils.database import get_db_session

   @mcp.tool()
   async def query_database(query: str) -> dict:
       """Execute database query."""
       session = get_db_session()
       # ... your database logic
   ```

## Testing Your Changes

### Writing Tests

Create test files in `tests/`:

```python
# tests/test_my_tools.py
import pytest
from unittest.mock import Mock, patch
from src.tools.my_custom_tools import my_business_function

@pytest.mark.asyncio
async def test_my_business_function():
    """Test my custom business function."""
    result = await my_business_function(
        input_param="test",
        optional_param=5
    )

    assert result["success"] is True
    assert "result" in result

@pytest.mark.asyncio
async def test_with_auth_context(mock_azure_env):
    """Test tool with authentication context."""
    with patch("src.auth.provider.get_access_token") as mock_token:
        # Mock the token
        mock_token.return_value.claims = {
            "email": "test@example.com",
            "sub": "test-user-id"
        }

        result = await my_business_function("test")
        assert result["user"] == "test@example.com"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_tools.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run only tests matching a pattern
pytest -k "test_my_business"
```

## Code Style Guidelines

### Formatting

- **Line length**: 120 characters
- **Formatting tool**: Black
- **Import sorting**: isort with black profile

### Naming Conventions

- **Functions/methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private methods**: `_leading_underscore`

### Documentation

- **Docstrings**: Google style
- **Type hints**: Always use for public functions
- **Comments**: Explain "why", not "what"

### Example:

```python
from typing import Dict, Any, Optional

def process_user_data(
    user_id: str,
    data: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process user data with optional configuration.

    This function validates and transforms user data according
    to the provided options.

    Args:
        user_id: The unique identifier for the user
        data: Raw user data to process
        options: Optional processing configuration

    Returns:
        Processed data dictionary with validation results

    Raises:
        ValueError: If user_id is invalid or data is malformed
    """
    if not user_id:
        raise ValueError("user_id is required")

    # Use options if provided, otherwise defaults
    config = options or get_default_options()

    # Process the data
    processed = transform_data(data, config)

    return {
        "user_id": user_id,
        "processed_data": processed,
        "success": True
    }
```

## Deployment Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Code formatted (black, isort)
- [ ] No linting errors (ruff)
- [ ] Type checking passes (mypy)
- [ ] Environment variables configured
- [ ] Azure credentials verified
- [ ] HTTPS configured for production
- [ ] Secrets stored securely (Key Vault)
- [ ] Logging configured
- [ ] Monitoring setup
- [ ] Documentation updated
- [ ] Performance tested
- [ ] Security reviewed

## Common Patterns

### Async Tool with External API

```python
import httpx

@mcp.tool()
async def fetch_external_data(query: str) -> dict:
    """Fetch data from external API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.example.com/data",
            params={"q": query}
        )
        response.raise_for_status()
        return response.json()
```

### Tool with Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@mcp.tool()
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def resilient_operation(data: str) -> dict:
    """Operation with automatic retry."""
    # ... implementation
```

### Cached Resource

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_expensive_data(key: str) -> dict:
    """Cached expensive operation."""
    # ... expensive computation
    return result

@mcp.resource("myapp://cached/{key}")
async def cached_resource(key: str) -> dict:
    """Resource with caching."""
    return get_expensive_data(key)
```

## Getting Help

- Review the [README](README.md) for general guidance
- Check [FastMCP documentation](https://gofastmcp.com)
- See [Azure setup guide](docs/AZURE_SETUP.md) for authentication
- Look at example implementations in `src/tools/example_tools.py`

## Questions?

Open an issue in your repository for:
- Feature requests
- Bug reports
- Documentation improvements
- General questions about the boilerplate
