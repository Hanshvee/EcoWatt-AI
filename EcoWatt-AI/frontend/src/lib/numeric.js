export function sanitizeIntegerInput(raw) {
  if (raw == null) {
    return "";
  }
  const digits = String(raw).replace(/[^\d]/g, "");
  if (digits === "") {
    return "";
  }
  return digits.replace(/^0+(?=\d)/, "");
}

export function sanitizeDecimalInput(raw) {
  if (raw == null) {
    return "";
  }
  let value = String(raw).replace(/[^\d.]/g, "");
  const dot = value.indexOf(".");
  if (dot !== -1) {
    value = `${value.slice(0, dot + 1)}${value.slice(dot + 1).replace(/\./g, "")}`;
  }
  if (value === "" || value === ".") {
    return value;
  }

  const [whole = "", fraction] = value.split(".");
  const normalizedWhole = whole.replace(/^0+(?=\d)/, "");
  if (fraction !== undefined) {
    return `${normalizedWhole}.${fraction}`;
  }
  return normalizedWhole;
}

export function normalizeInteger(raw) {
  if (raw === "" || raw == null) {
    return "";
  }
  const value = Number(raw);
  if (!Number.isFinite(value)) {
    return "";
  }
  return String(Math.trunc(value));
}

export function normalizeDecimal(raw) {
  if (raw === "" || raw == null || raw === ".") {
    return "";
  }
  const value = Number(raw);
  if (!Number.isFinite(value)) {
    return "";
  }
  return String(value);
}

export function toFiniteNumber(raw) {
  if (raw === "" || raw == null || raw === ".") {
    return NaN;
  }
  return Number(raw);
}
