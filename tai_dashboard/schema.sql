PRAGMA foreign_keys = ON;

CREATE TABLE release (
    id INTEGER PRIMARY KEY,
    period TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    available_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    source_url TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    UNIQUE (period, revision),
    UNIQUE (period, available_at)
);

CREATE TABLE epoch (
    release_id INTEGER NOT NULL REFERENCES release(id),
    mjd INTEGER NOT NULL,
    PRIMARY KEY (release_id, mjd)
);

CREATE TABLE clock (
    code TEXT PRIMARY KEY
);

CREATE TABLE assignment (
    release_id INTEGER NOT NULL,
    mjd INTEGER NOT NULL,
    clock_code TEXT NOT NULL REFERENCES clock(code),
    lab TEXT NOT NULL,
    technology TEXT NOT NULL,
    PRIMARY KEY (release_id, mjd, clock_code),
    FOREIGN KEY (release_id, mjd) REFERENCES epoch(release_id, mjd)
);

-- A missing row represents an absent report. An excluded row retains its provenance.
CREATE TABLE observation (
    release_id INTEGER NOT NULL,
    mjd INTEGER NOT NULL,
    clock_code TEXT NOT NULL,
    phase_ns REAL,
    exclusion_reason TEXT,
    CHECK (phase_ns IS NOT NULL OR exclusion_reason IS NOT NULL),
    PRIMARY KEY (release_id, mjd, clock_code),
    FOREIGN KEY (release_id, mjd, clock_code)
        REFERENCES assignment(release_id, mjd, clock_code)
);

-- A missing row represents unknown weight. A row with zero is a published value.
CREATE TABLE official_weight (
    release_id INTEGER NOT NULL REFERENCES release(id),
    clock_code TEXT NOT NULL REFERENCES clock(code),
    weight_percent REAL NOT NULL CHECK (weight_percent BETWEEN 0 AND 100),
    PRIMARY KEY (release_id, clock_code)
);

CREATE TABLE clock_step (
    release_id INTEGER NOT NULL REFERENCES release(id),
    clock_code TEXT NOT NULL REFERENCES clock(code),
    mjd REAL NOT NULL,
    phase_step_ns REAL NOT NULL,
    note TEXT NOT NULL,
    PRIMARY KEY (release_id, clock_code, mjd)
);
