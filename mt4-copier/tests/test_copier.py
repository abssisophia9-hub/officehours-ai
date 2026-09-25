"""Unit tests for the local MT4 copier. No terminal required."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bridge import read_jsonl  # noqa: E402
from app.commands import build_command, command_id  # noqa: E402
from app.diff import diff_orders  # noqa: E402
from app.engine import Engine  # noqa: E402
from app.lots import scale_lots  # noqa: E402
from app.server import AUTH_LABEL, PAGE, CopierHandler  # noqa: E402
from app.simulator import SlaveSimulator, publish_master, run_scenario  # noqa: E402
from app.store import AuthorizationError, SubscriberStore  # noqa: E402
from app.symbols import map_symbol  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402


def order(**kwargs) -> dict:
    base = {
        "ticket": 1,
        "symbol": "EURUSD",
        "type": "BUY",
        "lots": 1.0,
        "open_price": 1.1,
        "sl": 1.0,
        "tp": 1.2,
        "comment": "",
        "magic": 0,
        "open_time": "t",
    }
    base.update(kwargs)
    return base


def subscriber(**kwargs) -> dict:
    base = {
        "display_name": "Demo",
        "slave_id": "demo",
        "lot_mode": "multiplier",
        "multiplier": 1.0,
        "fixed_lot": 0.01,
        "max_lot": 10.0,
        "min_lot": 0.01,
        "lot_step": 0.01,
        "symbol_prefix": "",
        "symbol_suffix": "",
        "symbol_map": {},
        "enabled": True,
        "authorized": True,
    }
    base.update(kwargs)
    return base


class DiffTests(unittest.TestCase):
    def test_open_modify_partial_close_and_noop(self):
        opened = order(ticket=7, lots=1.0, sl=1.0, open_price=1.1)
        modified = order(ticket=7, lots=1.0, sl=1.05, open_price=1.1)
        partial = order(ticket=7, lots=0.4, sl=1.05, open_price=1.1)
        self.assertEqual([event["event"] for event in diff_orders([], [opened])], ["OPEN"])
        self.assertEqual([event["event"] for event in diff_orders([opened], [modified])], ["MODIFY"])
        partial_events = diff_orders([modified], [partial])
        self.assertEqual([event["event"] for event in partial_events], ["PARTIAL"])
        self.assertAlmostEqual(partial_events[0]["close_lots"], 0.6)
        self.assertEqual([event["event"] for event in diff_orders([partial], [])], ["CLOSE"])
        self.assertEqual(diff_orders([opened], [opened]), [])
        comment_only = order(ticket=7, lots=1.0, sl=1.0, open_price=1.1, comment="note")
        self.assertEqual(diff_orders([opened], [comment_only]), [])
        price = order(ticket=7, lots=1.0, sl=1.0, open_price=1.11)
        self.assertEqual([event["event"] for event in diff_orders([opened], [price])], ["MODIFY"])

    def test_modify_and_partial_together(self):
        before = order(ticket=3, lots=1.0, sl=1.0)
        after = order(ticket=3, lots=0.5, sl=1.02)
        kinds = [event["event"] for event in diff_orders([before], [after])]
        self.assertEqual(kinds, ["MODIFY", "PARTIAL"])

    def test_lot_increase_is_not_an_event(self):
        before = order(lots=0.4)
        after = order(lots=0.8)
        self.assertEqual(diff_orders([before], [after]), [])


class CommandIdTests(unittest.TestCase):
    def test_same_event_twice_is_one_id_and_one_file_line(self):
        self.assertEqual(command_id("OPEN", 11), command_id("OPEN", 11))
        self.assertNotEqual(command_id("OPEN", 11), command_id("CLOSE", 11))
        self.assertEqual(
            command_id("MODIFY", 11, price=1.1, sl=1.0, tp=1.2),
            command_id("MODIFY", 11, price=1.1, sl=1.0, tp=1.2),
        )
        self.assertNotEqual(
            command_id("MODIFY", 11, price=1.1, sl=1.0, tp=1.2),
            command_id("MODIFY", 11, price=1.1, sl=1.05, tp=1.2),
        )
        with tempfile.TemporaryDirectory() as tmp:
            engine = Engine(Path(tmp) / "bus", Path(tmp) / "data")
            engine.store.add(subscriber(slave_id="demo"))
            engine.store.update("demo", {"authorized": True, "enabled": True})
            sub = engine.store.get("demo")
            event = {"event": "OPEN", "ticket": 11, "order": order(ticket=11)}
            first = engine.handle_events(sub, [event])
            second = engine.handle_events(sub, [event])
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            engine.seen_ids = {}
            third = engine.handle_events(sub, [event])
            self.assertEqual(third, [])
            rows = read_jsonl(Path(tmp) / "bus" / "commands" / "demo.jsonl")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], first[0]["id"])


class LotTests(unittest.TestCase):
    def test_multiplier_fixed_and_clamp(self):
        self.assertEqual(scale_lots(0.4, "multiplier", 0.5, 0.01, 0.01, 10, 0.01), 0.2)
        self.assertEqual(scale_lots(1.25, "fixed", 2, 0.07, 0.01, 10, 0.01), 0.07)
        self.assertEqual(scale_lots(2, "multiplier", 1, 0.01, 0.01, 0.5, 0.01), 0.5)
        self.assertEqual(scale_lots(0.01, "multiplier", 0.2, 0.01, 0.01, 10, 0.01), 0.01)
        self.assertEqual(scale_lots(0.24, "multiplier", 1, 0.01, 0.01, 10, 0.1), 0.2)
        self.assertEqual(scale_lots(0.25, "multiplier", 1, 0.01, 0.01, 10, 0.1), 0.3)
        self.assertEqual(scale_lots(0.99, "multiplier", 1, 0.01, 0.01, 0.95, 0.1), 0.9)
        self.assertEqual(scale_lots(1, "multiplier", 0, 0.01, 0.01, 10, 0.01), 0.0)


class SymbolTests(unittest.TestCase):
    def test_prefix_suffix_and_explicit_map(self):
        self.assertEqual(map_symbol("EURUSD", "", ".raw"), "EURUSD.raw")
        self.assertEqual(map_symbol("EURUSD", "pro", ""), "proEURUSD")
        self.assertEqual(map_symbol("EURUSD", "", ""), "EURUSD")
        mapped = map_symbol("EURUSD", "x", ".y", {"EURUSD": "EURUSD.r"})
        self.assertEqual(mapped, "EURUSD.r")
        self.assertEqual(map_symbol("GBPUSD", "x", ".y", {"EURUSD": "EURUSD.r"}), "xGBPUSD.y")
        self.assertEqual(map_symbol("gold", "", "", {"GOLD": "XAUUSD"}), "XAUUSD")


class RestartTests(unittest.TestCase):
    def test_existing_mapping_does_not_open_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = Path(tmp) / "bus"
            data = Path(tmp) / "data"
            engine = Engine(bus, data)
            engine.store.add(subscriber())
            engine.store.update("demo", {"authorized": True, "enabled": True})
            sub = engine.store.get("demo")
            engine.mappings["demo"] = {42: 9001}
            event = {"event": "OPEN", "ticket": 42, "order": order(ticket=42, lots=0.2)}
            self.assertEqual(engine.plan_commands(sub, [event]), [])

            fill = {
                "command_id": "already",
                "ok": True,
                "slave_ticket": 9001,
                "master_ticket": 42,
                "event": "OPEN",
                "error_code": 0,
                "retcode": 0,
                "message": "ok",
            }
            (bus / "fills").mkdir(parents=True, exist_ok=True)
            (bus / "fills" / "demo.jsonl").write_text(json.dumps(fill) + "\n", encoding="utf-8")
            restarted = Engine(bus, data)
            restarted.last_orders = {}
            restarted._baseline_done = True
            publish_master(bus, [order(ticket=42, lots=0.2)])
            restarted.poll()
            self.assertEqual(read_jsonl(bus / "commands" / "demo.jsonl"), [])
            self.assertEqual(restarted.mappings["demo"][42], 9001)

    def test_first_snapshot_is_a_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = Path(tmp) / "bus"
            engine = Engine(bus, Path(tmp) / "data")
            engine.store.add(subscriber())
            engine.store.update("demo", {"authorized": True, "enabled": True})
            publish_master(bus, [order(ticket=5)])
            engine.poll()
            self.assertEqual(read_jsonl(bus / "commands" / "demo.jsonl"), [])
            publish_master(bus, [order(ticket=5), order(ticket=6)])
            engine.poll()
            rows = read_jsonl(bus / "commands" / "demo.jsonl")
            self.assertEqual([row["event"] for row in rows], ["OPEN"])
            self.assertEqual(rows[0]["master_ticket"], 6)

    def test_pause_does_not_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            bus = Path(tmp) / "bus"
            engine = Engine(bus, Path(tmp) / "data")
            engine.store.add(subscriber())
            engine.store.update("demo", {"authorized": True, "enabled": True})
            publish_master(bus, [])
            engine.poll()
            engine.set_control("pause")
            publish_master(bus, [order(ticket=8)])
            engine.poll()
            self.assertEqual(read_jsonl(bus / "commands" / "demo.jsonl"), [])
            engine.set_control("resume")
            engine.poll()
            self.assertEqual(read_jsonl(bus / "commands" / "demo.jsonl"), [])

    def test_enable_requires_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SubscriberStore(Path(tmp) / "subscribers.json")
            created = store.add(subscriber(slave_id="alex"))
            self.assertFalse(created["enabled"])
            self.assertFalse(created["authorized"])
            with self.assertRaises(AuthorizationError):
                store.update("alex", {"enabled": True, "authorized": False})
            enabled = store.update("alex", {"authorized": True, "enabled": True})
            self.assertTrue(enabled["enabled"])


class SimulatorTests(unittest.TestCase):
    def test_open_modify_partial_close_maps_the_fill(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Engine(Path(tmp) / "bus", Path(tmp) / "data")
            engine.store.add(subscriber())
            engine.store.update("demo", {"authorized": True, "enabled": True})
            slave = SlaveSimulator(engine.copier, "demo", first_ticket=91001)
            result = run_scenario(engine, slave)
            events = [row["event"] for row in result["commands"]]
            self.assertEqual(events, ["OPEN", "MODIFY", "PARTIAL", "CLOSE"])
            opened, modified, partial, closed = result["commands"]
            self.assertEqual(opened["symbol"], "EURUSD")
            self.assertAlmostEqual(opened["lots"], 1.0)
            self.assertTrue(opened["mapped"])
            self.assertAlmostEqual(modified["sl"], 1.095)
            self.assertAlmostEqual(partial["close_lots"], 0.6)
            self.assertAlmostEqual(partial["lots"], 0.4)
            self.assertEqual(closed["event"], "CLOSE")
            self.assertEqual(result["mapping"][1001], 91001)
            open_fills = [row for row in result["fills"] if row["event"] == "OPEN" and row["ok"]]
            self.assertEqual(open_fills[0]["slave_ticket"], 91001)
            again = run_scenario(engine, SlaveSimulator(engine.copier, "demo"))
            self.assertEqual([row["event"] for row in again["commands"]], events)
            self.assertEqual(len(again["commands"]), 4)
            self.assertEqual(again["mapping"][1001], 91001)

    def test_symbol_and_lots_are_applied_on_the_command(self):
        event = {"event": "OPEN", "ticket": 3, "order": order(ticket=3, symbol="GOLD", lots=1.0)}
        command = build_command(
            event,
            subscriber(
                lot_mode="multiplier",
                multiplier=0.5,
                max_lot=0.3,
                symbol_prefix="xx",
                symbol_suffix=".y",
                symbol_map={"GOLD": "XAUUSD"},
            ),
        )
        self.assertEqual(command["symbol"], "XAUUSD")
        self.assertAlmostEqual(command["lots"], 0.3)


class PageTests(unittest.TestCase):
    def test_page_explains_login_and_has_no_password_field(self):
        self.assertIn(AUTH_LABEL, PAGE)
        self.assertNotIn('type="password"', PAGE)
        self.assertNotIn("type='password'", PAGE)
        self.assertIn("account number cannot place trades", PAGE)
        self.assertIn("never asks for that password", PAGE)

    def test_http_rejects_enable_without_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Engine(Path(tmp) / "bus", Path(tmp) / "data")
            CopierHandler.engine = engine
            server = ThreadingHTTPServer(("127.0.0.1", 0), CopierHandler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode("utf-8")
                self.assertIn(AUTH_LABEL, page)
                self._post(port, "/api/subscribers", {"display_name": "Alex", "slave_id": "alex"})
                state = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state").read().decode())
                self.assertFalse(state["subscribers"][0]["enabled"])
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self._post(
                        port,
                        "/api/subscribers/update",
                        {"slave_id": "alex", "enabled": True, "authorized": False},
                    )
                self.assertEqual(caught.exception.code, 400)
                saved = self._post(
                    port,
                    "/api/subscribers/update",
                    {"slave_id": "alex", "enabled": True, "authorized": True},
                )
                self.assertTrue(saved["subscriber"]["enabled"])
            finally:
                server.shutdown()
                server.server_close()

    def _post(self, port: int, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))

