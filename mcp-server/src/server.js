import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";

import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const DEFAULT_ROOT = path.resolve(process.env.BRAVE_MCP_ROOT ?? path.join(import.meta.dirname, "..", ".."));
const WORKSPACE_VENV = path.join(DEFAULT_ROOT, ".venv");
const WORKSPACE_VENV_BIN = path.join(WORKSPACE_VENV, "bin");
const PORT = Number(process.env.PORT ?? process.env.BRAVE_MCP_PORT ?? 3333);
const MAX_READ_BYTES = Number(process.env.BRAVE_MCP_MAX_READ_BYTES ?? 200_000);
const MAX_COMMAND_BYTES = Number(process.env.BRAVE_MCP_MAX_COMMAND_BYTES ?? 200_000);
const DEFAULT_TIMEOUT_MS = Number(process.env.BRAVE_MCP_TIMEOUT_MS ?? 30_000);

const IGNORED_DIRS = new Set([
  ".git",
  ".venv",
  "__pycache__",
  "node_modules",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "dist",
  "build",
]);

function log(message, details = undefined) {
  const timestamp = new Date().toISOString();
  if (details === undefined) {
    console.error(`[${timestamp}] ${message}`);
  } else {
    console.error(`[${timestamp}] ${message}`, details);
  }
}

function normalizeRelativePath(inputPath = ".") {
  if (typeof inputPath !== "string" || inputPath.includes("\0")) {
    throw new Error("Path must be a normal string.");
  }
  const absolutePath = path.resolve(DEFAULT_ROOT, inputPath);
  const relativePath = path.relative(DEFAULT_ROOT, absolutePath);
  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    throw new Error(`Path escapes workspace root: ${inputPath}`);
  }
  return { absolutePath, relativePath: relativePath || "." };
}

async function pathExists(absolutePath) {
  try {
    await fs.access(absolutePath);
    return true;
  } catch {
    return false;
  }
}

async function readTextFile(relativePath, maxBytes = MAX_READ_BYTES) {
  const { absolutePath } = normalizeRelativePath(relativePath);
  const stat = await fs.stat(absolutePath);
  if (!stat.isFile()) {
    throw new Error(`Not a file: ${relativePath}`);
  }
  if (stat.size > maxBytes) {
    throw new Error(`File is ${stat.size} bytes, above limit ${maxBytes}.`);
  }
  return fs.readFile(absolutePath, "utf8");
}

function sha256(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}

async function walkFiles(startRelativePath, limit) {
  const { absolutePath: startAbsolutePath } = normalizeRelativePath(startRelativePath);
  const output = [];

  async function visit(absolutePath) {
    if (output.length >= limit) return;
    const entries = await fs.readdir(absolutePath, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (output.length >= limit) return;
      if (IGNORED_DIRS.has(entry.name)) continue;
      const child = path.join(absolutePath, entry.name);
      const relativePath = path.relative(DEFAULT_ROOT, child);
      if (entry.isDirectory()) {
        await visit(child);
      } else if (entry.isFile()) {
        output.push(relativePath);
      }
    }
  }

  const stat = await fs.stat(startAbsolutePath);
  if (stat.isFile()) return [path.relative(DEFAULT_ROOT, startAbsolutePath)];
  await visit(startAbsolutePath);
  return output;
}

function runProcess(command, args, options = {}) {
  return new Promise((resolve) => {
    const timeoutMs = Math.min(options.timeoutMs ?? DEFAULT_TIMEOUT_MS, 120_000);
    const env = {
      ...process.env,
      VIRTUAL_ENV: WORKSPACE_VENV,
      PATH: `${WORKSPACE_VENV_BIN}${path.delimiter}${process.env.PATH ?? ""}`,
      ...options.env,
    };
    const child = spawn(command, args, {
      cwd: options.cwd,
      shell: false,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
      setTimeout(() => child.kill("SIGKILL"), 1000).unref();
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
      if (stdout.length > MAX_COMMAND_BYTES) stdout = stdout.slice(0, MAX_COMMAND_BYTES);
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
      if (stderr.length > MAX_COMMAND_BYTES) stderr = stderr.slice(0, MAX_COMMAND_BYTES);
    });
    child.stdin.on("error", (error) => {
      if (error.code !== "EPIPE") {
        stderr += `${stderr ? "\n" : ""}${error.message}`;
      }
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      resolve({ exitCode: -1, stdout, stderr: `${stderr}${error.message}`, timedOut });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ exitCode: code ?? -1, stdout, stderr, timedOut });
    });
    if (!child.stdin.destroyed) {
      child.stdin.end(options.input ?? "");
    }
  });
}

function toolText(payload) {
  return {
    content: [{ type: "text", text: typeof payload === "string" ? payload : JSON.stringify(payload, null, 2) }],
  };
}

function toolHandler(name, handler) {
  return async (args) => {
    const startedAt = Date.now();
    log(`tool start: ${name}`, summarizeToolArgs(args));
    try {
      const result = await handler(args);
      log(`tool ok: ${name} (${Date.now() - startedAt}ms)`);
      return result;
    } catch (error) {
      log(`tool error: ${name} (${Date.now() - startedAt}ms)`, error.stack ?? String(error));
      throw error;
    }
  };
}

function summarizeToolArgs(args) {
  if (!args || typeof args !== "object") return args;
  const summary = {};
  for (const [key, value] of Object.entries(args)) {
    if (typeof value === "string" && value.length > 500) {
      summary[key] = `${value.slice(0, 500)}... <${value.length} chars>`;
    } else {
      summary[key] = value;
    }
  }
  return summary;
}

function createServer() {
  const server = new McpServer({
    name: "brave-workspace",
    version: "0.1.0",
  });

  server.tool("workspace_info", "Return the Brave workspace root and server limits.", {}, toolHandler("workspace_info", async () =>
    toolText({
      root: DEFAULT_ROOT,
      virtualEnv: WORKSPACE_VENV,
      maxReadBytes: MAX_READ_BYTES,
      maxCommandBytes: MAX_COMMAND_BYTES,
      defaultTimeoutMs: DEFAULT_TIMEOUT_MS,
      tools: ["list_files", "read_file", "search_files", "replace_text", "write_file", "apply_unified_patch", "run_command"],
    }),
  ));

  server.tool(
    "list_files",
    "List files under a workspace-relative directory, ignoring common generated folders.",
    {
      path: z.string().default(".").describe("Workspace-relative file or directory path."),
      limit: z.number().int().min(1).max(5000).default(500).describe("Maximum number of files to return."),
    },
    toolHandler("list_files", async ({ path: requestedPath, limit }) => toolText(await walkFiles(requestedPath, limit))),
  );

  server.tool(
    "read_file",
    "Read a UTF-8 file from the Brave workspace.",
    {
      path: z.string().describe("Workspace-relative file path."),
      maxBytes: z.number().int().min(1).max(1_000_000).default(MAX_READ_BYTES),
    },
    toolHandler("read_file", async ({ path: requestedPath, maxBytes }) => {
      const text = await readTextFile(requestedPath, maxBytes);
      return toolText({
        path: normalizeRelativePath(requestedPath).relativePath,
        sha256: sha256(text),
        text,
      });
    }),
  );

  server.tool(
    "search_files",
    "Search workspace files using ripgrep. Returns matching lines with file paths and line numbers.",
    {
      query: z.string().min(1).describe("Ripgrep search pattern."),
      path: z.string().default(".").describe("Workspace-relative path to search."),
      fixedStrings: z.boolean().default(false).describe("Treat query as literal text instead of a regex."),
      caseSensitive: z.boolean().default(true).describe("Use case-sensitive matching."),
      maxCount: z.number().int().min(1).max(1000).default(200).describe("Maximum matches to return."),
    },
    toolHandler("search_files", async ({ query, path: requestedPath, fixedStrings, caseSensitive, maxCount }) => {
      const { absolutePath } = normalizeRelativePath(requestedPath);
      const args = ["--line-number", "--column", "--no-heading", "--color", "never", "-m", String(maxCount)];
      if (fixedStrings) args.push("-F");
      if (!caseSensitive) args.push("-i");
      args.push(query, absolutePath);
      const result = await runProcess("rg", args, { cwd: DEFAULT_ROOT });
      return toolText(result);
    }),
  );

  server.tool(
    "replace_text",
    "Replace one exact text block in a UTF-8 file. Fails unless the old text appears exactly once.",
    {
      path: z.string().describe("Workspace-relative file path."),
      oldText: z.string().min(1).describe("Exact text to replace."),
      newText: z.string().describe("Replacement text."),
      expectedSha256: z.string().optional().describe("Optional SHA-256 hash from read_file to guard against stale edits."),
    },
    toolHandler("replace_text", async ({ path: requestedPath, oldText, newText, expectedSha256 }) => {
      const { absolutePath, relativePath } = normalizeRelativePath(requestedPath);
      const current = await readTextFile(relativePath, 5_000_000);
      if (expectedSha256 && sha256(current) !== expectedSha256) {
        throw new Error(`Refusing stale edit for ${relativePath}: SHA-256 does not match.`);
      }
      const matches = current.split(oldText).length - 1;
      if (matches !== 1) {
        throw new Error(`Expected exactly one match in ${relativePath}, found ${matches}.`);
      }
      const next = current.replace(oldText, newText);
      await fs.writeFile(absolutePath, next, "utf8");
      return toolText({ path: relativePath, oldSha256: sha256(current), newSha256: sha256(next), bytes: Buffer.byteLength(next) });
    }),
  );

  server.tool(
    "write_file",
    "Create or overwrite a UTF-8 file. Use expectedSha256 when overwriting an existing file.",
    {
      path: z.string().describe("Workspace-relative file path."),
      text: z.string().describe("Complete file contents to write."),
      expectedSha256: z.string().optional().describe("Required to guard overwrites when the target file already exists."),
      createOnly: z.boolean().default(false).describe("Fail if the target file already exists."),
    },
    toolHandler("write_file", async ({ path: requestedPath, text, expectedSha256, createOnly }) => {
      const { absolutePath, relativePath } = normalizeRelativePath(requestedPath);
      const exists = await pathExists(absolutePath);
      if (createOnly && exists) throw new Error(`File already exists: ${relativePath}`);
      if (exists) {
        if (!expectedSha256) throw new Error(`expectedSha256 is required to overwrite ${relativePath}.`);
        const current = await readTextFile(relativePath, 5_000_000);
        if (sha256(current) !== expectedSha256) throw new Error(`Refusing stale overwrite for ${relativePath}: SHA-256 does not match.`);
      }
      await fs.mkdir(path.dirname(absolutePath), { recursive: true });
      await fs.writeFile(absolutePath, text, "utf8");
      return toolText({ path: relativePath, sha256: sha256(text), bytes: Buffer.byteLength(text) });
    }),
  );

  server.tool(
    "apply_unified_patch",
    "Apply a unified diff patch to files in the workspace using git apply.",
    {
      patch: z.string().min(1).describe("Unified diff text."),
      checkOnly: z.boolean().default(false).describe("Only validate whether the patch applies; do not change files."),
    },
    toolHandler("apply_unified_patch", async ({ patch, checkOnly }) => {
      const check = await runProcess("git", ["apply", "--check", "-"], { cwd: DEFAULT_ROOT, env: {}, timeoutMs: DEFAULT_TIMEOUT_MS, input: patch });
      if (check.exitCode !== 0) return toolText({ ok: false, phase: "check", ...check });
      if (checkOnly) return toolText({ ok: true, checkOnly: true });
      const apply = await new Promise((resolve) => {
        const child = spawn("git", ["apply", "-"], { cwd: DEFAULT_ROOT, shell: false, env: process.env });
        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
        child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
        child.on("error", (error) => resolve({ exitCode: -1, stdout, stderr: `${stderr}${error.message}` }));
        child.on("close", (code) => resolve({ exitCode: code ?? -1, stdout, stderr }));
        child.stdin.end(patch);
      });
      return toolText({ ok: apply.exitCode === 0, ...apply });
    }),
  );

  server.tool(
    "run_command",
    "Run a non-shell command in the workspace. Intended for tests, linters, and project inspection.",
    {
      command: z.string().min(1).describe("Executable name, for example rg, git, npm, node, python3, bash."),
      args: z.array(z.string()).default([]).describe("Command arguments. No shell interpolation is performed."),
      cwd: z.string().default(".").describe("Workspace-relative working directory."),
      timeoutMs: z.number().int().min(1000).max(120_000).default(DEFAULT_TIMEOUT_MS),
    },
    toolHandler("run_command", async ({ command, args, cwd, timeoutMs }) => {
      const { absolutePath, relativePath } = normalizeRelativePath(cwd);
      const result = await runProcess(command, args, { cwd: absolutePath, timeoutMs });
      return toolText({ cwd: relativePath, command, args, ...result });
    }),
  );

  return server;
}

const app = express();
app.use((req, res, next) => {
  const startedAt = Date.now();
  res.on("finish", () => {
    log(`${req.method} ${req.originalUrl} -> ${res.statusCode} (${Date.now() - startedAt}ms)`);
  });
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "authorization, content-type, mcp-protocol-version, mcp-session-id");
  res.setHeader("Access-Control-Expose-Headers", "mcp-session-id");
  next();
});
app.options("/mcp", (_req, res) => {
  res.sendStatus(204);
});
app.use(express.json({ limit: "10mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true, name: "brave-workspace-mcp", root: DEFAULT_ROOT });
});

app.get("/", (_req, res) => {
  res.type("text/plain").send("Brave workspace MCP server is running. Use /mcp for MCP and /health for health checks.\n");
});

app.post("/mcp", async (req, res) => {
  log("mcp request", { method: req.body?.method, id: req.body?.id, tool: req.body?.params?.name });
  const server = createServer();
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  res.on("close", () => {
    transport.close();
    server.close();
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    log("mcp request error", error.stack ?? String(error));
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        id: req.body?.id ?? null,
        error: {
          code: -32603,
          message: error.message ?? "Internal MCP server error",
        },
      });
    }
  }
});

app.listen(PORT, "0.0.0.0", () => {
  log(`Brave workspace MCP server listening at http://localhost:${PORT}/mcp`);
  log(`Workspace root: ${DEFAULT_ROOT}`);
});
