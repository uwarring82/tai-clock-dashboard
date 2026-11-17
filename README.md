# TAI Clock Dashboard

## Public dashboard

[Open the TAI Clock Dashboard](https://tai-clock-dashboard.uwarring.chatgpt.site). It shows the device-based UTC and TAI clocks, the published offset, and BIPM's aggregate scale-interval and steering figures. Publication snapshots show the date they were checked. The static source is in [`public/`](public/).

## Clearance notice

This is an independent research project. We have no official BIPM endorsement or clearance to reuse data submitted by contributing laboratories. The public page cites aggregate BIPM results and links to the original archives. Consult the [BIPM Time Department reuse notice](https://www.bipm.org/en/time-ftp) for submitted records.

A research dashboard for the atomic clocks that contribute to International Atomic Time (TAI). The historical views bring together reported clock phase, declared events, observation status and monthly ensemble weights.

The public page is a static summary of published BIPM and IERS results. This branch, `synthetic-history`, adds a synthetic-data pilot of the historical views (no submitted clock records).

**Starting work?** Read the [contributor handoff](HANDOFF.md). It describes the first pull request, the October 2026 audit, and the conditions for using submitted clock data or starting the weight replay.

## Limits and honest claims

- The ticking clocks are the visitor's device clock, not a UTC realization; its error is unknown.
- Values are copied by hand from Circular T 466 and Bulletin C 72 and go stale when the next issues appear (dates on the page).
- The page is not endorsed by BIPM or IERS.
- No laboratory-submitted clock records are used or stored here; the pilot below runs on synthetic fixtures only.
- The HANDOFF's power estimate is not reproducible from this repository. Its script, seed and assumptions must be supplied and the estimate reproduced before use.

## Run locally

Serve `public/` over HTTP, for example:

```sh
python3 -m http.server --directory public 8000
```

Open http://localhost:8000. The ES module does not load from `file://`. Run the page tests with `node --test` (Node 22 or later).

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

## Licence and citation

The code is under MIT ([LICENSE](LICENSE)); the text and original figures are under CC BY 4.0 ([LICENSE-docs.md](LICENSE-docs.md)). BIPM and IERS material is under its own terms ([NOTICE.md](NOTICE.md)). Cite via [CITATION.cff](CITATION.cff).
