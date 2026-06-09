"""PhoenixGuard — Phoenix Tools (Phase 2).

Provides a ``PhoenixClient`` wrapper around the ``arize-phoenix-client``
SDK so the rest of the codebase works with clean, typed Python objects
instead of raw API dicts.

Every public function returns plain ``dict`` / ``list[dict]`` data that
can be serialised to JSON, making the output directly usable as ADK tool
results or as input to the analysis agents (Phases 3–8).

Usage::

    from tools.phoenix_tools import PhoenixTools

    pt = PhoenixTools()                     # reads env vars
    projects = pt.get_projects()
    traces   = pt.get_recent_traces()
    spans    = pt.get_recent_spans()
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

try:
    from phoenix.client import Client as _PhoenixClient
    PHOENIX_SDK_AVAILABLE = True
except ImportError:
    _PhoenixClient = None  # type: ignore[assignment, misc]
    PHOENIX_SDK_AVAILABLE = False


logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PhoenixConfig:
    """Immutable configuration for the Phoenix connection."""

    base_url: str = ""
    api_key: str = ""
    project_name: str = "phoenixguard"
    default_limit: int = 100
    default_lookback_hours: int = 24
    timeout: int = 10

    @classmethod
    def from_env(cls) -> "PhoenixConfig":
        """Build configuration from environment variables."""
        return cls(
            base_url=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"),
            api_key=os.getenv("PHOENIX_API_KEY", ""),
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "phoenixguard"),
            default_limit=int(os.getenv("PHOENIX_DEFAULT_LIMIT", "100")),
            default_lookback_hours=int(os.getenv("PHOENIX_LOOKBACK_HOURS", "24")),
            timeout=int(os.getenv("PHOENIX_TIMEOUT", "10")),
        )


# ────────────────────────────────────────────────────────────────────
# Helper: safe dict extraction from TypedDict responses
# ────────────────────────────────────────────────────────────────────

def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a TypedDict (or mapping) to a plain dict, recursively."""
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]  # type: ignore[return-value]
    return obj


# ────────────────────────────────────────────────────────────────────
# Main abstraction
# ────────────────────────────────────────────────────────────────────

class PhoenixTools:
    """High-level wrapper around the Phoenix Python client.

    Provides the six methods required by the PhoenixGuard architecture:

    * ``get_projects()``
    * ``get_recent_traces()``
    * ``get_recent_spans()``
    * ``get_recent_sessions()``
    * ``get_prompts()``
    * ``get_datasets()``
    * ``get_experiments()``
    """

    def __init__(self, config: Optional[PhoenixConfig] = None) -> None:
        if not PHOENIX_SDK_AVAILABLE or _PhoenixClient is None:
            raise ImportError(
                "The 'phoenix' package is not installed. "
                "Please run 'pip install arize-phoenix' to use the Phoenix Python SDK."
            )
        self._config = config or PhoenixConfig.from_env()
        self._client = _PhoenixClient(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
        )
        logger.info(
            "PhoenixTools initialised: base_url=%s project=%s",
            self._config.base_url,
            self._config.project_name,
        )

    # ── property shortcuts ──────────────────────────────────────────

    @property
    def config(self) -> PhoenixConfig:
        return self._config

    @property
    def client(self) -> _PhoenixClient:
        """Access the underlying ``phoenix.client.Client`` for advanced use."""
        return self._client

    # ── 1. Projects ─────────────────────────────────────────────────

    def get_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the Phoenix instance.

        Returns:
            List of project dicts with keys: ``name``, ``id``,
            ``description``.
        """
        logger.info("Fetching projects")
        try:
            raw = self._client.projects.list()
            projects = [_to_dict(p) for p in raw]
            logger.info("Found %d projects", len(projects))
            return projects
        except Exception as exc:
            logger.error("Failed to fetch projects: %s", exc)
            return [{"error": str(exc)}]

    # ── 2. Traces ───────────────────────────────────────────────────

    def get_recent_traces(
        self,
        *,
        project_name: Optional[str] = None,
        limit: Optional[int] = None,
        lookback_hours: Optional[int] = None,
        include_spans: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent traces for the project.

        Args:
            project_name: Override the default project.
            limit: Max traces to return (default from config).
            lookback_hours: How far back to look (default from config).
            include_spans: Whether to embed span data inside each trace.

        Returns:
            List of trace dicts with keys: ``id``, ``trace_id``,
            ``project_id``, ``start_time``, ``end_time``,
            ``token_count_prompt``, ``token_count_completion``,
            ``token_count_total``, and optionally ``spans``.
        """
        proj = project_name or self._config.project_name
        lim = limit or self._config.default_limit
        hours = lookback_hours or self._config.default_lookback_hours
        start = datetime.now(timezone.utc) - timedelta(hours=hours)

        logger.info(
            "Fetching traces: project=%s limit=%d lookback=%dh",
            proj, lim, hours,
        )
        try:
            raw = self._client.traces.get_traces(
                project_identifier=proj,
                start_time=start,
                limit=lim,
                sort="start_time",
                order="desc",
                include_spans=include_spans,
                timeout=self._config.timeout,
            )
            traces = [_to_dict(t) for t in raw]
            logger.info("Found %d traces", len(traces))
            return traces
        except Exception as exc:
            logger.error("Failed to fetch traces: %s", exc)
            return [{"error": str(exc)}]

    # ── 3. Spans ────────────────────────────────────────────────────

    def get_recent_spans(
        self,
        *,
        project_name: Optional[str] = None,
        limit: Optional[int] = None,
        lookback_hours: Optional[int] = None,
        span_kind: Optional[str] = None,
        status_code: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent spans, optionally filtered.

        Args:
            project_name: Override the default project.
            limit: Max spans to return.
            lookback_hours: How far back to look.
            span_kind: Filter by kind (e.g. ``"LLM"``, ``"TOOL"``,
                       ``"AGENT"``, ``"CHAIN"``).
            status_code: Filter by status (e.g. ``"OK"``, ``"ERROR"``).
            name: Filter by span name.

        Returns:
            List of span dicts with keys: ``name``, ``span_kind``,
            ``status_code``, ``start_time``, ``end_time``,
            ``attributes``, etc.
        """
        proj = project_name or self._config.project_name
        lim = limit or self._config.default_limit
        hours = lookback_hours or self._config.default_lookback_hours
        start = datetime.now(timezone.utc) - timedelta(hours=hours)

        logger.info(
            "Fetching spans: project=%s limit=%d kind=%s status=%s",
            proj, lim, span_kind, status_code,
        )
        try:
            kwargs: Dict[str, Any] = dict(
                project_identifier=proj,
                start_time=start,
                limit=lim,
                timeout=self._config.timeout,
            )
            if span_kind:
                kwargs["span_kind"] = span_kind
            if status_code:
                kwargs["status_code"] = status_code
            if name:
                kwargs["name"] = name

            raw = self._client.spans.get_spans(**kwargs)
            spans = [_to_dict(s) for s in raw]
            logger.info("Found %d spans", len(spans))
            return spans
        except Exception as exc:
            logger.error("Failed to fetch spans: %s", exc)
            return [{"error": str(exc)}]

    # ── 4. Sessions ─────────────────────────────────────────────────

    def get_recent_sessions(
        self,
        *,
        project_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent sessions for the project.

        Args:
            project_name: Override the default project.
            limit: Max sessions to return.

        Returns:
            List of session dicts with keys: ``id``, ``session_id``,
            ``project_id``, ``start_time``, ``end_time``, ``traces``,
            and token counts.
        """
        proj = project_name or self._config.project_name
        lim = limit or self._config.default_limit

        logger.info("Fetching sessions: project=%s limit=%d", proj, lim)
        try:
            raw = self._client.sessions.list(
                project_name=proj,
                limit=lim,
                timeout=self._config.timeout,
            )
            sessions = [_to_dict(s) for s in raw]
            logger.info("Found %d sessions", len(sessions))
            return sessions
        except Exception as exc:
            logger.error("Failed to fetch sessions: %s", exc)
            return [{"error": str(exc)}]

    # ── 5. Prompts ──────────────────────────────────────────────────

    def get_prompts(
        self,
        *,
        prompt_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve prompts from Phoenix.

        If *prompt_name* is given, fetches that specific prompt version.
        Otherwise returns an informational message (Phoenix does not
        expose a ``list`` endpoint for prompts at this time).

        Args:
            prompt_name: The identifier of a specific prompt to fetch.

        Returns:
            List of prompt dicts.
        """
        logger.info("Fetching prompts: name=%s", prompt_name)
        try:
            if prompt_name:
                raw = self._client.prompts.get(prompt_identifier=prompt_name)
                return [_to_dict(raw)] if raw else []
            # No list endpoint — return informational
            return [{"info": "Provide a prompt_name to fetch a specific prompt."}]
        except Exception as exc:
            logger.error("Failed to fetch prompts: %s", exc)
            return [{"error": str(exc)}]

    # ── 6. Datasets ─────────────────────────────────────────────────

    def get_datasets(
        self,
        *,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List datasets in Phoenix.

        Returns:
            List of dataset dicts with keys: ``id``, ``name``,
            ``description``, ``example_count``, ``created_at``,
            ``updated_at``.
        """
        lim = limit or self._config.default_limit

        logger.info("Fetching datasets: limit=%d", lim)
        try:
            raw = self._client.datasets.list(limit=lim, timeout=self._config.timeout)
            datasets = [_to_dict(d) for d in raw]
            logger.info("Found %d datasets", len(datasets))
            return datasets
        except Exception as exc:
            logger.error("Failed to fetch datasets: %s", exc)
            return [{"error": str(exc)}]

    # ── 7. Experiments ──────────────────────────────────────────────

    def get_experiments(
        self,
        *,
        dataset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List experiments for a dataset.

        Args:
            dataset_id: The dataset ID to list experiments for.
                If not given, attempts to find experiments for
                all known datasets.

        Returns:
            List of experiment dicts with keys: ``id``,
            ``dataset_id``, ``repetitions``, ``project_name``,
            ``created_at``, ``example_count``,
            ``successful_run_count``, ``failed_run_count``.
        """
        logger.info("Fetching experiments: dataset_id=%s", dataset_id)
        try:
            if dataset_id:
                raw = self._client.experiments.list(
                    dataset_id=dataset_id,
                    timeout=self._config.timeout,
                )
                return [_to_dict(e) for e in raw]

            # Iterate over all datasets
            all_experiments: List[Dict[str, Any]] = []
            datasets = self.get_datasets()
            for ds in datasets:
                if "error" in ds:
                    continue
                ds_id = ds.get("id", "")
                if not ds_id:
                    continue
                try:
                    raw = self._client.experiments.list(
                        dataset_id=ds_id,
                        timeout=self._config.timeout,
                    )
                    all_experiments.extend(_to_dict(e) for e in raw)
                except Exception:
                    logger.warning("No experiments for dataset %s", ds_id)
            logger.info("Found %d experiments total", len(all_experiments))
            return all_experiments
        except Exception as exc:
            logger.error("Failed to fetch experiments: %s", exc)
            return [{"error": str(exc)}]

    # ── Convenience: spans DataFrame ────────────────────────────────

    def get_spans_dataframe(
        self,
        *,
        project_name: Optional[str] = None,
        limit: int = 1000,
        lookback_hours: Optional[int] = None,
    ) -> "Any":
        """Return spans as a pandas DataFrame for analysis.

        This is a convenience wrapper for ``client.spans.get_spans_dataframe``
        useful in Phases 3–8 for batch analysis.

        Returns:
            A ``pandas.DataFrame`` with one row per span.
        """
        proj = project_name or self._config.project_name
        hours = lookback_hours or self._config.default_lookback_hours
        start = datetime.now(timezone.utc) - timedelta(hours=hours)

        logger.info("Fetching spans DataFrame: project=%s limit=%d", proj, limit)
        try:
            df = self._client.spans.get_spans_dataframe(
                project_name=proj,
                start_time=start,
                limit=limit,
                timeout=self._config.timeout,
            )
            logger.info("DataFrame shape: %s", df.shape)
            return df
        except Exception as exc:
            logger.error("Failed to fetch spans DataFrame: %s", exc)
            import pandas as pd
            return pd.DataFrame()


# ────────────────────────────────────────────────────────────────────
# ADK-compatible tool functions
# ────────────────────────────────────────────────────────────────────
# These thin wrappers can be registered as ADK agent tools so
# PhoenixGuard can introspect its own traces at runtime.

_tools_instance: Optional[PhoenixTools] = None


def _get_tools() -> PhoenixTools:
    """Lazy singleton for the PhoenixTools instance."""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = PhoenixTools()
    return _tools_instance


def get_phoenix_projects() -> dict:
    """List all projects in Phoenix Cloud.

    Returns a dictionary containing a list of projects, each with
    name, id, and description.

    Returns:
        A dictionary with a 'projects' key containing the project list.
    """
    projects = _get_tools().get_projects()
    return {"projects": projects, "count": len(projects)}


def get_phoenix_traces(limit: int = 20, lookback_hours: int = 24) -> dict:
    """Get recent traces from Phoenix Cloud for the current project.

    Retrieves trace-level data including trace IDs, timing, and token
    counts.  Useful for understanding overall agent interaction patterns.

    Args:
        limit: Maximum number of traces to return (default 20).
        lookback_hours: How many hours back to search (default 24).

    Returns:
        A dictionary with a 'traces' key and count.
    """
    traces = _get_tools().get_recent_traces(
        limit=limit, lookback_hours=lookback_hours,
    )
    return {"traces": traces, "count": len(traces)}


def get_phoenix_spans(
    limit: int = 50,
    lookback_hours: int = 24,
    span_kind: str = "",
) -> dict:
    """Get recent spans from Phoenix Cloud for the current project.

    Retrieves individual span data including name, kind, status,
    timing, and attributes.  Filter by span_kind to focus on LLM
    calls, tool executions, or agent runs.

    Args:
        limit: Maximum number of spans to return (default 50).
        lookback_hours: How many hours back to search (default 24).
        span_kind: Filter by kind — use 'LLM', 'TOOL', 'AGENT',
                   or 'CHAIN'. Empty string means no filter.

    Returns:
        A dictionary with a 'spans' key and count.
    """
    kwargs: Dict[str, Any] = dict(limit=limit, lookback_hours=lookback_hours)
    if span_kind:
        kwargs["span_kind"] = span_kind
    spans = _get_tools().get_recent_spans(**kwargs)
    return {"spans": spans, "count": len(spans)}


def get_phoenix_sessions(limit: int = 20) -> dict:
    """Get recent sessions from Phoenix Cloud for the current project.

    Sessions group multiple traces from a single user conversation.

    Args:
        limit: Maximum number of sessions to return (default 20).

    Returns:
        A dictionary with a 'sessions' key and count.
    """
    sessions = _get_tools().get_recent_sessions(limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


def get_phoenix_datasets() -> dict:
    """List all datasets in Phoenix Cloud.

    Returns:
        A dictionary with a 'datasets' key and count.
    """
    datasets = _get_tools().get_datasets()
    return {"datasets": datasets, "count": len(datasets)}


def get_phoenix_experiments(dataset_id: str = "") -> dict:
    """List experiments in Phoenix Cloud.

    If dataset_id is provided, lists experiments for that dataset.
    Otherwise lists experiments across all datasets.

    Args:
        dataset_id: Optional dataset ID to filter by.

    Returns:
        A dictionary with an 'experiments' key and count.
    """
    kwargs: Dict[str, Any] = {}
    if dataset_id:
        kwargs["dataset_id"] = dataset_id
    experiments = _get_tools().get_experiments(**kwargs)
    return {"experiments": experiments, "count": len(experiments)}
