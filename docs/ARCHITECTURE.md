# Architecture Documentation

## Overview

This MCP server implements a **hybrid cloud-on-premise architecture** with separated authentication and authorization responsibilities:

- **Authentication**: Microsoft Entra ID (cloud-based, shared with Azure OpenAI)
- **Authorization**: Keycloak (on-premise or private, protects critical infrastructure)
- **Bridge**: OAuth2 Token Exchange pattern

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Azure Cloud                                   │
│                                                                           │
│  ┌─────────────────┐              ┌──────────────────┐                   │
│  │  Azure OpenAI   │              │  Microsoft       │                   │
│  │                 │              │  Entra ID        │                   │
│  │  - GPT-4        │◄─────────────┤                  │                   │
│  │  - Embeddings   │ Authenticate │  - SSO           │                   │
│  │  - Assistants   │              │  - OAuth2        │                   │
│  └────────┬────────┘              │  - User Store    │                   │
│           │                        └────────┬─────────┘                   │
│           │                                 │                             │
└───────────┼─────────────────────────────────┼─────────────────────────────┘
            │                                 │
            │ MCP Protocol                    │ OAuth2
            │ (Entra ID Token)                │ (Token Validation)
            │                                 │
┌───────────▼─────────────────────────────────▼─────────────────────────────┐
│                         MCP Server (This Application)                     │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                      Authentication Layer                            │ │
│  │                                                                      │ │
│  │  ┌──────────────┐          ┌─────────────────┐                      │ │
│  │  │  FastMCP     │          │  Azure Auth     │                      │ │
│  │  │  Auth        │◄─────────┤  Provider       │                      │ │
│  │  │  Middleware  │          │                 │                      │ │
│  │  └──────┬───────┘          └─────────────────┘                      │ │
│  └─────────┼──────────────────────────────────────────────────────────────┘ │
│            │                                                            │
│            │ Entra ID Token                                             │
│            │                                                            │
│  ┌─────────▼──────────────────────────────────────────────────────────┐ │
│  │                   Token Exchange Service                            │ │
│  │                                                                     │ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │ │
│  │  │  1. Receive Entra ID Token                                    │ │ │
│  │  │  2. Validate token signature                                  │ │ │
│  │  │  3. Exchange for Keycloak token (OAuth2 Token Exchange)       │ │ │
│  │  │  4. Cache Keycloak token                                      │ │ │
│  │  │  5. Create unified AuthContext                                │ │ │
│  │  └───────────────────────────────────────────────────────────────┘ │ │
│  └─────────┬────────────────────────────────────────────────────────────┘ │
│            │                                                            │
│            │ Keycloak Token (with roles/permissions)                   │
│            │                                                            │
│  ┌─────────▼──────────────────────────────────────────────────────────┐ │
│  │                   Authorization Layer                              │ │
│  │                                                                     │ │
│  │  ┌────────────────┐  ┌─────────────────┐  ┌───────────────────┐   │ │
│  │  │  @require_role │  │ @require_any    │  │ @require_resource │   │ │
│  │  │                │  │  _role          │  │  _role            │   │ │
│  │  └────────────────┘  └─────────────────┘  └───────────────────┘   │ │
│  │                                                                     │ │
│  │  Role-based access control using Keycloak roles                    │ │
│  └─────────┬────────────────────────────────────────────────────────────┘ │
│            │                                                            │
│            │ Authorized                                                  │
│            │                                                            │
│  ┌─────────▼──────────────────────────────────────────────────────────┐ │
│  │                         MCP Tools                                   │ │
│  │                                                                     │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │ │
│  │  │  Protected  │  │  Critical    │  │  Conditional Access      │  │ │
│  │  │  Data       │  │  Operations  │  │  Based on Sensitivity    │  │ │
│  │  │  Reader     │  │              │  │                          │  │ │
│  │  └─────────────┘  └──────────────┘  └──────────────────────────┘  │ │
│  └─────────┬────────────────────────────────────────────────────────────┘ │
└────────────┼──────────────────────────────────────────────────────────────┘
             │
             │ Internal API Calls
             │ (with authorization context)
             │
┌────────────▼──────────────────────────────────────────────────────────────┐
│                      On-Premise / Private Network                         │
│                                                                           │
│  ┌──────────────────┐            ┌─────────────────────────────────────┐ │
│  │   Keycloak       │            │   Critical Infrastructure           │ │
│  │                  │            │                                     │ │
│  │  - User/Role     │            │   ┌───────────┐    ┌────────────┐  │ │
│  │    Federation    │            │   │ Database  │    │  Legacy    │  │ │
│  │  - Token         │            │   │ Systems   │    │  Systems   │  │ │
│  │    Exchange      │            │   └───────────┘    └────────────┘  │ │
│  │  - Fine-grained  │            │                                     │ │
│  │    Permissions   │            │   ┌───────────┐    ┌────────────┐  │ │
│  │  - Audit Logs    │            │   │ Financial │    │  Customer  │  │ │
│  └──────────────────┘            │   │ Data      │    │  Data      │  │ │
│                                   │   └───────────┘    └────────────┘  │ │
│                                   └─────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

## Authentication Flow

### 1. Initial Authentication (Azure OpenAI → MCP Server)

```sequence
Azure OpenAI -> Entra ID: Authenticate user
Entra ID -> Azure OpenAI: Entra ID access token
Azure OpenAI -> MCP Server: MCP request with Entra ID token
MCP Server -> MCP Server: Validate Entra ID token
```

### 2. Token Exchange (MCP Server → Keycloak)

```sequence
MCP Server -> Token Exchange Service: Exchange Entra ID token
Token Exchange Service -> Keycloak: OAuth2 Token Exchange request
Keycloak -> Keycloak: Validate Entra ID token
Keycloak -> Keycloak: Map user to local user
Keycloak -> Keycloak: Attach roles and permissions
Keycloak -> Token Exchange Service: Keycloak access token (with roles)
Token Exchange Service -> Token Cache: Cache token
Token Exchange Service -> MCP Server: AuthContext (Entra ID + Keycloak)
```

### 3. Authorization Check

```sequence
MCP Server -> Tool Handler: Execute tool
Tool Handler -> Auth Decorator: Check authorization
Auth Decorator -> AuthContext: Get user roles
Auth Decorator -> Auth Decorator: Verify required roles
Auth Decorator -> Tool Handler: Authorized / Denied
Tool Handler -> Critical System: Access if authorized
```

## Component Architecture

### Core Components

#### 1. FastMCP Server (`src/server.py`)
- Entry point
- Initializes authentication and authorization
- Registers tools and resources
- Handles server lifecycle

#### 2. Configuration Management (`src/config.py`)
- Environment-based configuration
- Validation for production
- Supports both Entra ID and Keycloak config
- Type-safe dataclasses

#### 3. Authentication Layer (`src/auth/provider.py`)
- Azure Entra ID provider setup
- Token validation
- User info extraction

#### 4. Keycloak Client (`src/auth/keycloak_client.py`)
- OAuth2 token exchange
- Token refresh
- Role/permission extraction
- Token validation

#### 5. Token Exchange Service (`src/auth/token_exchange.py`)
- Orchestrates Entra ID ↔ Keycloak exchange
- Token caching
- Unified AuthContext creation
- Lifecycle management

#### 6. Authorization Layer (`src/auth/authorization.py`)
- Role-based decorators (`@require_role`, etc.)
- Permission checking
- Custom authorization logic
- Error handling

#### 7. Tools (`src/tools/`)
- `example_tools.py`: Basic tools without authorization
- `authorized_tools.py`: Tools with authorization checks
- Demonstrates various authorization patterns

#### 8. Resources (`src/resources/`)
- Static and dynamic resources
- Configuration and documentation endpoints
- Template URI patterns

## Data Flow

### Successful Request Flow

```
1. Azure OpenAI makes MCP request
   ├─ Includes Entra ID access token
   └─ Contains user identity information

2. MCP Server receives request
   ├─ FastMCP validates Entra ID token
   └─ Extracts user claims (email, OID, etc.)

3. Token Exchange (if Keycloak enabled)
   ├─ Check token cache for existing Keycloak token
   ├─ If not cached or expired:
   │  ├─ Call Keycloak token exchange endpoint
   │  ├─ Keycloak validates Entra ID token
   │  ├─ Keycloak maps user (by email/OID)
   │  ├─ Keycloak attaches roles from user's role mappings
   │  └─ Returns Keycloak access token
   └─ Cache Keycloak token

4. Create AuthContext
   ├─ Entra ID user info
   ├─ Keycloak user info
   ├─ Combined roles list
   └─ Token metadata

5. Tool execution
   ├─ Authorization decorator checks required roles
   ├─ Compare required vs. user's roles
   ├─ If authorized: execute tool logic
   └─ If denied: return authorization error

6. Critical system access
   ├─ Use Keycloak roles for fine-grained access
   ├─ Audit log the access attempt
   └─ Return results to Azure OpenAI
```

## Security Architecture

### Defense in Depth

1. **Network Layer**
   - Keycloak not publicly accessible
   - MCP server in DMZ or private network
   - Firewall rules restrict access

2. **Authentication Layer**
   - Entra ID provides cryptographic authentication
   - Token signature validation
   - Token expiry enforcement

3. **Authorization Layer**
   - Keycloak provides fine-grained authorization
   - Role-based access control (RBAC)
   - Resource-specific permissions
   - Attribute-based access control (ABAC) possible

4. **Application Layer**
   - Input validation
   - Rate limiting
   - Audit logging
   - Error handling without information leakage

5. **Data Layer**
   - Encrypted token storage
   - Encrypted communication (TLS)
   - Minimal data exposure

### Token Security

```
┌─────────────────────────────────────────────────────┐
│                 Entra ID Token                      │
│                                                     │
│  - Short-lived (1 hour typical)                     │
│  - Signed by Microsoft                              │
│  - Contains: user ID, email, tenant                 │
│  - No authorization info (just authentication)      │
└─────────────────────────────────────────────────────┘
                       │
                       │ Token Exchange
                       ▼
┌─────────────────────────────────────────────────────┐
│               Keycloak Token                        │
│                                                     │
│  - Short-lived (5-15 minutes typical)               │
│  - Signed by Keycloak                               │
│  - Contains: user ID, roles, permissions            │
│  - Resource access mappings                         │
│  - Can be refreshed without re-authentication       │
└─────────────────────────────────────────────────────┘
```

### Principle of Least Privilege

- Users assigned minimum necessary roles
- Roles mapped to specific capabilities
- Client-specific roles for system access
- Regular audits of role assignments

## Deployment Architecture

### Development Setup

```
┌──────────────────────────────────────────┐
│  Developer Machine                       │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  MCP Server (localhost:8000)       │  │
│  │  - ENABLE_KEYCLOAK=false          │  │
│  │  - Uses mock data                  │  │
│  └────────────────────────────────────┘  │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  Keycloak (Docker)                 │  │
│  │  - localhost:8080                  │  │
│  │  - Self-signed cert OK             │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

### Production Setup

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure Cloud                             │
│                                                             │
│  ┌──────────────┐         ┌─────────────────┐              │
│  │ Azure OpenAI │────────►│  Entra ID       │              │
│  └──────┬───────┘         └─────────────────┘              │
│         │                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ HTTPS (Public Internet or VPN)
          │
┌─────────▼───────────────────────────────────────────────────┐
│                  DMZ / Edge Network                         │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  Load Balancer / Reverse Proxy               │          │
│  │  - SSL Termination                            │          │
│  │  - Rate Limiting                              │          │
│  │  - DDoS Protection                            │          │
│  └────────┬─────────────────────────────────────┘          │
└───────────┼─────────────────────────────────────────────────┘
            │
            │ Internal Network
            │
┌───────────▼─────────────────────────────────────────────────┐
│              Application Network (Private)                  │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  MCP Server Cluster                           │          │
│  │  - Kubernetes / Docker Swarm                  │          │
│  │  - Auto-scaling                               │          │
│  │  - Health checks                              │          │
│  └────────┬────────┬────────────────────────────┘          │
│           │        │                                        │
│  ┌────────▼──────┐ │  ┌──────────────┐                     │
│  │  Redis        │ │  │  Monitoring   │                    │
│  │  (Token Cache)│ │  │  Logging      │                    │
│  └───────────────┘ │  └──────────────┘                     │
│                    │                                        │
└────────────────────┼────────────────────────────────────────┘
                     │
                     │ Internal Network
                     │
┌────────────────────▼────────────────────────────────────────┐
│            Data Center (On-Premise/Private)                 │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────────┐          │
│  │  Keycloak        │    │  Critical Systems     │          │
│  │  - HA Setup      │    │                       │          │
│  │  - PostgreSQL DB │    │  - Databases          │          │
│  │  - Backup/DR     │    │  - Legacy Systems     │          │
│  └──────────────────┘    │  - File Servers       │          │
│                          │  - Financial Systems  │          │
│                          └──────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling

- MCP servers are stateless (except token cache)
- Use Redis for distributed token caching
- Load balancer distributes requests
- Auto-scaling based on CPU/memory/request rate

### Token Caching Strategy

- **In-Memory**: Development, single server
- **Redis**: Production, multiple servers
- **TTL**: Match or slightly exceed Keycloak token expiry
- **Refresh**: Automatic when token nears expiry

### Performance Optimization

1. **Token Exchange Caching**
   - Cache Keycloak tokens to avoid repeated exchanges
   - Typical cache hit rate: 95%+
   - Reduces latency from ~100ms to <1ms

2. **Connection Pooling**
   - HTTP connection pool to Keycloak
   - Reuse connections for better performance

3. **Async Operations**
   - All I/O operations are async
   - Non-blocking token exchange
   - Concurrent request handling

## Monitoring and Observability

### Key Metrics

1. **Authentication Metrics**
   - Entra ID token validation success rate
   - Token validation latency

2. **Authorization Metrics**
   - Token exchange success rate
   - Token exchange latency
   - Cache hit rate
   - Authorization check latency

3. **Business Metrics**
   - Tool execution count by role
   - Failed authorization attempts
   - User activity patterns

### Logging Strategy

```python
{
  "timestamp": "2025-01-05T10:30:00Z",
  "level": "INFO",
  "event": "token_exchange_success",
  "user_email": "user@example.com",
  "entra_user_id": "oid-123",
  "keycloak_user_id": "kc-456",
  "roles": ["data_reader", "analyst"],
  "duration_ms": 95
}
```

### Alerting

- Failed token exchanges > 5% in 5min
- Authorization failures > threshold
- Keycloak connectivity issues
- Unusual role assignment patterns

## Disaster Recovery

### Backup Strategy

1. **Keycloak Database**
   - Regular PostgreSQL backups
   - Point-in-time recovery
   - Replicate to secondary site

2. **Configuration**
   - Version control for all config
   - Automated deployment
   - Infrastructure as Code

3. **Secrets**
   - Azure Key Vault for cloud secrets
   - On-premise secret manager
   - Regular rotation

### Failover Scenarios

1. **Keycloak Failure**
   - Option 1: Fail closed (deny all)
   - Option 2: Cached tokens continue to work
   - Option 3: Fallback to read-only mode

2. **Entra ID Outage**
   - Existing sessions continue (cached tokens)
   - New sessions fail
   - Monitor Microsoft status

3. **Network Partition**
   - Cloud-to-on-premise link fails
   - Graceful degradation
   - Alert operations team

## Future Enhancements

1. **Fine-grained Permissions**
   - Attribute-based access control (ABAC)
   - Policy-based authorization
   - Dynamic policy evaluation

2. **Advanced Caching**
   - Permission caching
   - User profile caching
   - Distributed cache with failover

3. **Multi-Region**
   - Keycloak replication across regions
   - Geo-distributed MCP servers
   - Latency optimization

4. **Zero Trust Architecture**
   - Mutual TLS
   - Continuous verification
   - Micro-segmentation

## References

- [OAuth 2.0 Token Exchange (RFC 8693)](https://datatracker.ietf.org/doc/html/rfc8693)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [FastMCP Documentation](https://gofastmcp.com)
- [Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity/)
- [Model Context Protocol](https://modelcontextprotocol.io)
