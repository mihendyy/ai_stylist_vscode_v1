"""Prometheus exporter helpers."""

from __future__ import annotations

from prometheus_client import Counter, Gauge


outfit_generation_total = Counter(
    "outfit_generation_total",
    "Total number of outfit generation requests.",
)

active_sessions = Gauge(
    "active_sessions",
    "Number of currently active Telegram sessions.",
)
