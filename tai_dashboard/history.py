"""Read historical snapshots with a release-availability cutoff."""

import sqlite3
from contextlib import closing
from pathlib import Path

PHASE_REFERENCE = "UTC(k) − clock"
PHASE_UNIT = "ns"

SELECTED = """
    WITH selected AS (
        SELECT r.*
        FROM release r
        WHERE r.available_at <= :as_of
          AND r.available_at = (
              SELECT MAX(available_at)
              FROM release
              WHERE period = r.period AND available_at <= :as_of
          )
    )
"""

WEIGHT_STATE = """CASE WHEN w.weight_percent IS NULL THEN 'unknown'
                       WHEN w.weight_percent = 0 THEN 'zero'
                       ELSE 'positive' END"""

OBSERVATIONS = """
    SELECT s.period, e.mjd, c.clock_code, a.lab, a.technology, o.phase_ns,
           o.exclusion_reason, w.weight_percent,
           CASE WHEN a.clock_code IS NULL THEN 'outside_roster'
                WHEN o.exclusion_reason IS NOT NULL THEN 'excluded'
                WHEN o.clock_code IS NULL THEN 'missing'
                ELSE 'observed' END AS observation_status,
           """ + WEIGHT_STATE + """ AS weight_status
    FROM selected s
    JOIN epoch e ON e.release_id = s.id
    CROSS JOIN visible_clocks c
    LEFT JOIN assignment a ON a.release_id = s.id
        AND a.mjd = e.mjd AND a.clock_code = c.clock_code
    LEFT JOIN observation o ON o.release_id = a.release_id
        AND o.mjd = a.mjd AND o.clock_code = a.clock_code
    LEFT JOIN official_weight w ON w.release_id = s.id AND w.clock_code = c.clock_code
"""

ALL_MEMBERS = """
    SELECT release_id, clock_code FROM assignment
    UNION SELECT release_id, clock_code FROM official_weight
    UNION SELECT release_id, clock_code FROM clock_step
"""


def read_only(database):
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    return closing(db)


def rows(db, query, parameters=()):
    return [dict(row) for row in db.execute(query, parameters)]


def release_options(db):
    return [row["available_at"] for row in db.execute(
        "SELECT DISTINCT available_at FROM release ORDER BY available_at DESC"
    )]


def metadata(db, as_of):
    return {
        "dataset": "synthetic",
        "as_of": as_of,
        "phase_reference": PHASE_REFERENCE,
        "phase_unit": PHASE_UNIT,
        "releases": rows(db, SELECTED + """
            SELECT period, revision, available_at, retrieved_at, source_url, sha256, parser_version
            FROM selected ORDER BY period
        """, {"as_of": as_of or "9999-12-31T23:59:59Z"}),
    }


def roster(db, as_of=None, period=None, mjd=None):
    result = metadata(db, as_of)
    periods = [release["period"] for release in result["releases"]]
    if period is not None and period not in periods:
        raise LookupError("No release for that period at this cutoff.")
    period = period or (periods[-1] if periods else None)
    params = {"as_of": as_of or "9999-12-31T23:59:59Z", "period": period}
    epochs = [row["mjd"] for row in db.execute(SELECTED + """
        SELECT e.mjd FROM epoch e JOIN selected s ON s.id = e.release_id
        WHERE s.period = :period ORDER BY e.mjd
    """, params)]
    if mjd is not None and mjd not in epochs:
        raise LookupError("No observation epoch for that period and MJD.")
    mjd = mjd if mjd is not None else (epochs[-1] if epochs else None)
    observations = rows(db, SELECTED + """
        , members AS (""" + ALL_MEMBERS + """),
        visible_clocks AS (
            SELECT DISTINCT m.clock_code FROM members m
            JOIN selected s ON s.id = m.release_id WHERE s.period = :period
        )
    """ + OBSERVATIONS + """
        WHERE s.period = :period AND e.mjd = :mjd ORDER BY c.clock_code
    """, {**params, "mjd": mjd})
    return {**result, "period": period, "mjd": mjd, "epochs": epochs, "clocks": observations}


def clock_history(db, code, as_of=None):
    result = metadata(db, as_of)
    params = {"as_of": as_of or "9999-12-31T23:59:59Z", "code": code}
    weights = rows(db, SELECTED + """
        , members AS (""" + ALL_MEMBERS + """)
        SELECT s.period, w.weight_percent, """ + WEIGHT_STATE + """ AS weight_status
        FROM selected s
        LEFT JOIN official_weight w ON w.release_id = s.id AND w.clock_code = :code
        WHERE EXISTS (
            SELECT 1 FROM selected v JOIN members m ON m.release_id = v.id
            WHERE m.clock_code = :code
        )
        ORDER BY s.period
    """, params)
    if not weights:
        raise LookupError("Clock unavailable at this cutoff.")
    observations = rows(db, SELECTED + """
        , visible_clocks AS (SELECT :code AS clock_code)
    """ + OBSERVATIONS + """ ORDER BY e.mjd
    """, params)
    steps = rows(db, SELECTED + """
        SELECT s.period, t.mjd, t.phase_step_ns, t.note
        FROM clock_step t JOIN selected s ON s.id = t.release_id
        WHERE t.clock_code = :code ORDER BY t.mjd
    """, params)
    return {**result, "clock_code": code, "observations": observations,
            "weights": weights, "steps": steps}
