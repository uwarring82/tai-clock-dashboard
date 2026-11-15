import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from tai_dashboard.history import clock_history, coverage, read_only, roster
from tai_dashboard.ingest import build_database
from tai_dashboard.web import handler_for

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MANIFEST = FIXTURES / "manifest.json"
FIRST_OCT_RELEASE = "2026-11-08T12:00:00Z"
REVISED_OCT_RELEASE = "2026-11-12T12:00:00Z"


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name)
        self.database = self.workspace / "tai.sqlite3"
        build_database(MANIFEST, self.database)

    def test_states_are_independent_and_move_preserves_identity(self):
        with read_only(self.database) as db:
            latest = roster(db)
            excluded = roster(db, mjd=latest["epochs"][-2])
            history = clock_history(db, "SYN-A")

        states = {record["clock_code"]: (record["observation_status"], record["weight_status"])
                  for record in latest["clocks"]}
        self.assertEqual(states, {"SYN-A": ("observed", "positive"),
                                  "SYN-B": ("observed", "zero"),
                                  "SYN-C": ("outside_roster", "unknown"),
                                  "SYN-D": ("missing", "positive")})
        flagged = next(record for record in excluded["clocks"] if record["clock_code"] == "SYN-A")
        self.assertEqual((flagged["observation_status"], flagged["phase_ns"]), ("excluded", 2.2))
        self.assertIn("receiver reset", flagged["exclusion_reason"])
        active_unknown = next(record for record in excluded["clocks"] if record["clock_code"] == "SYN-C")
        self.assertEqual((active_unknown["observation_status"], active_unknown["weight_status"]),
                         ("observed", "unknown"))
        october = [record for record in history["observations"] if record["period"] == "2026-10"]
        self.assertEqual((october[2]["lab"], october[3]["lab"]),
                         ("North Laboratory", "South Laboratory"))
        self.assertEqual(october[3]["observation_status"], "missing")
        self.assertIsNone(october[3]["phase_ns"])
        self.assertEqual(history["steps"][0]["phase_step_ns"], 1.25)
        self.assertLess(october[2]["mjd"], history["steps"][0]["mjd"])
        self.assertLess(history["steps"][0]["mjd"], october[3]["mjd"])
        self.assertEqual(october[-1]["phase_ns"], 3.1)

    def test_cutoff_includes_only_available_revisions_and_clocks(self):
        with read_only(self.database) as db:
            self.assertEqual(roster(db, "2026-10-01T00:00:00Z")["clocks"], [])
            with self.assertRaises(LookupError):
                clock_history(db, "SYN-D", "2026-11-08T11:59:59Z")
            first = clock_history(db, "SYN-A", FIRST_OCT_RELEASE)
            revised = clock_history(db, "SYN-A", REVISED_OCT_RELEASE)
        self.assertEqual([release["revision"] for release in first["releases"]], [1, 1])
        self.assertEqual([release["revision"] for release in revised["releases"]], [1, 2])
        self.assertEqual((first["observations"][-1]["phase_ns"], first["weights"][-1]["weight_percent"]),
                         (2.9, 0.38))
        self.assertEqual((revised["observations"][-1]["phase_ns"], revised["weights"][-1]["weight_percent"]),
                         (3.1, 0.41))
        self.assertEqual(first["phase_reference"], "UTC(k) − clock")
        self.assertEqual(first["phase_unit"], "ns")

    def test_coverage_reconciles_each_epoch_against_monthly_positive_weights(self):
        with read_only(self.database) as db:
            audit = coverage(db, period="2026-10")
            september = coverage(db, period="2026-09")

        self.assertEqual(audit["positive_weight_clocks"], 2)
        self.assertAlmostEqual(audit["total_positive_weight_percent"], 0.76)
        self.assertEqual([epoch["mjd"] for epoch in audit["epochs"]],
                         [61316, 61321, 61326, 61331, 61336, 61341])
        for epoch, weight in zip(audit["epochs"], (0.41, 0.41, 0.41, 0.35, 0.35, 0.41)):
            with self.subTest(mjd=epoch["mjd"]):
                self.assertEqual(epoch["observed_clocks"], 1)
                self.assertEqual(epoch["count_fraction"], 0.5)
                self.assertAlmostEqual(epoch["observed_weight_percent"], weight)
                self.assertAlmostEqual(epoch["weight_fraction"], weight / 0.76)

        gaps = {clock["clock_code"]: clock["issues"] for clock in audit["incomplete_clocks"]}
        self.assertEqual(list(gaps), ["SYN-A", "SYN-D"])
        self.assertEqual([issue["observation_status"] for issue in gaps["SYN-A"]],
                         ["missing", "excluded"])
        self.assertIn("receiver reset", gaps["SYN-A"][1]["exclusion_reason"])
        self.assertEqual([issue["observation_status"] for issue in gaps["SYN-D"]],
                         ["outside_roster", "outside_roster", "outside_roster", "missing"])
        self.assertEqual(september["epochs"][0]["count_fraction"], 1.0)
        self.assertEqual(september["epochs"][0]["weight_fraction"], 1.0)

    def test_coverage_with_no_positive_weight_has_undefined_fractions(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("DELETE FROM official_weight WHERE weight_percent > 0")
        with read_only(self.database) as db:
            audit = coverage(db, period="2026-10")
            before_first_release = coverage(db, as_of="2026-10-01T00:00:00Z")

        self.assertEqual(audit["positive_weight_clocks"], 0)
        self.assertEqual(audit["total_positive_weight_percent"], 0)
        self.assertEqual(audit["incomplete_clocks"], [])
        self.assertEqual(len(audit["epochs"]), 6)
        self.assertTrue(all(
            epoch["count_fraction"] is None and epoch["weight_fraction"] is None
            for epoch in audit["epochs"]
        ))
        self.assertEqual(before_first_release["epochs"], [])

    def test_failed_ingest_preserves_existing_snapshot(self):
        sources = self.workspace / "sources"
        shutil.copytree(FIXTURES, sources)
        (sources / "2026-10-r2.json").write_text("{}")
        baseline = self.database.read_bytes()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            build_database(sources / "manifest.json", self.database)
        self.assertEqual(self.database.read_bytes(), baseline)
        with read_only(self.database) as db, self.assertRaises(sqlite3.OperationalError):
            db.execute("DELETE FROM release")

    def test_http_views_and_errors(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.database)) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                address = f"http://127.0.0.1:{server.server_port}"
                with urlopen(address + "/", timeout=5) as response:
                    html = response.read().decode()
                    self.assertIn("Synthetic demonstration", html)
                    self.assertIn("Outside roster", html)
                    self.assertIn("0%", html)
                    self.assertIn("/clocks/SYN-A", html)
                    self.assertIn("/coverage?period=2026-10", html)
                with urlopen(address + "/clocks/SYN-A", timeout=5) as response:
                    html = response.read().decode()
                    self.assertLess(html.index("Declared step ·"), html.index(">Missing<"))
                    self.assertIn("0.41%", html)
                with urlopen(address + f"/api/clocks/SYN-A?as_of={FIRST_OCT_RELEASE}", timeout=5) as response:
                    self.assertEqual(response.headers.get_content_type(), "application/json")
                    self.assertEqual(json.load(response)["observations"][-1]["phase_ns"], 2.9)
                with urlopen(address + "/coverage?period=2026-10", timeout=5) as response:
                    html = response.read().decode()
                    self.assertIn("Coverage by epoch", html)
                    self.assertIn("53.95%", html)
                    self.assertIn("46.05%", html)
                    self.assertIn("receiver reset", html)
                first_audit = f"/api/coverage?period=2026-10&as_of={FIRST_OCT_RELEASE}"
                with urlopen(address + first_audit, timeout=5) as response:
                    first = json.load(response)
                    self.assertEqual(first["releases"][-1]["revision"], 1)
                    self.assertAlmostEqual(first["total_positive_weight_percent"], 0.73)
                    self.assertAlmostEqual(first["epochs"][0]["weight_fraction"], 0.38 / 0.73)
                for path, status in (
                    ("/api/roster?as_of=tomorrow", 400),
                    ("/api/roster?mjd=1", 404),
                    ("/api/coverage?period=2026-11", 404),
                    ("/api/clocks/unknown", 404),
                ):
                    with self.subTest(path=path), self.assertRaises(HTTPError) as context:
                        urlopen(address + path, timeout=5)
                    with context.exception as error:
                        self.assertEqual(error.code, status)
                        self.assertIn("error", json.load(error))
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
