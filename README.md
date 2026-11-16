# TAI Clock Dashboard

## Public dashboard

[Open the TAI Clock Dashboard](https://tai-clock-dashboard.uwarring.chatgpt.site). It shows the device-based UTC and TAI clocks, the published offset, and BIPM's aggregate scale-interval and steering figures. Publication snapshots show the date they were checked. The static source is in [`public/`](public/).

## Clearance notice

This is an independent research project. We have no official BIPM endorsement or clearance to reuse data submitted by contributing laboratories. The public page cites aggregate BIPM results and links to the original archives. Consult the [BIPM Time Department reuse notice](https://www.bipm.org/en/time-ftp) for submitted records.

A research dashboard for the atomic clocks that contribute to International Atomic Time (TAI). The planned historical views bring together clock measurements, declared events, data coverage, and published ensemble weights.

The public page is a static summary of published BIPM and IERS results. A synthetic-data pilot of the historical views is on the branch `synthetic-history` (no submitted clock records).

**Starting work?** Read the [contributor handoff](HANDOFF.md). It describes the first pull request, the October 2026 audit, and the conditions for using submitted clock data or starting the weight replay.

## Limits and honest claims

- The ticking clocks are the visitor's device clock, not a UTC realization; its error is unknown.
- Values are copied by hand from Circular T 466 and Bulletin C 72 and go stale when the next issues appear (dates on the page).
- The page is not endorsed by BIPM or IERS.
- No laboratory-submitted clock records are used or stored here.
- The HANDOFF's power estimate is not reproducible from this repository. Its script, seed and assumptions must be supplied and the estimate reproduced before use.

## Run locally

Serve `public/` over HTTP, for example:

```sh
python3 -m http.server --directory public 8000
```

Open http://localhost:8000. The ES module does not load from `file://`.

## Licence and citation

The code is under MIT ([LICENSE](LICENSE)); the text and original figures are under CC BY 4.0 ([LICENSE-docs.md](LICENSE-docs.md)). BIPM and IERS material is under its own terms ([NOTICE.md](NOTICE.md)). Cite via [CITATION.cff](CITATION.cff).
