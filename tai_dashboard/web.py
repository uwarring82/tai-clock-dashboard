"""Server-rendered historical pages and a small read-only JSON API."""

import json
from datetime import timedelta
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from .history import PHASE_REFERENCE, clock_history, read_only, release_options, roster
from .ingest import MJD_ZERO, validate_cutoff


def h(value):
    return escape(str(value), quote=True)


def url(path, **filters):
    query = urlencode({key: value for key, value in filters.items() if value is not None})
    return f"{path}?{query}" if query else path


def page(title, content):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)} · TAI Clock Dashboard</title>
<style>
:root {{ color-scheme: light; font: 16px/1.5 system-ui, sans-serif; color: #182a35; background: #f4f7fa; }}
body {{ margin: 0; }}
main {{ max-width: 72rem; margin: auto; padding: clamp(1rem, 4vw, 3rem); }}
h1 {{ margin: .25rem 0 0; line-height: 1.15; font-size: clamp(2rem, 5vw, 3.25rem); }}
h2 {{ margin-top: 2rem; }}
a {{ color: #07598a; }}
.banner {{ color: #415970; font-size: .9rem; font-weight: 600; }}
form {{ display: flex; flex-wrap: wrap; gap: .8rem; align-items: end; margin: 1.5rem 0; }}
label {{ display: grid; gap: .2rem; font-size: .9rem; font-weight: 600; }}
select, button {{ padding: .5rem; font: inherit; background: white; border: 1px solid #688596; border-radius: .25rem; }}
button {{ background: #173950; color: white; cursor: pointer; }}
.scroll {{ overflow-x: auto; margin-bottom: 1rem; }}
table {{ width: 100%; border-collapse: collapse; background: white; font-variant-numeric: tabular-nums; }}
th, td {{ padding: .6rem .8rem; border-bottom: 1px solid #d6e1e9; text-align: left; }}
thead {{ background: #e5edf4; }}
small {{ color: #415970; }}
.event {{ background: #fff7e5; }}
</style>
</head>
<body><main>
<div class="banner">TAI Clock Dashboard · Synthetic demonstration</div>
<h1>{h(title)}</h1>
{content}
</main></body>
</html>
"""


def table(headings, body):
    header = "".join(f'<th scope="col">{h(label)}</th>' for label in headings)
    return f'<div class="scroll"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>'


def row(*cells, event=False):
    content = "".join(f"<td>{cell}</td>" for cell in cells)
    attributes = ' class="event"' if event else ""
    return f"<tr{attributes}>{content}</tr>"


def select(label, name, values, selected, empty=None):
    options = f'<option value="">{h(empty)}</option>' if empty else ""
    for value, caption in values:
        flag = " selected" if value == selected else ""
        options += f'<option value="{h(value)}"{flag}>{h(caption)}</option>'
    return f'<label>{h(label)} <select name="{h(name)}">{options}</select></label>'


def cutoff_select(releases, as_of):
    options = [(stamp, stamp.replace("T", " ").replace("Z", " UTC")) for stamp in releases]
    if as_of and as_of not in releases:
        options.insert(0, (as_of, as_of))
    return select("Releases available by", "as_of", options, as_of, "Latest available")


def observation_label(item):
    label = item["observation_status"].replace("_", " ").capitalize()
    if item["exclusion_reason"]:
        return f"{h(label)}<br><small>{h(item['exclusion_reason'])}</small>"
    return h(label)


def date_label(mjd):
    return h(f"{MJD_ZERO + timedelta(days=int(mjd))} ({mjd:g})")


def number(value):
    return "—" if value is None else h(f"{value:g}")


def weight_label(item):
    value = item["weight_percent"]
    return "Unknown" if value is None else f"{number(value)}%"


def release_source(release):
    return (f"Revision {release['revision']} · available {h(release['available_at'])}"
            f"<br><small>{h(release['parser_version'])} · {h(release['source_url'])}"
            f"<br>Retrieved {h(release['retrieved_at'])} · SHA-256 {h(release['sha256'])}</small>")


def roster_page(data, releases):
    as_of, period = data["as_of"], data["period"]
    cutoff = cutoff_select(releases, as_of)
    periods = [(release["period"], release["period"]) for release in data["releases"]]
    period_control = select("Period", "period", periods, period, "Latest period")
    current = f'<form action="/">{cutoff}<button>Apply cutoff</button></form>'
    if period is None:
        return page("Clock roster", current + "<p>No releases were available at this cutoff.</p>")

    epochs = [(mjd, f"{MJD_ZERO + timedelta(days=mjd)} ({mjd})") for mjd in data["epochs"]]
    epoch_control = select("Observation epoch (MJD)", "mjd", epochs, data["mjd"])
    hidden_cutoff = f'<input type="hidden" name="as_of" value="{h(as_of or "")}">'
    current += f'<form action="/">{hidden_cutoff}{period_control}<button>Load period</button></form>'
    current += (f'<form action="/">{hidden_cutoff}<input type="hidden" name="period" value="{h(period)}">'
                f'{epoch_control}<button>Load epoch</button></form>')
    body = ""
    for item in data["clocks"]:
        code = item["clock_code"]
        link = url(f"/clocks/{quote(code, safe='')}", as_of=as_of)
        body += row(f'<a href="{h(link)}">{h(code)}</a>', h(item["lab"] or "—"),
                    h(item["technology"] or "—"), observation_label(item),
                    number(item["phase_ns"]), weight_label(item))
    current += table(("Clock", "Laboratory", "Technology", "Observation", f"{PHASE_REFERENCE} (ns)",
                      "Monthly weight"), body)
    release = next(release for release in data["releases"] if release["period"] == period)
    return page("Clock roster", current + f"<p>{release_source(release)}</p>")


def clock_page(data, releases):
    as_of = data["as_of"]
    back = url("/", as_of=as_of)
    controls = (f'<p><a href="{h(back)}">Clock roster</a></p>'
                f'<form>{cutoff_select(releases, as_of)}<button>Apply cutoff</button></form>')
    weights_by_period = {item["period"]: item for item in data["weights"]}
    timeline = [(item["mjd"],
                 row(date_label(item["mjd"]), h(item["lab"] or "—"), h(item["technology"] or "—"),
                     observation_label(item), number(item["phase_ns"]), "—", weight_label(item)))
                for item in data["observations"]]
    timeline += [(step["mjd"],
                  row(date_label(step["mjd"]), "—", "—", f"Declared step · {h(step['note'])}",
                      "—", number(step["phase_step_ns"]),
                      weight_label(weights_by_period[step["period"]]), event=True))
                 for step in data["steps"]]
    phase = table(("Date (MJD)", "Laboratory", "Technology", "Observation / event",
                   "Reported phase (ns)", "Declared phase step (ns)", "Monthly weight"),
                  "".join(html for _, html in sorted(timeline, key=lambda item: item[0])))
    sources = table(("Period", "Source release"),
                    "".join(row(h(item["period"]), release_source(item)) for item in data["releases"]))
    return page(data["clock_code"], controls + f"""<h2>Phase timeline</h2>
<p>{PHASE_REFERENCE} in nanoseconds. A positive value means the clock is late.
The timeline shows phase as reported and lists declared steps separately.</p>
{phase}<h2>Source releases</h2>{sources}""")


def filters(query, allowed):
    params = parse_qs(query, keep_blank_values=True)
    if any(key not in allowed or len(values) != 1 for key, values in params.items()):
        raise ValueError("Use one value per supported filter.")
    values = {key: items[0] for key, items in params.items() if items[0]}
    if "as_of" in values:
        validate_cutoff(values["as_of"])
    if "mjd" in values:
        values["mjd"] = int(values["mjd"])
    return values


def handler_for(database):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            request = urlsplit(self.path)
            path = request.path
            api = path.startswith("/api/")
            try:
                with read_only(database) as db, db:
                    db.execute("BEGIN")
                    if path in ("/", "/api/roster"):
                        data = roster(db, **filters(request.query, {"as_of", "period", "mjd"}))
                        html = None if api else roster_page(data, release_options(db))
                    elif path.startswith(("/clocks/", "/api/clocks/")):
                        code = unquote(path.split("/clocks/", 1)[1])
                        data = clock_history(db, code, **filters(request.query, {"as_of"}))
                        html = None if api else clock_page(data, release_options(db))
                    else:
                        raise LookupError("Page unavailable.")
            except ValueError as error:
                self.render_error(400, str(error), api)
                return
            except LookupError as error:
                self.render_error(404, str(error), api)
                return
            self.send_body(200, data if api else html, api)

        def render_error(self, status, message, api):
            self.send_body(status, {"error": message} if api else
                           page("Request could not be completed",
                                f'<p>{h(message)}</p><p><a href="/">Clock roster</a></p>'), api)

        def send_body(self, status, payload, api):
            content = (json.dumps(payload, allow_nan=False) if api else payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ("application/json" if api else "text/html") + "; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return Handler


def serve(database, host, port):
    with read_only(database) as db:
        db.execute("SELECT id FROM release LIMIT 1").fetchone()
    with ThreadingHTTPServer((host, port), handler_for(database)) as server:
        print(f"Serving the synthetic dashboard at http://{host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
