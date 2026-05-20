# Brave Workspace MCP Server

This is a local MCP server for ChatGPT Apps/Connectors development. It exposes controlled tools for the Brave workspace:

- `workspace_info`
- `list_files`
- `read_file`
- `search_files`
- `replace_text`
- `write_file`
- `apply_unified_patch`
- `run_command`

## Run Locally

```bash
cd mcp-server
npm install
npm start
```

`run_command` automatically prepends the workspace `.venv/bin` directory to `PATH`, so Brave commands can use `python`, `python3`, and `evennia` the same way `run_evennia.sh` does.

The server listens on:

```text
http://localhost:3333/mcp
```

Health check:

```bash
curl http://localhost:3333/health
```

## Connect ChatGPT During Development

ChatGPT needs a public HTTPS URL. Use a tunnel while the server is running:

```bash
npx --yes cloudflared tunnel --url http://localhost:3333
```

Then create a ChatGPT connector with:

```text
https://YOUR-TUNNEL-HOST/mcp
```

The `trycloudflare.com` URL is temporary. If the tunnel session exits, restart the tunnel and update the connector URL. Anonymous `localhost.run` tunnels were too unstable for ChatGPT connector testing because they can rotate URLs and return `no tunnel here :(` while the SSH process is still alive.

Set `BRAVE_MCP_ROOT` if you want to point the server at a different workspace root.
