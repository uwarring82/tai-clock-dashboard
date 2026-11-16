# TAI Clock Dashboard

## Public dashboard

[Open the TAI Clock Dashboard](https://tai-clock-dashboard.uwarring.chatgpt.site). It shows the device-based UTC and TAI clocks, the published offset, and BIPM's aggregate scale-interval and steering figures. Publication snapshots show the date they were checked. The static source is in [`public/`](public/).

## Clearance notice

This is an independent research project. We have no official BIPM endorsement or clearance to reuse data submitted by contributing laboratories. The public page cites aggregate BIPM results and links to the original archives. Consult the [BIPM Time Department reuse notice](https://www.bipm.org/en/time-ftp) for submitted records.

A research dashboard for the atomic clocks that contribute to International Atomic Time (TAI). The historical views bring together reported clock phase, declared events, observation status and monthly ensemble weights.

## Run the synthetic pilot

From the repository root, use Python 3.10 or newer. The pilot uses the standard library and SQLite.

```sh
python3 -m tai_dashboard build
python3 -m tai_dashboard serve
```

Open [the local dashboard](http://127.0.0.1:8000/). The roster shows one five-day epoch at a time. Select a clock to see its timeline across months. The October fixtures include a lab move, an off-grid clock step, a gap, an exclusion, and a revised phase and weight. The release cutoff changes which revisions are available in both views.

The synthetic manifest identifies each source by SHA-256 and records its availability and retrieval timestamps. Ingest verifies the bytes and builds a SQLite snapshot that the server opens read-only. Each fixture release is a complete snapshot for its month. The dashboard labels phase as `UTC(k) − clock` in ns and retains reported values, including flagged observations. Its weights are example percentages for a subset of a synthetic ensemble.

## October coverage audit

Open **Coverage audit** from the roster. For each epoch, the denominator is the archived monthly list of positively weighted clocks, or the sum of their monthly weights for weighted coverage. A clock contributes to the numerator when its observation is usable. The incomplete clock-months table lists every missing, excluded, or outside-roster epoch for each positively weighted clock.

In the revised synthetic October release, one of two positively weighted clocks is observed at every epoch. The count coverage stays at 50%, while the weight coverage is 46.05% or 53.95% depending on which clock is observed.

## Read-only API

- `GET /api/roster` accepts optional `period` (YYYY-MM), `mjd` (integer epoch) and `as_of`.
- `GET /api/clocks/SYN-A` returns the clock timeline, declared steps, and monthly weights with optional `as_of`.
- `GET /api/coverage` accepts optional `period` and `as_of`. It returns the monthly denominators, per-epoch numerators and fractions, and incomplete positive-weight clock-months. Fractions are `null` when the denominator is zero.
- Use a UTC release cutoff of the form `2026-11-08T12:00:00Z`. By default the endpoints select the latest available revision per month.

Run the tests with `python3 -m unittest discover -s tests -v`.

**Continuing development?** See the [contributor handoff](HANDOFF.md) for the October 2026 audit and the conditions for using submitted clock data or starting weight replay.
