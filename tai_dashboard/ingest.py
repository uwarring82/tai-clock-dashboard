"""Build a SQLite snapshot from checksummed synthetic releases."""

import hashlib
import json
import math
import re
import sqlite3
import tempfile
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

PARSER_VERSION = "synthetic-v1"
MJD_ZERO = date(1858, 11, 17)
RELEASE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")


def validate_cutoff(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
        raise ValueError("Use the UTC format YYYY-MM-DDTHH:MM:SSZ for the release cutoff.")
    datetime.strptime(value, RELEASE_FORMAT)
    return value


def finite_number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Expected a finite number.")
    return value


def clock_id(db, code):
    if not re.fullmatch(r"SYN-[A-Z0-9]+", code):
        raise ValueError(f"Expected a synthetic clock code, received {code!r}.")
    db.execute("INSERT OR IGNORE INTO clock VALUES (?)", (code,))
    return code


def insert_release(db, entry, payload):
    period = entry["period"]
    revision = entry["revision"]
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", period) or type(revision) is not int:
        raise ValueError("Expected a YYYY-MM period and integer revision.")
    month_start = date.fromisoformat(f"{period}-01")
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    first_mjd = (month_start - MJD_ZERO).days
    end_mjd = (next_month - MJD_ZERO).days
    available = validate_cutoff(entry["available_at"])
    retrieved = validate_cutoff(entry["retrieved_at"])
    if payload["period"] != period or payload["revision"] != revision or retrieved < available:
        raise ValueError("Manifest and release metadata disagree.")
    if not entry["source_url"].startswith("https://synthetic.invalid/"):
        raise ValueError("This parser accepts only synthetic sources.")

    epochs = payload["epochs"]
    if (not epochs or any(type(epoch) is not int or not first_mjd <= epoch < end_mjd for epoch in epochs)
            or any(later - earlier != 5 for earlier, later in zip(epochs, epochs[1:]))):
        raise ValueError("Expected a nonempty five-day MJD grid within the release month.")

    release_id = db.execute(
        """INSERT INTO release
           (period, revision, available_at, retrieved_at, source_url, sha256, parser_version)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (period, revision, available, retrieved, entry["source_url"], entry["sha256"], PARSER_VERSION),
    ).lastrowid
    db.executemany("INSERT INTO epoch VALUES (?, ?)", ((release_id, mjd) for mjd in epochs))

    for assignment in payload["assignments"]:
        code = clock_id(db, assignment["clock"])
        start, end = assignment["first_mjd"], assignment["last_mjd"]
        if start not in epochs or end not in epochs or start > end:
            raise ValueError(f"Invalid assignment bounds for {code}.")
        db.executemany(
            "INSERT INTO assignment VALUES (?, ?, ?, ?, ?)",
            ((release_id, mjd, code, assignment["lab"], assignment["technology"])
             for mjd in epochs if start <= mjd <= end),
        )

    for obs in payload["observations"]:
        phase = obs["phase_ns"]
        reason = obs.get("exclusion_reason")
        if phase is not None:
            finite_number(phase)
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise ValueError("An exclusion requires a reason.")
        db.execute("INSERT INTO observation VALUES (?, ?, ?, ?, ?)",
                   (release_id, obs["mjd"], obs["clock"], phase, reason))

    for code, weight in payload["weights_percent"].items():
        db.execute("INSERT INTO official_weight VALUES (?, ?, ?)",
                   (release_id, clock_id(db, code), finite_number(weight)))

    for step in payload["steps"]:
        mjd = finite_number(step["mjd"])
        if not first_mjd <= mjd < end_mjd:
            raise ValueError("A clock step must fall within its release month.")
        db.execute("INSERT INTO clock_step VALUES (?, ?, ?, ?, ?)",
                   (release_id, clock_id(db, step["clock"]), mjd,
                    finite_number(step["phase_step_ns"]), step["note"]))


def populate(db, manifest_path):
    manifest = json.loads(manifest_path.read_bytes())
    if manifest["format"] != PARSER_VERSION or not manifest["releases"]:
        raise ValueError("Expected a nonempty synthetic-v1 source manifest.")
    db.executescript(SCHEMA)
    with db:
        for entry in manifest["releases"]:
            name = entry["file"]
            if Path(name).name != name or not name.endswith(".json"):
                raise ValueError(f"Expected a JSON file beside the manifest: {name}")
            source = manifest_path.with_name(name).read_bytes()
            if hashlib.sha256(source).hexdigest() != entry["sha256"]:
                raise ValueError(f"SHA-256 mismatch for {name}.")
            insert_release(db, entry, json.loads(source))


def build_database(manifest_path, destination):
    """Publish the new snapshot only after every release has validated."""
    manifest_path = Path(manifest_path)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary_dir:
        snapshot = Path(temporary_dir) / "snapshot.sqlite3"
        with closing(sqlite3.connect(snapshot)) as db:
            populate(db, manifest_path)
        snapshot.replace(destination)
