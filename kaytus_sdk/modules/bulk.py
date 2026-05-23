"""Bulk operations across multiple Kaytus BMC hosts.

    from kaytus_sdk import bulk_run, ip_range, bulk_summary

    hosts   = ip_range("10.255.40", 100, 130)
    results = bulk_run(hosts, "admin", "Pwd@10000",
                       lambda c: c.system.overview())
    print(bulk_summary(results))
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from ..client import KaytusClient
from ..exceptions import KaytusError

log = logging.getLogger(__name__)


def bulk_run(
    hosts: list[str],
    username: str,
    password: str,
    operation: Callable[[KaytusClient], Any],
    *,
    port: int = 443,
    timeout: int = 10,
    max_workers: int = 20,
    stagger_delay: float = 0.2,
) -> dict[str, Any]:
    """
    Run operation(client) against every host concurrently.

    Returns dict keyed by host IP:
      - operation result on success
      - {"error": "<message>"} on failure
    """
    results: dict[str, Any] = {}
    lock = threading.Lock()
    sem  = threading.Semaphore(max_workers)

    def _worker(host: str):
        with sem:
            try:
                with KaytusClient(host, username, password, port=port, timeout=timeout) as c:
                    result = operation(c)
                with lock:
                    results[host] = result
                log.info(f"[{host}] OK")
            except KaytusError as e:
                with lock:
                    results[host] = {"error": str(e)}
                log.warning(f"[{host}] {e}")
            except Exception as e:
                with lock:
                    results[host] = {"error": f"Unexpected: {e}"}
                log.error(f"[{host}] Unexpected: {e}")

    threads = [
        threading.Thread(target=_worker, args=(h,), daemon=True)
        for h in hosts
    ]
    for t in threads:
        t.start()
        if stagger_delay > 0:
            time.sleep(stagger_delay)
    for t in threads:
        t.join(timeout=timeout + 30)

    return results


def ip_range(base: str, start: int, end: int) -> list[str]:
    """ip_range("192.168.40", 100, 130)  →  ["192.168.40.100", ..., "192.168.40.130"]"""
    return [f"{base}.{i}" for i in range(start, end + 1)]


def bulk_summary(results: dict[str, Any]) -> dict:
    """Summarise bulk_run results into ok / failed counts."""
    ok   = {h: v for h, v in results.items() if not (isinstance(v, dict) and "error" in v)}
    fail = {h: v for h, v in results.items() if isinstance(v, dict) and "error" in v}
    return {
        "total":      len(results),
        "ok":         len(ok),
        "failed":     len(fail),
        "ok_hosts":   list(ok.keys()),
        "fail_hosts": {h: v["error"] for h, v in fail.items()},
    }
