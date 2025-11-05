# FastMCP Server Boilerplate with Azure Entra ID Authentication & Keycloak Authorization

A production-ready boilerplate for building MCP (Model Context Protocol) servers in Python using FastMCP with **hybrid authentication/authorization architecture**:

- **Authentication**: Microsoft Entra ID (Azure AD) - Common ground for cloud services
- **Authorization**: Keycloak - Protects on-premise critical infrastructure
- **Bridge**: OAuth2 Token Exchange for seamless integration

Designed for **enterprise hybrid cloud-on-premise deployments** where Azure OpenAI needs controlled access to critical data systems.

## Features

- **FastMCP Framework**: Modern, Pythonic MCP server implementation
- **Azure Entra ID Authentication**: Enterprise-grade OAuth2 authentication
- **Keycloak Authorization**: Role-based access control (RBAC) for critical systems
- **OAuth2 Token Exchange**: Seamless authentication handover to authorization
- **Production-Ready**: Comprehensive configuration, logging, and error handling
- **Extensible Architecture**: Clean separation of concerns with modular design
- **Authorization Decorators**: Simple `@require_role` decorators for access control
- **Docker Support**: Multi-stage Dockerfile with development and production targets
- **Redis Integration**: Optional persistent token storage with encryption
- **Type-Safe**: Full type hints throughout the codebase
- **Example Tools & Resources**: Ready-to-customize templates with authorization patterns

## Use Case: Hybrid Cloud-On-Premise Architecture

This boilerplate solves a common enterprise challenge:

**Scenario**: You have:
- ✅ Azure OpenAI running in the cloud
- ✅ Critical data systems on-premise or in private networks
- ✅ Need for fine-grained authorization to protect sensitive data
- ✅ Microsoft Entra ID as your existing identity provider

**Solution**: This architecture provides:
1. **Authentication** via Entra ID (cloud, shared with Azure OpenAI)
2. **Authorization** via Keycloak (on-premise, protects critical systems)
3. **Token Exchange** automatically bridges the two systems
4. **Role-Based Access Control** for granular permissions

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Prerequisites

- Python 3.10 or higher
- Azure subscription with App Registration permissions
- (Optional) Keycloak server for authorization
- (Optional) Docker and Docker Compose
- (Optional) Redis for production token storage

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to your project directory
cd qnagent

# Run the setup script
./scripts/setup.sh
```

The setup script will:
- Create a Python virtual environment
- Install all required dependencies
- Create a `.env` file from the template
- Set up the logs directory

### 2. Configure Azure Entra ID

#### Create an App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** > **App registrations**
3. Click **New registration**
4. Configure your application:
   - **Name**: Choose a descriptive name (e.g., "My FastMCP Server")
   - **Supported account types**: Choose based on your needs
   - **Redirect URI**:
     - Type: Web
     - URI: `http://localhost:8000/auth/callback` (for development)
     - For production: `https://your-domain.com/auth/callback`

#### Configure API Exposure

1. Go to **Expose an API** in your app registration
2. Set the **Application ID URI**: `api://{your-client-id}` (or custom)
3. Add scopes:
   - Click **Add a scope**
   - Scope name: `read`
   - Who can consent: Admins and users
   - Fill in display names and descriptions
   - Repeat for `write` scope (or your custom scopes)

#### Enable Access Token v2

1. Go to **Manifest**
2. Find `"requestedAccessTokenVersion"`
3. Change the value to `2`:
   ```json
   "api": {
       "requestedAccessTokenVersion": 2
   }
   ```
4. Save the manifest

#### Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and choose expiration
4. **Copy the secret value immediately** (you won't see it again)

#### Collect Your Credentials

From the **Overview** page, note:
- **Application (client) ID**
- **Directory (tenant) ID**
- **Client secret value** (from previous step)

### 3. Configure Environment Variables

Edit your `.env` file with your Azure credentials:

```bash
# Required Azure Configuration
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
AZURE_TENANT_ID=your-tenant-id-here

# Base URL (update for production)
AZURE_BASE_URL=http://localhost:8000

# Required scopes (must match what you created in Azure)
AZURE_REQUIRED_SCOPES=read,write
```

### 4. Generate Cryptographic Keys

```bash
python scripts/generate_keys.py
```

Add the generated keys to your `.env` file:

```bash
JWT_SIGNING_KEY=your-generated-jwt-key
STORAGE_ENCRYPTION_KEY=your-generated-fernet-key
```

### 5. Run the Server

```bash
# Using the run script
./scripts/run.sh

# Or directly with fastmcp CLI
fastmcp run src/server.py --transport http --port 8000

# Or with Python
python src/server.py
```

The server will start on `http://localhost:8000`

## Keycloak Integration (Optional)

For hybrid cloud-on-premise deployments, enable Keycloak authorization:

### Why Keycloak?

Keycloak provides **authorization** (what users can do) while Entra ID provides **authentication** (who users are). This separation is ideal when:

- Critical data systems are on-premise
- Fine-grained role-based access control is needed
- Compliance requires authorization to stay on-premise
- You need to manage permissions independently from cloud identity

### Quick Setup

1. **Configure Keycloak** (detailed guide: [docs/KEYCLOAK_SETUP.md](docs/KEYCLOAK_SETUP.md)):
   - Set up Keycloak server
   - Configure Entra ID as Identity Provider
   - Create client for MCP server
   - Enable OAuth2 Token Exchange
   - Define roles and permissions

2. **Enable in `.env`**:
   ```bash
   ENABLE_KEYCLOAK=true
   KEYCLOAK_SERVER_URL=https://your-keycloak-server.com
   KEYCLOAK_REALM=your-realm-name
   KEYCLOAK_CLIENT_ID=mcp-server
   KEYCLOAK_CLIENT_SECRET=your-client-secret
   ```

3. **Use authorization decorators** in your tools:
   ```python
   from src.auth.authorization import require_role, get_auth_context

   @mcp.tool()
   @require_role("data_reader")
   async def read_critical_data(query: str) -> dict:
       """Only users with 'data_reader' role can access this."""
       ctx = await get_auth_context()

       # ctx.roles contains Keycloak roles
       # ctx.email contains user email
       # ctx.keycloak_token contains full token with permissions

       return {"data": "..."}
   ```

4. **Available authorization patterns**:
   - `@require_role("role_name")` - Single role required
   - `@require_any_role(["admin", "supervisor"])` - Any of the roles
   - `@require_all_roles(["finance", "executive"])` - All roles required
   - `@require_resource_role("api", "writer")` - Client-specific roles
   - Programmatic checks with `AuthorizationHelper`

See [docs/KEYCLOAK_SETUP.md](docs/KEYCLOAK_SETUP.md) for complete setup instructions and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for architecture details.

## Project Structure

```
qnagent/
├── src/
│   ├── __init__.py
│   ├── server.py                    # Main server entry point
│   ├── config.py                    # Configuration management
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── provider.py              # Azure auth provider setup
│   │   ├── keycloak_client.py       # Keycloak client for token exchange
│   │   ├── token_exchange.py        # Token exchange service
│   │   └── authorization.py         # Authorization decorators & helpers
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── example_tools.py         # Example MCP tools
│   │   └── authorized_tools.py      # Tools with authorization checks
│   ├── resources/
│   │   ├── __init__.py
│   │   └── example_resources.py     # Example MCP resources
│   └── utils/
│       ├── __init__.py
│       └── logging_config.py        # Logging configuration
├── docs/
│   ├── AZURE_SETUP.md               # Azure Entra ID setup guide
│   ├── KEYCLOAK_SETUP.md            # Keycloak setup guide
│   └── ARCHITECTURE.md              # System architecture documentation
├── scripts/
│   ├── generate_keys.py             # Generate cryptographic keys
│   ├── setup.sh                     # Setup script
│   └── run.sh                       # Run server script
├── tests/                           # Test directory (add your tests)
├── config/                          # Additional config files
├── logs/                            # Log files (created automatically)
├── .env                             # Environment variables (create from .env.example)
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # Docker Compose configuration
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Development dependencies
├── pyproject.toml                   # Project metadata and tool config
├── LICENSE                          # MIT License
├── CONTRIBUTING.md                  # Development guide
└── README.md                        # This file
```

## Usage

### Testing Authentication

Use the FastMCP client to test authentication:

```python
from fastmcp import Client
import asyncio

async def main():
    async with Client("http://localhost:8000/mcp", auth="oauth") as client:
        print("✅ Authenticated with Azure!")

        # Call a tool
        result = await client.call_tool("get_current_user")
        print(f"User: {result}")

        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

if __name__ == "__main__":
    asyncio.run(main())
```

On first run, your browser will open for Azure authentication.

### Adding Custom Tools

Create your tools in `src/tools/` or extend `example_tools.py`:

```python
from fastmcp import FastMCP

def register_custom_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def my_custom_tool(param: str) -> dict:
        """
        Description of what your tool does.

        Args:
            param: Parameter description

        Returns:
            Result dictionary
        """
        # Your business logic here
        return {
            "success": True,
            "result": f"Processed: {param}"
        }
```

Register in `src/server.py`:

```python
from src.tools.custom_tools import register_custom_tools

# In create_server():
register_custom_tools(mcp)
```

### Adding Custom Resources

Create resources in `src/resources/` or extend `example_resources.py`:

```python
from fastmcp import FastMCP

def register_custom_resources(mcp: FastMCP) -> None:
    @mcp.resource("data://my-resource")
    async def get_my_data() -> str:
        """Provide custom data to the LLM."""
        return "Your data here"

    # Dynamic resources with parameters
    @mcp.resource("data://items/{item_id}")
    async def get_item(item_id: str) -> dict:
        """Get item by ID."""
        return {"id": item_id, "data": "..."}
```

### Accessing User Information

Within any tool handler, access the authenticated user's information:

```python
from src.auth.provider import get_user_info_from_token

@mcp.tool()
async def my_tool() -> dict:
    user_info = get_user_info_from_token()

    # user_info contains:
    # - azure_id: User's Azure ID
    # - email: Email address
    # - name: Display name
    # - tenant_id: Azure tenant ID
    # - oid: Object ID
    # ... and more

    return {"user": user_info["email"]}
```

## Docker Deployment

### Development with Docker Compose

```bash
# Start all services (MCP server + Redis)
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f mcp-server

# Stop services
docker-compose down
```

### Production Docker Build

```bash
# Build production image
docker build --target production -t fastmcp-server:latest .

# Run container
docker run -p 8000:8000 \
  --env-file .env \
  fastmcp-server:latest
```

## Production Deployment

### Environment Configuration

For production, ensure these settings in your `.env`:

```bash
ENVIRONMENT=production
DEBUG=false
AZURE_BASE_URL=https://your-domain.com
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_AUTH=true

# Required for production
JWT_SIGNING_KEY=your-secure-key
STORAGE_ENCRYPTION_KEY=your-fernet-key

# Redis for persistent token storage
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
STORAGE_ENCRYPTION_KEY=your-encryption-key
```

### Security Checklist

- [ ] Use HTTPS for `AZURE_BASE_URL` in production
- [ ] Set strong `JWT_SIGNING_KEY` (32+ random characters)
- [ ] Enable Redis with `STORAGE_ENCRYPTION_KEY` for token encryption
- [ ] Use specific `AZURE_TENANT_ID` (not "common" or "organizations")
- [ ] Rotate client secrets regularly
- [ ] Enable Redis password authentication
- [ ] Configure proper CORS origins (not `*`)
- [ ] Set up log aggregation
- [ ] Use a secrets manager (Azure Key Vault, AWS Secrets Manager, etc.)
- [ ] Enable monitoring and alerting
- [ ] Update Azure redirect URIs to production HTTPS endpoints

### Redis Setup

For production token storage with encryption:

```bash
# Install Redis dependencies
pip install key-value-py[redis] redis

# Configure in .env
REDIS_HOST=your-redis-host
REDIS_PORT=6379
STORAGE_ENCRYPTION_KEY=your-fernet-key
```

The server will automatically use Redis for token storage when configured.

## Integration with Azure OpenAI

This MCP server is designed to work with Azure OpenAI. Your Azure OpenAI instance can call the authenticated MCP server to access tools and resources.

### Configuration Steps

1. **Deploy your MCP server** with HTTPS and proper Azure authentication
2. **Configure Azure OpenAI** to use your MCP server endpoint
3. **Ensure network connectivity** between Azure OpenAI and your MCP server
4. **Use the same Azure tenant** for both services for seamless authentication

### Example Usage from Azure OpenAI

When Azure OpenAI calls your MCP server, it will:
1. Authenticate using Azure Entra ID OAuth2 flow
2. Access tools and resources you've defined
3. Execute tools with parameters provided by the LLM
4. Receive structured responses

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVER_NAME` | No | "FastMCP Boilerplate Server" | Server display name |
| `ENVIRONMENT` | No | development | Environment (development/staging/production) |
| `DEBUG` | No | false | Enable debug mode |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |
| `TRANSPORT` | No | http | Transport type (http/sse/stdio) |
| `LOG_LEVEL` | No | INFO | Logging level |
| `LOG_FORMAT` | No | json | Log format (json/text) |
| `ENABLE_AUTH` | No | true | Enable authentication |
| `AZURE_CLIENT_ID` | Yes* | - | Azure App Registration Client ID |
| `AZURE_CLIENT_SECRET` | Yes* | - | Azure Client Secret |
| `AZURE_TENANT_ID` | Yes* | - | Azure Tenant ID |
| `AZURE_BASE_URL` | No | http://localhost:8000 | Server public URL |
| `AZURE_REQUIRED_SCOPES` | No | read,write | Required OAuth scopes |
| `JWT_SIGNING_KEY` | No** | - | JWT signing key for sessions |
| `REDIS_HOST` | No | - | Redis host for token storage |
| `REDIS_PORT` | No | 6379 | Redis port |
| `STORAGE_ENCRYPTION_KEY` | Yes*** | - | Fernet key for token encryption |

\* Required if `ENABLE_AUTH=true`
\** Recommended for production
\*** Required if using Redis

## Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Code Quality Tools

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_server.py
```

### Project Configuration

The project uses `pyproject.toml` for configuration. Key settings:
- **black**: Line length 120, Python 3.10+
- **isort**: Black-compatible profile
- **ruff**: E, W, F, I, B, C4, UP rules enabled
- **mypy**: Strict optional, warn on unused ignores
- **pytest**: Coverage reporting, async support

## Troubleshooting

### Authentication Errors

**Problem**: "Authentication failed" or "Invalid token"

**Solutions**:
- Verify Azure credentials in `.env` are correct
- Ensure `requestedAccessTokenVersion: 2` in Azure app manifest
- Check redirect URI matches exactly (including trailing slash)
- Verify scopes exist in Azure app registration

### Port Already in Use

**Problem**: "Address already in use" error

**Solutions**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
PORT=8001 ./scripts/run.sh
```

### Redis Connection Errors

**Problem**: "Cannot connect to Redis"

**Solutions**:
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Check Redis host and port in `.env`
- For Docker: Ensure services are on the same network

### Import Errors

**Problem**: "ModuleNotFoundError"

**Solutions**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Or run setup again
./scripts/setup.sh
```

## Advanced Topics

### Custom Configuration

Create custom config files in `config/` directory:

```python
# In src/config.py, extend ServerConfig class
from pathlib import Path
import yaml

def load_custom_config():
    config_path = Path("config/custom.yaml")
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}
```

### Multi-Tenant Support

For multi-tenant scenarios:

```python
# In your tools
from src.auth.provider import get_user_info_from_token

@mcp.tool()
async def tenant_aware_tool(data: str) -> dict:
    user_info = get_user_info_from_token()
    tenant_id = user_info["tenant_id"]

    # Use tenant_id to scope data access
    # ... your business logic
```

### Monitoring and Observability

Add application insights or custom metrics:

```python
# src/utils/metrics.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def track_tool_execution(tool_name: str, duration: float, success: bool):
    logger.info(
        "Tool execution",
        extra={
            "tool": tool_name,
            "duration_ms": duration * 1000,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

## Contributing

This is a boilerplate template. Customize it for your needs:

1. **Fork or clone** this repository
2. **Implement your business logic** in tools and resources
3. **Update configuration** as needed
4. **Add tests** for your custom code
5. **Document your changes** in this README

## Resources

- [FastMCP Documentation](https://gofastmcp.com)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [Azure Entra ID Documentation](https://learn.microsoft.com/en-us/entra/identity/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

## License

MIT License - feel free to use this boilerplate for your projects.

## Support

For issues related to:
- **FastMCP**: [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- **Azure Entra ID**: [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/)
- **This boilerplate**: Open an issue in your repository

## Changelog

### Version 1.0.0
- Initial boilerplate release
- Azure Entra ID authentication
- Example tools and resources
- Docker support
- Comprehensive configuration management
- Production-ready logging and error handling

---

**Built with FastMCP** 🚀
