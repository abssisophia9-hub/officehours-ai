"""Run the local copier UI, or one simulated copy from open through close."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading
from pathlib import Path

from app.bridge import copier_dir_from_env, data_dir, default_common_dir
from app.engine import Engine
from app.simulator import (
    SIM_SLAVE_ID,
    SlaveSimulator,
    ensure_sim_subscriber,
    publish_master,
    run_scenario,
    scenario_orders,
)


def _fresh(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_dirs(simulate: bool) -> tuple[Path, Path]:
    env_bus = copier_dir_from_env()
    env_data = os.environ.get("MT4_COPIER_DATA")
    if simulate and env_bus is None:
        bus = _fresh(data_dir() / "simulate-bus")
    else:
        bus = env_bus or default_common_dir()
        bus.mkdir(parents=True, exist_ok=True)
    if simulate and not env_data:
        stored = _fresh(data_dir() / "simulate")
    else:
        stored = Path(env_data) if env_data else data_dir()
        stored.mkdir(parents=True, exist_ok=True)
    if simulate and env_bus is not None:
        print("Simulate is using MT4_COPIER_DIR. Live slave terminals that share this folder will see the fake master.")
    return bus, stored


def _serve_simulation(engine: Engine, stop: threading.Event) -> None:
    slave = SlaveSimulator(engine.copier, SIM_SLAVE_ID)
    snaps = scenario_orders()
    last: list[dict] = []
    for orders in snaps:
        if stop.is_set():
            return
        last = orders
        publish_master(engine.copier, orders)
        engine.poll()
        slave.poll()
        engine.ingest_fills()
        stop.wait(0.4)
    while not stop.is_set():
        publish_master(engine.copier, last)
        engine.poll()
        slave.poll()
        engine.ingest_fills()
        stop.wait(1.0)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Local MT4 trade copier. No account passwords.")
    parser.add_argument("--simulate", action="store_true", help="Fake a master stream and a subscriber fill")
    parser.add_argument("--once", action="store_true", help="Run one simulated open, modify, partial, and close, then exit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.once:
        args.simulate = True
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        sys.exit("Refusing to bind anything except localhost")
    bind_host = "127.0.0.1" if args.host == "localhost" else args.host
    bus, stored = resolve_dirs(args.simulate)
    engine = Engine(bus, stored, simulate=args.simulate)
    if args.simulate:
        ensure_sim_subscriber(engine)
    if args.once:
        result = run_scenario(engine)
        events = [row["event"] for row in result["commands"]]
        print("commands:", " ".join(events))
        print("mapping:", result["mapping"])
        print("bus:", bus)
        if events != ["OPEN", "MODIFY", "PARTIAL", "CLOSE"] or 1001 not in result["mapping"]:
            sys.exit(1)
        print("simulate ok")
        return
    stop = threading.Event()
    if args.simulate:
        thread = threading.Thread(target=_serve_simulation, args=(engine, stop), daemon=True)
        thread.start()
    from app.server import serve

    try:
        serve(engine, bind_host, args.port)
    finally:
        stop.set()


if __name__ == "__main__":
    main()
