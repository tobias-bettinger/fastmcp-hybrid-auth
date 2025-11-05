# Keycloak Setup Guide for Entra ID Integration

This guide walks you through configuring Keycloak to work with Azure Entra ID for authentication and authorization. This setup enables the **authorization handover** pattern where:

1. **Entra ID** handles authentication (Azure OpenAI and cloud services)
2. **Keycloak** handles authorization (on-premise critical infrastructure)
3. **MCP Server** bridges the two via OAuth2 Token Exchange

## Architecture Overview

```
┌─────────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│  Azure      │          │  MCP Server  │          │  Keycloak    │          │  On-Premise  │
│  OpenAI     │  Entra   │              │  Token   │              │  Authz   │  Critical    │
│             │  ──────► │  Validates   │  ───────►│  Provides    │  ───────►│  Data        │
│             │   ID     │  & Exchanges │  Exchange│  Roles       │  Check   │  Systems     │
└─────────────┘          └──────────────┘          └──────────────┘          └──────────────┘
```

**Flow:**
1. Azure OpenAI authenticates user with Entra ID → gets Entra ID token
2. MCP Server receives Entra ID token, validates it
3. MCP Server exchanges Entra ID token for Keycloak token (OAuth2 Token Exchange)
4. Keycloak token contains roles/permissions for on-premise systems
5. MCP Server uses Keycloak roles to authorize access to critical operations

## Prerequisites

- Keycloak server (22.0+recommended) - on-premise or cloud
- Azure Entra ID configured (see [AZURE_SETUP.md](AZURE_SETUP.md))
- Admin access to both systems
- Network connectivity between MCP server and Keycloak

## Part 1: Configure Azure Entra ID as Identity Provider in Keycloak

### Step 1: Create Realm in Keycloak

1. **Log into Keycloak Admin Console**
   - Navigate to `https://your-keycloak-server.com`
   - Sign in with admin credentials

2. **Create a new realm** (or use existing)
   - Hover over realm selector in top-left
   - Click "Create Realm"
   - **Name**: `your-realm-name` (e.g., `mcp-production`)
   - **Enabled**: ON
   - Click "Create"

### Step 2: Configure Entra ID as Identity Provider

1. **Navigate to Identity Providers**
   - In your realm, click "Identity providers" in the left sidebar

2. **Add Microsoft Provider**
   - Click "Add provider"
   - Select "Microsoft"

3. **Configure Microsoft Identity Provider**

   **Redirect URI**: Copy this value (you'll need it for Azure)
   ```
   https://your-keycloak-server.com/realms/your-realm-name/broker/microsoft/endpoint
   ```

   **Settings:**
   - **Alias**: `microsoft` (or custom name)
   - **Display name**: Azure Entra ID
   - **Enabled**: ON
   - **Store tokens**: ON (important!)
   - **Stored tokens readable**: ON
   - **Trust email**: ON
   - **First login flow**: first broker login
   - **Sync mode**: IMPORT

4. **Add Azure credentials** (from Azure Portal):

   - **Client ID**: Your Entra ID Application (client) ID
   - **Client Secret**: Your Entra ID client secret
   - **Tenant ID**: Your Entra ID Directory (tenant) ID

   **Advanced Settings:**
   - **Default scopes**: `openid profile email`
   - **Prompt**: (leave empty or `consent` for first-time users)

5. **Click "Add"**

### Step 3: Configure Azure App Registration

1. **Add Keycloak Redirect URI** in Azure Portal:
   - Go to your App Registration
   - Navigate to **Authentication**
   - Click "+ Add a URI"
   - Add: `https://your-keycloak-server.com/realms/your-realm-name/broker/microsoft/endpoint`
   - **Must be HTTPS in production**

2. **Verify token version** is still set to v2 in manifest

### Step 4: Test Identity Provider Link

1. **Test the connection**:
   - In Keycloak, open a new incognito/private browser window
   - Navigate to: `https://your-keycloak-server.com/realms/your-realm-name/account`
   - You should see "Azure Entra ID" or "Microsoft" as login option
   - Click it - should redirect to Microsoft login
   - Sign in with Azure credentials
   - Should redirect back to Keycloak

2. **Verify user import**:
   - In Keycloak Admin Console, go to **Users**
   - You should see your test user imported
   - Check that user has email and other attributes

## Part 2: Configure Client for MCP Server

### Step 1: Create Keycloak Client

1. **Navigate to Clients**
   - In your realm, click "Clients" in the left sidebar

2. **Create new client**:
   - Click "Create client"

   **General Settings:**
   - **Client type**: OpenID Connect
   - **Client ID**: `mcp-server` (or your preferred name)
   - Click "Next"

   **Capability config:**
   - **Client authentication**: ON (for confidential client)
   - **Authorization**: ON
   - **Standard flow**: ON
   - **Direct access grants**: ON
   - **Service accounts roles**: ON
   - Click "Next"

   **Login settings:**
   - **Root URL**: `https://your-mcp-server.com`
   - **Valid redirect URIs**: `https://your-mcp-server.com/*`
   - **Web origins**: `https://your-mcp-server.com`
   - Click "Save"

3. **Get Client Credentials**:
   - Go to the **Credentials** tab
   - Copy the **Client Secret**
   - Save this for your `.env` file

### Step 2: Configure Token Exchange

This is the **critical part** that enables the Entra ID → Keycloak token exchange.

1. **Enable Token Exchange in Keycloak**:

   Keycloak 22+ has token exchange enabled by default. For older versions:
   - Edit `standalone.xml` or `standalone-ha.xml`
   - Add under `<subsystem xmlns="urn:jboss:domain:keycloak-server:1.1">`:
   ```xml
   <spi name="tokenExchange">
       <provider name="token-exchange" enabled="true"/>
   </spi>
   ```

2. **Create Token Exchange Permission**:

   This allows the Microsoft/Azure IDP tokens to be exchanged.

   **Via Admin Console:**
   - Go to your **mcp-server** client
   - Navigate to **Permissions** tab
   - Enable "Permissions enabled"
   - Go to **Service Account Roles** tab
   - Click "Assign role"
   - Filter by "realm-management"
   - Add: `view-identity-providers`, `view-users`

   **Via Keycloak Admin REST API** (recommended for automation):

   ```bash
   # Get admin token
   TOKEN=$(curl -X POST "https://your-keycloak-server.com/realms/master/protocol/openid-connect/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin" \
     -d "password=your-admin-password" \
     -d "grant_type=password" \
     -d "client_id=admin-cli" \
     | jq -r '.access_token')

   # Allow token exchange from microsoft IDP
   curl -X POST \
     "https://your-keycloak-server.com/admin/realms/your-realm-name/clients/{mcp-server-client-uuid}/token-exchange-permission/idps/microsoft" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"enabled": true}'
   ```

3. **Configure Identity Provider Mappers** (optional but recommended):

   This maps Entra ID attributes to Keycloak user attributes.

   - In **Identity Providers** > **microsoft** > **Mappers**
   - Add mappers for:
     - `email` → User Attribute `email`
     - `name` → User Attribute `full_name`
     - `preferred_username` → Username
     - `oid` (Object ID) → User Attribute `azure_oid`

## Part 3: Define Roles and Permissions

Now configure the roles that will authorize access to your on-premise systems.

### Step 1: Create Realm Roles

1. **Navigate to Realm roles**:
   - Click "Realm roles" in the left sidebar

2. **Create roles** for your use cases:
   ```
   - data_reader        (read-only access to critical data)
   - data_writer        (write access to critical data)
   - admin              (administrative access)
   - supervisor         (supervisory functions)
   - data_manager       (data management operations)
   - analyst            (analytics and reporting)
   - employee           (general employee access)
   - executive_level    (executive access)
   - finance_access     (financial data access)
   - security_clearance (security-sensitive operations)
   ```

3. **For each role**:
   - Click "Create role"
   - **Role name**: (from list above)
   - **Description**: Clear description of what this role allows
   - Click "Save"

### Step 2: Create Client Roles (for specific systems)

Client roles represent permissions for specific applications/systems.

1. **Navigate to your mcp-server client**:
   - Clients → mcp-server → Roles tab

2. **Create client role**:
   - Example: `critical-data-api`
   - Click "Create role"
   - **Role name**: `reader`
   - Click "Save"
   - Repeat for: `writer`, `admin`

3. **Repeat for other on-premise systems**:
   - Create client for each critical system
   - Define appropriate roles

### Step 3: Assign Roles to Users

1. **Navigate to Users**:
   - Click "Users" in the left sidebar
   - Find your test user (imported from Azure)

2. **Assign roles**:
   - Click on the user
   - Go to **Role mapping** tab
   - Click "Assign role"
   - Filter by "realm roles" and assign appropriate roles
   - Filter by client roles and assign as needed

3. **Set up Default Roles** (optional):
   - Realm settings → User registration → Default roles
   - Add roles that every user should have by default

### Step 4: Map Azure Groups to Keycloak Roles (Optional)

If you manage groups in Entra ID, map them to Keycloak roles:

1. **In Azure Entra ID**:
   - Ensure groups are included in token claims
   - App registration → Token configuration → Add groups claim

2. **In Keycloak**:
   - Identity Providers → microsoft → Mappers
   - Create new mapper:
     - **Name**: Azure Group Mapper
     - **Sync mode override**: IMPORT
     - **Mapper type**: Attribute Importer
     - **Claim**: groups
     - **User Attribute Name**: azure_groups

3. **Create Role Mapping Script** (Keycloak admin):
   - Use Keycloak Event Listeners or custom mappers
   - Map specific Azure group IDs to Keycloak roles

## Part 4: Configure MCP Server

### Step 1: Update Environment Variables

Edit your `.env` file:

```bash
# Enable Keycloak
ENABLE_KEYCLOAK=true

# Keycloak Configuration
KEYCLOAK_SERVER_URL=https://your-keycloak-server.com
KEYCLOAK_REALM=your-realm-name
KEYCLOAK_CLIENT_ID=mcp-server
KEYCLOAK_CLIENT_SECRET=your-client-secret-from-keycloak

# Optional: Set to false for dev with self-signed certs
KEYCLOAK_VERIFY_SSL=true

# Token exchange enabled
KEYCLOAK_ENABLE_TOKEN_EXCHANGE=true
KEYCLOAK_CACHE_TOKENS=true
```

### Step 2: Test the Integration

Create a test script:

```python
# test_keycloak.py
import asyncio
from src.auth.keycloak_client import KeycloakClient
from src.config import get_config

async def test_token_exchange():
    """Test Entra ID to Keycloak token exchange."""
    config = get_config()

    # Initialize Keycloak client
    kc_client = KeycloakClient(
        server_url=config.keycloak.server_url,
        realm=config.keycloak.realm,
        client_id=config.keycloak.client_id,
        client_secret=config.keycloak.client_secret,
    )

    # Replace with actual Entra ID token
    entra_token = "your-entra-id-access-token"

    # Exchange token
    try:
        keycloak_token = await kc_client.exchange_token(entra_token)
        print("✅ Token exchange successful!")
        print(f"User: {keycloak_token.preferred_username}")
        print(f"Roles: {keycloak_token.roles}")
        print(f"Expires at: {keycloak_token.expires_at}")
    except Exception as e:
        print(f"❌ Token exchange failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_token_exchange())
```

Run the test:
```bash
python test_keycloak.py
```

## Part 5: Production Deployment

### Security Checklist

- [ ] Keycloak uses HTTPS with valid SSL certificate
- [ ] Keycloak is not publicly accessible (use VPN or firewall)
- [ ] Client secrets are stored in Azure Key Vault or similar
- [ ] Token exchange is restricted to specific clients
- [ ] Regular security audits of role assignments
- [ ] Logging enabled for all authentication/authorization events
- [ ] Rate limiting configured
- [ ] Session timeouts configured appropriately

### Network Architecture

```
┌─────────────────┐
│   Azure Cloud   │
│                 │
│  ┌───────────┐  │
│  │  Entra ID │  │
│  └─────┬─────┘  │
│        │ HTTPS  │
└────────┼────────┘
         │
         │ Internet/VPN
         │
┌────────┼────────────────┐
│   On-Premise / Private  │
│        │                │
│  ┌─────▼──────┐         │
│  │ MCP Server │         │
│  └─────┬──────┘         │
│        │ Internal       │
│  ┌─────▼──────┐         │
│  │  Keycloak  │         │
│  └─────┬──────┘         │
│        │ Internal       │
│  ┌─────▼──────┐         │
│  │ Critical   │         │
│  │ Data       │         │
│  └────────────┘         │
└─────────────────────────┘
```

### Monitoring and Logging

1. **Enable Keycloak Event Logging**:
   - Realm settings → Events
   - Enable "Save events"
   - Configure event listeners

2. **Monitor Token Exchange**:
   - Track successful/failed exchanges
   - Alert on unusual patterns
   - Monitor token expiry and refresh

3. **Audit Role Changes**:
   - Log all role assignments/removals
   - Regular review of user permissions

## Troubleshooting

### Issue: Token Exchange Fails with "Exchange not allowed"

**Solution**:
- Verify token exchange permission is set for microsoft IDP
- Check that service account has `view-identity-providers` role
- Ensure token exchange SPI is enabled in Keycloak

### Issue: "Invalid issuer" Error

**Solution**:
- Check that Entra ID token is v2 format
- Verify `requestedAccessTokenVersion: 2` in Azure manifest
- Ensure token is not expired

### Issue: User Roles Not Appearing in Keycloak Token

**Solution**:
- Check role mappings in User → Role mapping
- Verify client scopes include roles
- Check that "Full scope allowed" is enabled on client (or specific scope mappings are correct)

### Issue: "Subject token type not supported"

**Solution**:
- Ensure using correct subject_token_type:
  `urn:ietf:params:oauth:token-type:access_token`
- Verify Keycloak version supports token exchange (18.0+)

### Issue: Cannot Connect to Keycloak from MCP Server

**Solution**:
- Check network connectivity: `curl https://keycloak-server.com`
- Verify firewall rules
- For self-signed certs: Set `KEYCLOAK_VERIFY_SSL=false` (dev only!)
- Check Keycloak is running: `systemctl status keycloak`

## Testing Authorization

Once everything is configured, test with MCP tools:

```python
# In a tool handler
from src.auth.authorization import require_role, get_auth_context

@mcp.tool()
@require_role("data_reader")
async def read_critical_data(query: str) -> dict:
    """Only users with data_reader role can execute this."""
    ctx = await get_auth_context()

    # ctx contains both Entra ID and Keycloak information
    print(f"User: {ctx.email}")
    print(f"Roles: {ctx.roles}")

    # Access your critical on-premise system
    return {"data": "..."}
```

## Alternative Approaches

If OAuth2 Token Exchange doesn't work for your environment:

### Option 1: User Attribute Mapping

- Map Entra ID user to Keycloak user by email/OID
- Look up roles in Keycloak based on mapped user
- Simpler but less secure (no cryptographic token binding)

### Option 2: Keycloak as Sole IdP

- Use Keycloak for both authentication AND authorization
- Federate Keycloak to Entra ID (same setup as above)
- Azure OpenAI authenticates through Keycloak directly
- Requires Azure OpenAI to support custom OIDC provider

### Option 3: Custom Authorization Service

- Build custom service that:
  1. Validates Entra ID token
  2. Looks up user in database
  3. Returns roles/permissions
- More control but more maintenance

## Recommended Approach

The **OAuth2 Token Exchange** approach (documented here) is recommended because:

✅ Industry standard (RFC 8693)
✅ Cryptographically secure
✅ Keeps Entra ID as single source of authentication
✅ Keycloak provides robust authorization
✅ Clear separation of concerns
✅ Scales well

## Resources

- [Keycloak Token Exchange Documentation](https://www.keycloak.org/docs/latest/securing_apps/index.html#_token-exchange)
- [RFC 8693 - OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693)
- [Keycloak Identity Brokering](https://www.keycloak.org/docs/latest/server_admin/#_identity_broker)
- [Azure Entra ID Documentation](https://learn.microsoft.com/en-us/entra/identity/)

## Support

For issues with this setup:
- Keycloak: Check Keycloak server logs in `standalone/log/`
- Azure: Azure Portal → App registrations → Sign-in logs
- MCP Server: Check application logs with `LOG_LEVEL=DEBUG`
