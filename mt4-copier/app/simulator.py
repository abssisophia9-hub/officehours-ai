"""Fake master stream and an in-process slave that acknowledges commands."""

from __future__ import annotations

from pathlib import Path

from app.bridge import (
    atomic_write_json,
    commands_path,
    fills_path,
    read_jsonl,
    snapshot_path,
    status_path,
)
from app.engine import Engine, _now

SIM_SLAVE_ID = "sim-demo"


def publish_master(
    copier: Path,
    orders: list[dict],
    *,
    account: int = 10001,
    balance: float = 10000.0,
    equity: float = 10000.0,
    comment_tag: str = "simulate",
) -> None:
    """Write the same snapshot and heartbeat files the master EA writes."""
    atomic_write_json(
        snapshot_path(copier),
        {
            "time": _now(),
            "account": account,
            "comment_tag": comment_tag,
            "orders": orders,
        },
    )
    atomic_write_json(
        status_path(copier),
        {
            "time": _now(),
            "account": account,
            "balance": balance,
            "equity": equity,
            "order_count": len(orders),
            "comment_tag": comment_tag,
            "trade_allowed": True,
        },
    )


def scenario_orders() -> list[list[dict]]:
    """Open, modify stop loss, partial close, then full close."""
    opened = {
        "ticket": 1001,
        "symbol": "EURUSD",
        "type": "BUY",
        "lots": 1.0,
        "open_price": 1.1000,
        "sl": 1.0900,
        "tp": 1.1200,
        "comment": "manager",
        "magic": 0,
        "open_time": "2026-09-25T12:00:00Z",
    }
    modified = dict(opened)
    modified["sl"] = 1.0950
    partial = dict(modified)
    partial["lots"] = 0.4
    return [[], [opened], [modified], [partial], []]


class SlaveSimulator:
    """Stand-in for SlaveCopier.mq4: read commands, append fills, remember tickets."""

    def __init__(self, copier: Path, slave_id: str = SIM_SLAVE_ID, first_ticket: int = 91001):
        self.copier = Path(copier)
        self.slave_id = slave_id
        self.next_ticket = first_ticket
        self.map: dict[int, int] = {}
        self.processed: set[str] = set()
        self._load()

    def _load(self) -> None:
        for row in read_jsonl(fills_path(self.copier, self.slave_id)):
            cid = row.get("command_id")
            if cid:
                self.processed.add(str(cid))
            if row.get("ok") and row.get("event") == "OPEN" and row.get("slave_ticket"):
                master = int(row["master_ticket"])
                slave = int(row["slave_ticket"])
                self.map[master] = slave
                if slave >= self.next_ticket:
                    self.next_ticket = slave + 1

    def poll(self) -> list[dict]:
        written: list[dict] = []
        for command in read_jsonl(commands_path(self.copier, self.slave_id)):
            cid = str(command.get("id") or "")
            if not cid or cid in self.processed:
                continue
            fill = self._ack(command)
            self.processed.add(cid)
            written.append(fill)
        return written

    def _ack(self, command: dict) -> dict:
        event = command.get("event")
        master = int(command["master_ticket"])
        slave_ticket = 0
        ok = True
        message = "ok"
        if event == "OPEN":
            if master in self.map:
                slave_ticket = self.map[master]
                message = "already open"
            else:
                slave_ticket = self.next_ticket
                self.next_ticket += 1
                self.map[master] = slave_ticket
        elif event in ("MODIFY", "PARTIAL", "CLOSE"):
            slave_ticket = self.map.get(master, 0)
            if not slave_ticket:
                ok = False
                message = "no slave ticket for master ticket"
            elif event == "CLOSE":
                message = "closed"
        else:
            ok = False
            message = "unknown event"
        fill = {
            "command_id": command["id"],
            "ok": ok,
            "slave_ticket": slave_ticket,
            "master_ticket": master,
            "event": event,
            "error_code": 0 if ok else 1,
            "retcode": 0 if ok else 1,
            "message": message,
            "time": _now(),
        }
        from app.bridge import append_jsonl

        append_jsonl(fills_path(self.copier, self.slave_id), fill)
        return fill


def ensure_sim_subscriber(engine: Engine, slave_id: str = SIM_SLAVE_ID) -> None:
    """Create the fake subscriber and record authorization for the in-process account only."""
    if engine.store.get(slave_id) is None:
        engine.store.add(
            {
                "display_name": "Simulated subscriber",
                "slave_id": slave_id,
                "lot_mode": "multiplier",
                "multiplier": 1.0,
                "fixed_lot": 0.01,
                "max_lot": 10.0,
                "min_lot": 0.01,
                "lot_step": 0.01,
            }
        )
    engine.store.update(
        slave_id,
        {
            "authorized": True,
            "enabled": True,
            "display_name": "Simulated subscriber",
            "lot_mode": "multiplier",
            "multiplier": 1.0,
        },
    )


def run_scenario(
    engine: Engine,
    slave: SlaveSimulator | None = None,
    snapshots: list[list[dict]] | None = None,
) -> dict:
    """Publish each snapshot, copy it, and let the fake slave acknowledge."""
    if slave is None:
        slave = SlaveSimulator(engine.copier, SIM_SLAVE_ID)
    if snapshots is None:
        snapshots = scenario_orders()
    for orders in snapshots:
        publish_master(engine.copier, orders)
        engine.poll()
        slave.poll()
        engine.ingest_fills()
    commands = read_jsonl(commands_path(engine.copier, slave.slave_id))
    fills = read_jsonl(fills_path(engine.copier, slave.slave_id))
    return {
        "commands": commands,
        "fills": fills,
        "mapping": dict(engine.mappings.get(slave.slave_id, {})),
    }
