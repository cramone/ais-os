# Official Microsoft Azure DevOps MCP server (@azure-devops/mcp), dockerized.
#
# In-repo (not D:\mcp) so it reaches Cortex via git the same way everything
# else does. Build once per machine that needs it — Claude Code on Windows,
# Claudia on Cortex — since this is a stdio MCP server, spawned locally by
# each consumer, not a shared network service.
#
# Build:  docker build -t azure-devops-mcp:latest .   (from this directory)
# Run:    see AIS-OS/.mcp.json for the Claude Code invocation, or
#         docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md-style
#         notes for the Claudia (Hermes) config.

FROM node:22-alpine

# Pin a version rather than floating on `latest` — bump deliberately.
RUN npm install -g @azure-devops/mcp@2.7.0

# PAT auth only — this org doesn't allow interactive/Entra auth. See
# GETTINGSTARTED.md in microsoft/azure-devops-mcp: PERSONAL_ACCESS_TOKEN must
# be base64(<any-non-empty-string>:<raw PAT>), not the raw PAT.
ENTRYPOINT ["mcp-server-azuredevops"]
