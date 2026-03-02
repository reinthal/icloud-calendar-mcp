# Deployment Guide

This guide covers deploying and managing the iCloud Calendar MCP server on Prefect Horizon.

## Overview

[Prefect Horizon](https://horizon.prefect.io/) is a managed hosting platform for FastMCP servers that provides:

- **Automatic CI/CD**: Push to main, server updates automatically
- **Authentication**: Built-in OAuth handling
- **Versioning**: Automatic versioning and rollbacks
- **Preview Deployments**: Automatic preview deployments for pull requests

## Initial Deployment

### 1. Prerequisites

- GitHub account
- Access to [horizon.prefect.io](https://horizon.prefect.io/)
- Repository with your FastMCP server code

### 2. Deploy to Horizon

1. Visit [horizon.prefect.io](https://horizon.prefect.io/) and sign in with your GitHub account
2. Connect your GitHub account to grant Horizon access to your repositories
3. Select the repository you want to deploy
4. Configure deployment settings:
   - **Server name**: Determines your server's URL
   - **Description**: Brief description of your server
   - **Entrypoint**: The Python module and FastMCP instance (e.g., `server.py:mcp`)
   - **Authentication**: Configure OAuth settings if needed

## Configuration Management

### Using `fastmcp.json`

FastMCP uses a **declarative JSON configuration** file as the single source of truth for server settings, dependencies, and environment variables.

#### Basic Structure

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["pandas", "matplotlib", "icalendar", "caldav"]
  }
}
```

#### With Environment Variables

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["icalendar", "caldav", "pytz", "requests"]
  },
  "env": {
    "ICLOUD_USERNAME": "your-email@example.com",
    "ICLOUD_PASSWORD": "your-app-specific-password",
    "DEFAULT_CALENDAR_NAME": "Personal"
  }
}
```

**Important**: All environment variable values must be strings.

## Managing Environment Variables

### Method 1: Direct Configuration (Recommended for Production)

Edit `fastmcp.json` in your repository:

```json
{
  "env": {
    "ICLOUD_USERNAME": "your-email@example.com",
    "ICLOUD_PASSWORD": "your-app-specific-password"
  }
}
```

### Method 2: Generate via CLI

Use the FastMCP CLI to generate configuration with environment variables:

```bash
# From individual variables
fastmcp install mcp-json server.py \
  --env ICLOUD_USERNAME=your-email@example.com \
  --env ICLOUD_PASSWORD=your-password

# From a .env file
fastmcp install mcp-json server.py --env-file .env
```

### Method 3: Using .env Files (Development)

Create a `.env` file in your repository:

```bash
ICLOUD_USERNAME=your-email@example.com
ICLOUD_PASSWORD=your-app-specific-password
DEFAULT_CALENDAR_NAME=Personal
```

**Warning**: Never commit `.env` files with secrets to your repository. Add `.env` to `.gitignore`.

## Updating Deployment Configuration

### Step 1: Update Configuration Files

Make changes to your `fastmcp.json` or other configuration files:

```bash
# Edit the configuration
vim fastmcp.json

# Or regenerate from .env
fastmcp install mcp-json server.py --env-file .env
```

### Step 2: Commit Changes

```bash
git add fastmcp.json
git commit -m "Update environment variables"
```

### Step 3: Push to Trigger Redeploy

```bash
git push origin main
```

Horizon will automatically:
1. Detect the push to main
2. Build a new container with your updated configuration
3. Deploy the new version
4. Make it available at your server's URL

## iCloud Calendar Specific Configuration

### Required Environment Variables

For the iCloud Calendar MCP server, you need:

```json
{
  "env": {
    "ICLOUD_USERNAME": "your-email@icloud.com",
    "ICLOUD_PASSWORD": "your-app-specific-password"
  }
}
```

### Optional Configuration

```json
{
  "env": {
    "ICLOUD_USERNAME": "your-email@icloud.com",
    "ICLOUD_PASSWORD": "your-app-specific-password",
    "DEFAULT_CALENDAR_NAME": "Personal",
    "CALDAV_SERVER": "https://caldav.icloud.com"
  }
}
```

### Getting an App-Specific Password

1. Sign in to [appleid.apple.com](https://appleid.apple.com/)
2. Navigate to **Sign-In and Security** → **App-Specific Passwords**
3. Click **Generate an app-specific password**
4. Enter a label (e.g., "MCP Server")
5. Copy the generated password (format: `xxxx-xxxx-xxxx-xxxx`)
6. Use this password in your `ICLOUD_PASSWORD` environment variable

## Best Practices

### Security

1. **Never commit secrets**: Keep `.env` files out of version control
2. **Use app-specific passwords**: Don't use your main iCloud password
3. **Rotate credentials regularly**: Update passwords periodically
4. **Review access**: Revoke app-specific passwords you're no longer using

### Configuration Management

1. **Use `fastmcp.json` for dependencies**: Keep all dependencies declared in the config file
2. **Document environment variables**: Add comments in your README about required env vars
3. **Test locally first**: Verify configuration works locally before pushing
4. **Use preview deployments**: Test changes in PR preview deployments before merging

### Deployment Workflow

1. **Develop locally**: Test changes in your local environment
2. **Create a PR**: Push to a feature branch and create a pull request
3. **Review preview**: Check the automatic preview deployment
4. **Merge to main**: Once approved, merge to trigger production deployment
5. **Verify deployment**: Check that the production deployment works as expected

## Troubleshooting

### Deployment Fails

- Check Horizon's build logs for errors
- Verify all required environment variables are set
- Ensure dependencies in `fastmcp.json` are correct
- Check that the entrypoint path is correct

### Authentication Issues

- Verify iCloud credentials are correct
- Ensure you're using an app-specific password, not your main password
- Check that the iCloud account has two-factor authentication enabled
- Verify the CalDAV server URL is correct

### Environment Variables Not Applied

- Ensure variables are in `fastmcp.json` under the `env` key
- Verify all values are strings (wrapped in quotes)
- Check that you've committed and pushed the changes
- Wait for the automatic redeploy to complete

### Calendar Not Found

- Check the calendar name is correct (case-sensitive)
- Verify the calendar exists in your iCloud account
- Try listing available calendars first
- Ensure the default calendar name is set if not providing one in requests

## Monitoring and Logs

Horizon provides:
- **Build logs**: Available during and after each deployment
- **Runtime logs**: Access to server logs for debugging
- **Metrics**: Basic performance and usage metrics
- **Version history**: Track all deployments and roll back if needed

## Rolling Back

If a deployment causes issues:

1. Navigate to your server in the Horizon dashboard
2. Go to the **Versions** section
3. Select a previous working version
4. Click **Rollback** to restore that version

Alternatively, revert your git commit and push to trigger a new deployment:

```bash
git revert HEAD
git push origin main
```

## References

- [FastMCP Documentation](https://gofastmcp.com/)
- [Prefect Horizon](https://horizon.prefect.io/)
- [MCP JSON Configuration](https://gofastmcp.com/integrations/mcp-json-configuration)
- [FastMCP Deployment Guide](https://gofastmcp.com/deployment/prefect-horizon)
