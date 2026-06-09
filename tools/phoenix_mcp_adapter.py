"""PhoenixGuard — Phoenix MCP Server Adapter (Arize Track compliance).

Connects to the official `@arizeai/phoenix-mcp` server via Node Stdio transport,
invokes its tools, and normalizes outputs to match the schemas of downstream agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PhoenixMCPAdapter:
    """Adapter to connect to the Phoenix MCP server and invoke tools."""

    def __init__(self) -> None:
        self.api_key = os.getenv("PHOENIX_API_KEY", "")
        # The MCP server expects PHOENIX_HOST
        self.host = (
            os.getenv("PHOENIX_HOST")
            or os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
            or "http://localhost:6006"
        )
        # Strip trailing /v1 or /v1/traces if present for PHOENIX_HOST compliance
        if "/v1" in self.host:
            self.host = self.host.split("/v1")[0]

        self.project = os.getenv("PHOENIX_PROJECT") or os.getenv(
            "PHOENIX_PROJECT_NAME", "phoenixguard"
        )

        # Validate that we have credentials to attempt connection
        if not self.api_key:
            raise ValueError("PHOENIX_API_KEY is not set for MCP adapter.")

    async def _call_mcp_tool_async(self, tool_name: str, arguments: dict) -> Any:
        """Asynchronously spawns the MCP server and executes a tool."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        # Prepare server parameters
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@arizeai/phoenix-mcp@latest"],
            env={
                "PHOENIX_API_KEY": self.api_key,
                "PHOENIX_HOST": self.host,
                "PHOENIX_PROJECT": self.project,
                # Carry over PATH to resolve npx/node on Windows
                "PATH": os.environ.get("PATH", ""),
                "SystemRoot": os.environ.get("SystemRoot", ""),
            },
        )

        logger.debug("Spawning Phoenix MCP Server: %s with args %s", tool_name, arguments)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)

                # Parse the result
                for block in result.content:
                    if getattr(block, "type", None) == "text":
                        try:
                            data = json.loads(block.text)
                            return data
                        except Exception:
                            # If not JSON, return raw text block
                            return block.text
                return None

    def _call_mcp_tool(self, tool_name: str, arguments: dict) -> Any:
        """Synchronous wrapper to call the async tool execution."""
        logger.info("[PhoenixMCPAdapter] MCP execution path triggered for tool: %s", tool_name)
        try:
            # Check if there is an active running event loop in the current thread
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                logger.info("[PhoenixMCPAdapter] Existing loop reused via ThreadPoolExecutor for tool: %s", tool_name)
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self._call_mcp_tool_async(tool_name, arguments))
                    )
                    return future.result()
            else:
                logger.info("[PhoenixMCPAdapter] New loop created and set in thread for tool: %s", tool_name)
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self._call_mcp_tool_async(tool_name, arguments))
                finally:
                    new_loop.close()
        except Exception as exc:
            logger.warning("[PhoenixMCPAdapter] MCP tool execution failed: %s (%s)", tool_name, exc)
            raise exc

    # ── Normalization Helpers ────────────────────────────────────────

    def _normalize_trace(self, t: dict) -> dict:
        """Normalize a trace object from the MCP schema to our production schema."""
        def get_val(d, keys, default=None):
            for k in keys:
                if k in d:
                    return d[k]
            return default

        normalized_spans = []
        raw_spans = get_val(t, ["spans"], [])
        for s in raw_spans:
            normalized_spans.append({
                "id": get_val(s, ["id"]),
                "span_id": get_val(s, ["span_id", "spanId"]),
                "parent_id": get_val(s, ["parent_id", "parentId"]),
                "name": get_val(s, ["name"]),
                "span_kind": get_val(s, ["span_kind", "spanKind"]),
                "status_code": get_val(s, ["status_code", "statusCode"]),
                "start_time": get_val(s, ["start_time", "startTime"]),
                "end_time": get_val(s, ["end_time", "endTime"]),
                "status_message": get_val(s, ["status_message", "statusMessage"]),
            })

        return {
            "id": get_val(t, ["id"]),
            "trace_id": get_val(t, ["trace_id", "traceId"]),
            "project_id": get_val(t, ["project_id", "projectId"]),
            "start_time": get_val(t, ["start_time", "startTime"]),
            "end_time": get_val(t, ["end_time", "endTime"]),
            "token_count_prompt": get_val(
                t, ["token_count_prompt", "tokenCountPrompt", "prompt_tokens"]
            ),
            "token_count_completion": get_val(
                t, ["token_count_completion", "tokenCountCompletion", "completion_tokens"]
            ),
            "token_count_total": get_val(
                t, ["token_count_total", "tokenCountTotal", "total_tokens"]
            ),
            "spans": normalized_spans,
        }

    def _normalize_session(self, s: dict) -> dict:
        """Normalize a session object from MCP to production schema."""
        def get_val(d, keys, default=None):
            for k in keys:
                if k in d:
                    return d[k]
            return default
        return {
            "id": get_val(s, ["id"]),
            "session_id": get_val(s, ["session_id", "sessionId"]),
            "project_id": get_val(s, ["project_id", "projectId"]),
            "start_time": get_val(s, ["start_time", "startTime"]),
            "end_time": get_val(s, ["end_time", "endTime"]),
            "token_count_prompt": get_val(s, ["token_count_prompt", "tokenCountPrompt"]),
            "token_count_completion": get_val(
                s, ["token_count_completion", "tokenCountCompletion"]
            ),
            "token_count_total": get_val(s, ["token_count_total", "tokenCountTotal"]),
        }

    def _normalize_prompt(self, p: dict) -> dict:
        """Normalize a prompt template version from MCP to production schema."""
        def get_val(d, keys, default=None):
            for k in keys:
                if k in d:
                    return d[k]
            return default

        template_data = get_val(p, ["template"])
        template_text = ""
        if isinstance(template_data, dict):
            messages = template_data.get("messages", [])
            if messages:
                template_text = "\n".join(
                    f"{m.get('role', '')}: {m.get('content', '')}" for m in messages
                )
            else:
                template_text = str(template_data)
        elif template_data:
            template_text = str(template_data)

        return {
            "id": get_val(p, ["id"]),
            "name": get_val(p, ["name"]),
            "description": get_val(p, ["description"]),
            "template": template_text or get_val(p, ["template"]),
            "version": get_val(p, ["version", "id"]),
        }

    def _normalize_dataset(self, d: dict) -> dict:
        """Normalize a dataset object from MCP to production schema."""
        def get_val(d, keys, default=None):
            for k in keys:
                if k in d:
                    return d[k]
            return default
        return {
            "id": get_val(d, ["id"]),
            "name": get_val(d, ["name"]),
            "description": get_val(d, ["description"]),
            "example_count": get_val(d, ["example_count", "exampleCount"]),
            "created_at": get_val(d, ["created_at", "createdAt"]),
            "updated_at": get_val(d, ["updated_at", "updatedAt"]),
        }

    def _normalize_experiment(self, e: dict) -> dict:
        """Normalize an experiment object from MCP to production schema."""
        def get_val(d, keys, default=None):
            for k in keys:
                if k in d:
                    return d[k]
            return default
        return {
            "id": get_val(e, ["id"]),
            "dataset_id": get_val(e, ["dataset_id", "datasetId"]),
            "repetitions": get_val(e, ["repetitions"]),
            "project_name": get_val(e, ["project_name", "projectName"]),
            "created_at": get_val(e, ["created_at", "createdAt"]),
            "example_count": get_val(e, ["example_count", "exampleCount"]),
            "successful_run_count": get_val(
                e, ["successful_run_count", "successfulRunCount"]
            ),
            "failed_run_count": get_val(e, ["failed_run_count", "failedRunCount"]),
        }

    # ── Client Methods ───────────────────────────────────────────────

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch and normalize traces using MCP list-traces tool."""
        res = self._call_mcp_tool(
            "list-traces",
            {"project_identifier": self.project, "limit": limit},
        )
        if isinstance(res, list):
            return [self._normalize_trace(t) for t in res]
        elif isinstance(res, dict) and "traces" in res:
            # Some versions might return wrapped dictionary
            return [self._normalize_trace(t) for t in res["traces"]]
        return []

    def get_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch and normalize sessions using MCP list-sessions tool."""
        res = self._call_mcp_tool(
            "list-sessions",
            {"project_identifier": self.project, "limit": limit},
        )
        if isinstance(res, list):
            return [self._normalize_session(s) for s in res]
        return []

    def get_prompts(self, prompt_name: str = "") -> List[Dict[str, Any]]:
        """Fetch prompts using MCP get-latest-prompt or list-prompts tools."""
        if prompt_name:
            res = self._call_mcp_tool("get-latest-prompt", {"prompt_identifier": prompt_name})
            if res:
                # Add prompt name to version payload
                if isinstance(res, dict) and "name" not in res:
                    res["name"] = prompt_name
                return [self._normalize_prompt(res)]
            return []
        else:
            res = self._call_mcp_tool("list-prompts", {"limit": 100})
            if isinstance(res, list):
                return [self._normalize_prompt(p) for p in res]
            return []

    def get_datasets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch and normalize datasets using MCP list-datasets tool."""
        res = self._call_mcp_tool("list-datasets", {"limit": limit})
        if isinstance(res, list):
            return [self._normalize_dataset(d) for d in res]
        return []

    def get_experiments(self, dataset_id: str = "") -> List[Dict[str, Any]]:
        """Fetch experiments using MCP list-experiments-for-dataset tool."""
        if dataset_id:
            res = self._call_mcp_tool(
                "list-experiments-for-dataset",
                {"dataset_id": dataset_id, "limit": 100},
            )
            if isinstance(res, list):
                return [self._normalize_experiment(e) for e in res]
            return []
        else:
            # Query datasets first, then iterate
            datasets = self.get_datasets()
            all_experiments = []
            for d in datasets:
                ds_id = d.get("id")
                if ds_id:
                    try:
                        res = self._call_mcp_tool(
                            "list-experiments-for-dataset",
                            {"dataset_id": ds_id, "limit": 100},
                        )
                        if isinstance(res, list):
                            all_experiments.extend([self._normalize_experiment(e) for e in res])
                    except Exception:
                        pass
            return all_experiments
