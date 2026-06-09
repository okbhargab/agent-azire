"""PhoenixGuard Agent Tools.

Provides functional tools for the Google ADK agent.
Each tool call generates real trace spans in Phoenix Cloud for
later analysis by the reliability engine.
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Tool 1: Simulated Weather Lookup
# ────────────────────────────────────────────────────────────────────

def get_weather(city: str) -> dict:
    """Get current weather information for a city.

    Returns simulated but realistic weather data including temperature,
    condition, humidity, and wind speed.  Each call produces a traced
    span in Phoenix so the reliability engine can analyze tool behavior.

    Args:
        city: The name of the city to get weather for (e.g. "Tokyo").

    Returns:
        A dictionary containing temperature_celsius, condition,
        humidity_percent, wind_speed_kmh, and a UTC timestamp.
    """
    logger.info("get_weather called for city=%s", city)

    # Deterministic seed from city name so the same city returns
    # consistent-ish data within the same hour.
    seed = int(hashlib.md5(city.lower().encode()).hexdigest()[:8], 16)
    rng = random.Random(seed + datetime.now(timezone.utc).hour)

    conditions = [
        "Sunny",
        "Partly Cloudy",
        "Cloudy",
        "Overcast",
        "Light Rain",
        "Heavy Rain",
        "Thunderstorm",
        "Foggy",
        "Windy",
        "Clear",
    ]

    temperature = round(rng.uniform(-10, 42), 1)
    condition = rng.choice(conditions)
    humidity = rng.randint(20, 95)
    wind_speed = round(rng.uniform(0, 60), 1)

    result = {
        "city": city.title(),
        "temperature_celsius": temperature,
        "condition": condition,
        "humidity_percent": humidity,
        "wind_speed_kmh": wind_speed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("Weather result: %s", result)
    return result


# ────────────────────────────────────────────────────────────────────
# Tool 2: Real System Health Check
# ────────────────────────────────────────────────────────────────────

def get_system_health() -> dict:
    """Check current system health metrics of the host machine.

    Returns real system metrics including CPU usage, memory usage,
    disk usage, and system uptime.  Useful for monitoring the host
    that is running the AI agent.

    Returns:
        A dictionary containing cpu_percent, memory_percent,
        disk_percent, uptime_hours, overall status, and a UTC timestamp.
    """
    logger.info("get_system_health called")

    try:
        import psutil
    except ImportError:
        logger.error("psutil is not installed")
        return {
            "error": "psutil is not installed. Run: pip install psutil",
            "status": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)

    # Memory
    mem = psutil.virtual_memory()

    # Disk — use the root of the current drive (works cross-platform)
    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(disk_path)

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = datetime.now(timezone.utc).timestamp() - boot_time
    uptime_hours = round(uptime_seconds / 3600, 1)

    # Health status classification
    if cpu_percent > 90 or mem.percent > 90 or disk.percent > 95:
        status = "critical"
    elif cpu_percent > 70 or mem.percent > 70 or disk.percent > 85:
        status = "warning"
    else:
        status = "healthy"

    result = {
        "cpu_percent": cpu_percent,
        "memory_percent": round(mem.percent, 1),
        "memory_used_gb": round(mem.used / (1024 ** 3), 2),
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),
        "disk_percent": round(disk.percent, 1),
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "uptime_hours": uptime_hours,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("System health: status=%s cpu=%.1f%% mem=%.1f%%",
                status, cpu_percent, mem.percent)
    return result
