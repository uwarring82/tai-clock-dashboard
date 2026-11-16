// Bulletin C 72 (July 2026) announced no leap second at the end of December 2026.
// Leap seconds occur only at the end of June or December, so TAI − UTC = 37 s
// holds until 2027-07-01T00:00Z. Re-check after Bulletin C 73 (January 2027)
// and move data-end accordingly.
export function clockReadings(now, offsetSeconds, validFrom, validUntil) {
  const utc = new Date(now).toISOString();
  const tai = now >= validFrom && now < validUntil
    ? new Date(now + offsetSeconds * 1000).toISOString()
    : null;
  return { utc, tai };
}

function startClocks() {
  const offset = document.querySelector("#tai-offset").dataset;
  const inputs = [Number(offset.seconds), Date.parse(offset.start), Date.parse(offset.end)];
  const utcTime = document.querySelector("#utc-time");
  const utcDate = document.querySelector("#utc-date");
  const taiTime = document.querySelector("#tai-time");
  const taiDate = document.querySelector("#tai-date");
  const render = () => {
    const { utc, tai } = clockReadings(Date.now(), ...inputs);
    utcTime.textContent = utc.slice(11, 19);
    utcDate.textContent = utc.slice(0, 10);
    taiTime.textContent = tai ? tai.slice(11, 19) : "--:--:--";
    taiDate.textContent = tai ? tai.slice(0, 10) : "Check the latest Bulletin C for this date.";
  };
  render();
  setInterval(render, 250);
}

if (typeof document !== "undefined") startClocks();
