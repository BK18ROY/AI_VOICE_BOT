"""Latency benchmarking script executing real turns and calculating statistical percentiles."""

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import get_settings
from app.conversation.state import create_initial_state
from app.pipeline.audio_transport import BaseAudioTransport
from app.pipeline.pipeline_factory import create_voice_pipeline
from app.schemas.responses import ServerEventType

BENCHMARK_PROMPTS = [
    "Can you check the warranty status for SN-5521?",
    "Please tell me my EMI status for account ACC-101.",
    "My car has broken down on Highway 48, I need roadside assistance.",
    "Customer ka service request status kya hai for JC-7711?",
    "What is the delivery status for order ORD-9982?",
    "Achha Hindi mein batao meri gaadi ka loan status kya hai?",
    "Where is the nearest authorized dealer and workshop?",
    "Can you check if the infotainment console is in stock?",
]


class BenchmarkTransport(BaseAudioTransport):
    def __init__(self):
        self.received_audio_count = 0
        self.latest_tts_complete_event = None

    async def send_audio(self, audio_bytes: bytes) -> None:
        self.received_audio_count += 1

    async def send_event(self, event_type: ServerEventType, data: Optional[Dict[str, Any]] = None) -> None:
        if event_type == ServerEventType.TTS_COMPLETE:
            self.latest_tts_complete_event = data

    async def close(self) -> None:
        pass

    @property
    def is_active(self) -> bool:
        return True


def compute_stats(values: List[float]) -> Dict[str, float]:
    """Compute min, max, mean, median, p95, p99 for a list of latency measurements."""
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0, "p99": 0.0}
    arr = np.array(values)
    return {
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "mean": round(float(np.mean(arr)), 2),
        "median": round(float(np.median(arr)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "p99": round(float(np.percentile(arr, 99)), 2),
    }


async def run_benchmark(num_runs: int = 20) -> Dict[str, Any]:
    print(f"[*] Starting latency benchmark with {num_runs} simulated conversational runs...")
    cfg = get_settings()

    e2e_latencies = []
    stt_latencies = []
    llm_ttft_latencies = []
    llm_total_latencies = []
    tts_ttfa_latencies = []

    out_metrics_dir = Path(cfg.metrics_dir)
    out_metrics_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_metrics_dir / "latency_report.csv"
    json_path = out_metrics_dir / "latency_report.json"

    raw_records = []

    for i in range(num_runs):
        session_id = f"bench_sess_{i+1}"
        transport = BenchmarkTransport()
        state = create_initial_state(session_id=session_id)
        pipeline = create_voice_pipeline(
            session_id=session_id,
            transport=transport,
            state=state,
            settings=cfg,
        )

        prompt = BENCHMARK_PROMPTS[i % len(BENCHMARK_PROMPTS)]
        start_ts = time.perf_counter()
        await pipeline.process_text_input(prompt)
        await asyncio.sleep(0.05)

        event_data = transport.latest_tts_complete_event or {}
        breakdown = event_data.get("latency_breakdown", {})

        e2e = breakdown.get("end_to_end_ms")
        stt = breakdown.get("stt_latency_ms")
        llm_ttft = breakdown.get("llm_ttft_ms")
        llm_tot = breakdown.get("llm_total_ms")
        tts_ttfa = breakdown.get("tts_ttfa_ms")

        if e2e:
            e2e_latencies.append(e2e)
        if stt:
            stt_latencies.append(stt)
        if llm_ttft:
            llm_ttft_latencies.append(llm_ttft)
        if llm_tot:
            llm_total_latencies.append(llm_tot)
        if tts_ttfa:
            tts_ttfa_latencies.append(tts_ttfa)

        raw_records.append({
            "run": i + 1,
            "session_id": session_id,
            "prompt": prompt,
            "e2e_ms": e2e,
            "stt_ms": stt,
            "llm_ttft_ms": llm_ttft,
            "tts_ttfa_ms": tts_ttfa,
        })

        print(f"  [Run {i+1:02d}/{num_runs}] Prompt: '{prompt[:32]}...' -> E2E: {e2e}ms | LLM TTFT: {llm_ttft}ms | TTS TTFA: {tts_ttfa}ms")

    # Generate Statistical Breakdown
    stats = {
        "benchmark_timestamp": time.time(),
        "total_runs": num_runs,
        "environment": "mock_mode" if cfg.enable_mock_stt else "live_providers",
        "metrics": {
            "end_to_end_latency_ms": compute_stats(e2e_latencies),
            "stt_latency_ms": compute_stats(stt_latencies),
            "llm_time_to_first_token_ms": compute_stats(llm_ttft_latencies),
            "llm_total_latency_ms": compute_stats(llm_total_latencies),
            "tts_time_to_first_audio_ms": compute_stats(tts_ttfa_latencies),
        },
    }

    # Save to JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    # Save to CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["run", "session_id", "prompt", "e2e_ms", "stt_ms", "llm_ttft_ms", "tts_ttfa_ms"])
        writer.writeheader()
        writer.writerows(raw_records)

    print("\n" + "=" * 65)
    print("LATENCY BENCHMARK REPORT SUMMARY (All units in ms)")
    print("=" * 65)
    print(f"{'Metric':<28} | {'Min':>6} | {'Mean':>6} | {'Median':>6} | {'P95':>6} | {'Max':>6}")
    print("-" * 65)
    for name, s in stats["metrics"].items():
        print(f"{name:<28} | {s['min']:>6.1f} | {s['mean']:>6.1f} | {s['median']:>6.1f} | {s['p95']:>6.1f} | {s['max']:>6.1f}")
    print("=" * 65)
    print(f"[OK] Report saved to:")
    print(f"     - {json_path}")
    print(f"     - {csv_path}\n")

    return stats


def main():
    parser = argparse.ArgumentParser(description="AI Voice Bot Latency Benchmark")
    parser.add_argument("--runs", type=int, default=20, help="Number of benchmark dialogue runs")
    args = parser.parse_args()
    asyncio.run(run_benchmark(num_runs=args.runs))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
