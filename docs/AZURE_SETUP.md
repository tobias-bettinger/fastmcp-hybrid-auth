# Azure Entra ID Setup Guide

This guide walks you through setting up Microsoft Entra ID (formerly Azure AD) authentication for your FastMCP server.

## Prerequisites

- Azure subscription
- Permission to create App Registrations in your Azure tenant
- Access to Azure Portal

## Step 1: Create App Registration

1. **Navigate to Azure Portal**
   - Go to [https://portal.azure.com](https://portal.azure.com)
   - Sign in with your Azure account

2. **Access App Registrations**
   - Search for "Microsoft Entra ID" in the top search bar
   - Click on "Microsoft Entra ID"
   - In the left sidebar, click "App registrations"

3. **Create New Registration**
   - Click "+ New registration" at the top
   - Fill in the application details:

   **Name**: Choose a descriptive name
   ```
   Example: "My FastMCP Server" or "Production MCP API"
   ```

   **Supported account types**: Choose one:
   - **Single tenant**: Only your organization (most secure, recommended)
   - **Multitenant**: Any Azure AD organization
   - **Multitenant + personal**: Any Azure AD org or personal Microsoft accounts

   **Redirect URI**:
   - Platform: Web
   - URI: `http://localhost:8000/auth/callback` (for development)

   > **Important**: For production, use HTTPS: `https://your-domain.com/auth/callback`

4. **Click "Register"**

## Step 2: Configure API Permissions (Optional)

If you need to access Microsoft Graph or other Microsoft APIs:

1. Go to **API permissions**
2. Click "+ Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions"
5. Add permissions you need (e.g., `User.Read`, `Mail.Read`)
6. Click "Add permissions"
7. Click "Grant admin consent" (requires admin)

## Step 3: Expose an API

This step creates the scopes that your MCP server will validate.

1. **Go to "Expose an API"** in the left sidebar

2. **Set Application ID URI**
   - Click "Add" next to Application ID URI
   - Accept the default: `api://{your-client-id}`
   - Or set a custom URI like: `api://mcp.yourdomain.com`
   - Click "Save"

3. **Add Scopes**

   Click "+ Add a scope" and create your first scope:

   **Scope name**: `read`

   **Who can consent**: Admins and users

   **Admin consent display name**: `Read access to MCP server`

   **Admin consent description**: `Allows the application to read data from the MCP server`

   **User consent display name**: `Read your data`

   **User consent description**: `Allows the app to read your data from the MCP server`

   **State**: Enabled

   Click "Add scope"

4. **Add Additional Scopes**

   Repeat for other scopes you need:
   - `write`: Write access to MCP server
   - `admin`: Administrative access
   - Any custom scopes for your application

## Step 4: Enable Access Token v2

This is **critical** for FastMCP to work correctly.

1. **Go to "Manifest"** in the left sidebar

2. **Find the `api` section**
   ```json
   "api": {
       "requestedAccessTokenVersion": null
   }
   ```

3. **Change to version 2**
   ```json
   "api": {
       "requestedAccessTokenVersion": 2
   }
   ```

4. **Click "Save"** at the top

> **Why is this important?**
> FastMCP validates JWT tokens in v2 format. If this is not set, authentication will fail with token validation errors.

## Step 5: Create Client Secret

1. **Go to "Certificates & secrets"**

2. **Create a new secret**
   - Click "+ New client secret"
   - Description: `MCP Server Secret` (or descriptive name)
   - Expires: Choose based on your security policy
     - Recommended: 6 months or 1 year
     - Set a reminder to rotate before expiration

3. **Copy the secret value**
   - **IMMEDIATELY** copy the "Value" (not the "Secret ID")
   - Store it securely (password manager, Azure Key Vault, etc.)
   - You **cannot** view this value again after leaving the page

## Step 6: Collect Your Credentials

Go to the **Overview** page and note these values:

```
Application (client) ID:    xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Directory (tenant) ID:      yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
Client secret:              (the value you copied in Step 5)
```

## Step 7: Configure Your .env File

Add these values to your `.env` file:

```bash
# Azure Entra ID Configuration
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-secret-value-from-step-5
AZURE_TENANT_ID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy

# Base URL - UPDATE FOR PRODUCTION
AZURE_BASE_URL=http://localhost:8000

# Scopes (must match what you created in Step 3)
AZURE_REQUIRED_SCOPES=read,write

# Optional: Custom Application ID URI (if you set one)
# AZURE_IDENTIFIER_URI=api://mcp.yourdomain.com
```

## Step 8: Update Redirect URIs for Production

When deploying to production:

1. **Go to "Authentication"** in your app registration

2. **Add production redirect URI**
   - Click "+ Add a URI"
   - Enter: `https://your-production-domain.com/auth/callback`
   - **Must be HTTPS** (not HTTP)
   - Must match **exactly** (including trailing slash)

3. **Update your production .env**
   ```bash
   AZURE_BASE_URL=https://your-production-domain.com
   ```

## Verification Checklist

Before running your server, verify:

- [ ] App registration created
- [ ] Scopes created (read, write, etc.)
- [ ] `requestedAccessTokenVersion: 2` set in manifest
- [ ] Client secret created and copied
- [ ] Redirect URI matches your server URL + `/auth/callback`
- [ ] All credentials added to `.env` file
- [ ] For production: HTTPS redirect URI configured
- [ ] For production: `AZURE_BASE_URL` uses HTTPS

## Testing Authentication

1. **Start your server**
   ```bash
   ./scripts/run.sh
   ```

2. **Test with FastMCP client**
   ```python
   from fastmcp import Client
   import asyncio

   async def main():
       async with Client("http://localhost:8000/mcp", auth="oauth") as client:
           print("✅ Authentication successful!")
           tools = await client.list_tools()
           print(f"Available tools: {tools}")

   asyncio.run(main())
   ```

3. **What should happen**
   - Browser opens to Microsoft login page
   - You sign in with your Azure credentials
   - You consent to the requested permissions
   - Browser shows "Authentication successful"
   - Client connects and lists tools

## Troubleshooting

### Error: "AADSTS700016: Application not found"

**Solution**: Check that `AZURE_CLIENT_ID` matches your app registration

### Error: "AADSTS50011: Redirect URI mismatch"

**Solution**: Ensure redirect URI in Azure matches exactly:
- Check `AZURE_BASE_URL` in .env
- Verify redirect URI in Azure includes `/auth/callback`
- For production, must use HTTPS

### Error: "Invalid token" or "Token validation failed"

**Solution**: Verify `requestedAccessTokenVersion: 2` in manifest

### Error: "AADSTS65001: The user or administrator has not consented"

**Solution**:
- First-time users must consent to permissions
- Or grant admin consent in Azure Portal (API permissions page)

### Error: "Scope not found"

**Solution**:
- Verify scopes in `AZURE_REQUIRED_SCOPES` match what you created
- Check scope names are exact (case-sensitive)
- Don't include `api://` prefix in scope names

## Security Best Practices

1. **Use Specific Tenant ID**
   - Use your actual tenant ID (recommended)
   - Avoid using "common" for new applications
   - Consider "organizations" only for multi-tenant apps

2. **Rotate Secrets Regularly**
   - Set secret expiration (6-12 months)
   - Create new secret before old one expires
   - Update `.env` and restart server
   - Delete old secret after verification

3. **Limit Scope Permissions**
   - Only request scopes you actually need
   - Use principle of least privilege
   - Consider separate app registrations for dev/prod

4. **Use Azure Key Vault**
   - Store secrets in Azure Key Vault (production)
   - Use Managed Identity for server
   - Avoid storing secrets in code or config files

5. **Monitor and Audit**
   - Enable Azure AD sign-in logs
   - Monitor for suspicious activity
   - Review app permissions regularly

## Advanced Configuration

### Using Azure Government Cloud

For Azure Government deployments:

```bash
AZURE_BASE_AUTHORITY=login.microsoftonline.us
```

### Requesting Additional Microsoft Graph Scopes

To access Microsoft Graph APIs:

```bash
AZURE_ADDITIONAL_AUTHORIZE_SCOPES=User.Read,Mail.Read
```

Then in your code:
```python
from src.auth.provider import get_user_info_from_token

# Access token claims include Graph permissions
user_info = get_user_info_from_token()
```

### Multi-Tenant Configuration

For multi-tenant apps:

```bash
# Use "organizations" instead of specific tenant ID
AZURE_TENANT_ID=organizations

# Or for personal + work accounts
AZURE_TENANT_ID=common
```

## Resources

- [Microsoft Entra ID Documentation](https://learn.microsoft.com/en-us/entra/identity/)
- [App Registration Guide](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)
- [OAuth 2.0 in Azure AD](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
- [Azure AD Best Practices](https://learn.microsoft.com/en-us/entra/identity-platform/identity-platform-integration-checklist)

## Need Help?

- Check the [main README](../README.md) for general setup
- Review [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/topics/azure-active-directory.html) for Azure-specific questions
- Open an issue in your repository for boilerplate-related problems
