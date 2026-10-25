export function parseIso(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Invalid timestamp.");
  }
  return date;
}

export function toIsoUtc(date) {
  return date.toISOString();
}

export function toLocalInputValue(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export function fromLocalInputValue(value) {
  if (!value) {
    throw new Error("A date and time is required.");
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Enter a valid date and time.");
  }
  return date;
}

export function formatLocal(iso) {
  return parseIso(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatLocalTime(iso) {
  return parseIso(iso).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export const UK_TIME_ZONE = "Europe/London";

function ukFormatToParts(iso, options) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: UK_TIME_ZONE,
    ...options,
  }).formatToParts(parseIso(iso));
}

function partMap(parts) {
  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
}

export function ukTimeZoneName(iso) {
  const name = partMap(ukFormatToParts(iso, { timeZoneName: "short" })).timeZoneName || "GMT";
  if (/BST|GMT\+1|UTC\+1/i.test(name)) {
    return "BST";
  }
  if (/GMT|UTC/i.test(name)) {
    return "GMT";
  }
  return name;
}

export function formatUkTime(iso) {
  const parts = partMap(
    ukFormatToParts(iso, {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }),
  );
  return `${parts.hour}:${parts.minute} ${parts.dayPeriod}`;
}

export function formatUkAxisTick(iso) {
  const parts = partMap(
    ukFormatToParts(iso, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    }),
  );
  const minutes = parts.minute === "00" ? "" : `:${parts.minute}`;
  return `${parts.month} ${parts.day}, ${parts.hour}${minutes} ${parts.dayPeriod}`;
}

export function formatUkFullDate(iso) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: UK_TIME_ZONE,
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(parseIso(iso));
}

export function formatUkTooltip(startIso, endIso) {
  return {
    date: formatUkFullDate(startIso),
    start: formatUkTime(startIso),
    end: formatUkTime(endIso),
    zone: `UK local time (${ukTimeZoneName(startIso)})`,
  };
}

export function formatBrowserTime(iso) {
  return formatLocalTime(iso);
}

export function formatBrowserDate(iso) {
  return parseIso(iso).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

export function formatBrowserTimeRange(startIso, finishIso) {
  const startDate = formatBrowserDate(startIso);
  const finishDate = formatBrowserDate(finishIso);
  return {
    time: `${formatBrowserTime(startIso)} – ${formatBrowserTime(finishIso)}`,
    date: startDate === finishDate ? startDate : `${startDate} – ${finishDate}`,
  };
}

export function formatGrams(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "—";
  }
  return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

export function nextHalfHour(from = new Date()) {
  const date = new Date(from);
  date.setSeconds(0, 0);
  const minutes = date.getMinutes();
  const add = minutes === 0 || minutes === 30 ? 30 : minutes < 30 ? 30 - minutes : 60 - minutes;
  date.setMinutes(date.getMinutes() + add);
  return date;
}

export function snapToHalfHourUtc(date) {
  const utc = new Date(date.getTime());
  const minutes = utc.getUTCMinutes();
  const snapped = minutes < 15 ? 0 : minutes < 45 ? 30 : 0;
  if (minutes >= 45) {
    utc.setUTCHours(utc.getUTCHours() + 1);
  }
  utc.setUTCMinutes(snapped, 0, 0);
  return utc;
}

export function durationFits(start, finish, durationMinutes) {
  return finish.getTime() - start.getTime() >= durationMinutes * 60 * 1000;
}
