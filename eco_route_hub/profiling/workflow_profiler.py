"""
Multi-stage benchmark profiler for route simulation pipelines.

Measures wall-clock time, CPU time, peak memory usage, and custom metadata
for distinct pipeline stages (data fetching, route processing, speed profiling,
and consumption estimation).
"""

import os
import platform
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class StageMetrics:
    """Metrics recorded for a single workflow stage."""

    stage_name: str
    wall_time_ms: float
    cpu_time_ms: float
    peak_memory_mb: float
    memory_delta_mb: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowProfiler:
    """
    Manages performance profiling across multiple execution stages of a simulation.
    """

    def __init__(self, workflow_name: str = "route_consumption_pipeline") -> None:
        self.workflow_name: str = workflow_name
        self.stages: List[StageMetrics] = []
        self._global_start_wall: float = time.perf_counter()

    @contextmanager
    def stage(self, stage_name: str, **metadata: Any):
        """
        Context manager to measure time and memory footprint of a specific stage.

        Usage:
            with profiler.stage("provider_weather_fetch", provider="OpenWeatherAPI"):
                weather_data = provider.get_weather(...)
        """
        tracemalloc.start()
        start_wall = time.perf_counter()
        start_cpu = time.process_time()

        if psutil:
            process = psutil.Process(os.getpid())
            start_rss_bytes = process.memory_info().rss
        else:
            start_rss_bytes = 0.0

        try:
            yield
        finally:
            end_wall = time.perf_counter()
            end_cpu = time.process_time()

            current_mem, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            if psutil:
                process = psutil.Process(os.getpid())
                end_rss_bytes = process.memory_info().rss
                delta_bytes = end_rss_bytes - start_rss_bytes
            else:
                delta_bytes = current_mem

            wall_ms = (end_wall - start_wall) * 1000.0
            cpu_ms = (end_cpu - start_cpu) * 1000.0

            metric = StageMetrics(
                stage_name=stage_name,
                wall_time_ms=round(wall_ms, 3),
                cpu_time_ms=round(cpu_ms, 3),
                peak_memory_mb=round(peak_bytes / (1024.0 * 1024.0), 4),
                memory_delta_mb=round(delta_bytes / (1024.0 * 1024.0), 4),
                metadata=metadata,
            )
            self.stages.append(metric)

    def to_dict(self) -> Dict[str, Any]:
        """Generate structured JSON report summarizing individual stages and totals."""
        total_wall_ms = sum(s.wall_time_ms for s in self.stages)
        total_cpu_ms = sum(s.cpu_time_ms for s in self.stages)
        max_peak_mem_mb = max((s.peak_memory_mb for s in self.stages), default=0.0)

        return {
            "workflow": self.workflow_name,
            "summary": {
                "total_wall_time_ms": round(total_wall_ms, 3),
                "total_cpu_time_ms": round(total_cpu_ms, 3),
                "max_stage_peak_memory_mb": round(max_peak_mem_mb, 4),
                "num_stages_executed": len(self.stages),
                "environment": {
                    "cpu_count": os.cpu_count() or 1,
                    "python_version": platform.python_version(),
                    "system_platform": platform.system(),
                },
            },
            "stages": [asdict(s) for s in self.stages],
        }