// scanner-tv-relay — TradingView webhook relay for the "קליטת התראות TradingView" routine.
//
// TradingView alert webhooks cannot send custom headers, but the routine webhook needs
// an Authorization header. This function:
//   1. accepts only POST with a body of at most 16 KB,
//   2. (optional, TV_IP_CHECK=1) accepts only TradingView's official webhook source IPs,
//   3. requires body JSON field "secret" to equal env TV_SHARED_SECRET (constant-time compare),
//   4. strips "secret" from the payload,
//   5. forwards the JSON to env ROUTINE_WEBHOOK_URL with header Authorization: env ROUTINE_AUTH_HEADER,
//   6. replies 200 immediately; forwarding continues in the background via waitUntil
//      (TradingView cancels requests that take longer than 3 seconds),
//   7. never logs the secret, the auth header, the routine URL or the payload body.
//
// Env vars:
//   TV_SHARED_SECRET     (required, sensitive) shared secret that TradingView puts in the alert JSON
//   ROUTINE_WEBHOOK_URL  (required to forward, sensitive) https URL of the routine webhook
//   ROUTINE_AUTH_HEADER  (required to forward, sensitive) full Authorization header value, e.g. "Bearer xxx"
//   TV_IP_CHECK          (optional) "1" = reject requests not coming from TradingView's IPs

import { createHash, timingSafeEqual } from "node:crypto";
import { waitUntil } from "@vercel/functions";

// Official TradingView webhook source IPs (IPv4 only; TradingView does not send over IPv6).
// Source: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
// Checked 2026-10-08. Update here if TradingView changes the list.
const TRADINGVIEW_IPS = new Set([
  "52.89.214.238",
  "34.212.75.30",
  "54.218.53.128",
  "52.32.178.7",
]);

const MAX_BODY_BYTES = 16 * 1024;
const FORWARD_TIMEOUT_MS = 10_000;

function json(status, obj, extraHeaders = {}) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extraHeaders },
  });
}

function clientIp(request) {
  const real = request.headers.get("x-real-ip");
  if (real) return real.trim();
  const xff = request.headers.get("x-forwarded-for");
  return xff ? xff.split(",")[0].trim() : "";
}

function safeEqual(a, b) {
  // Hash both sides so lengths always match and the compare is constant-time.
  const ha = createHash("sha256").update(String(a), "utf8").digest();
  const hb = createHash("sha256").update(String(b), "utf8").digest();
  return timingSafeEqual(ha, hb);
}

function isPlaceholder(v) {
  return !v || /^\s*$/.test(v) || /placeholder|changeme|^todo$/i.test(v);
}

async function forward(url, authHeader, payload, meta) {
  const t0 = Date.now();
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: authHeader },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(FORWARD_TIMEOUT_MS),
    });
    console.log(JSON.stringify({ evt: "forward_done", status: res.status, ms: Date.now() - t0, ...meta }));
  } catch (err) {
    console.log(JSON.stringify({ evt: "forward_failed", error: err?.name || "error", ms: Date.now() - t0, ...meta }));
  }
}

async function handle(request) {
  if (request.method !== "POST") {
    return json(405, { ok: false, error: "method_not_allowed" }, { allow: "POST" });
  }

  const ip = clientIp(request);
  if (process.env.TV_IP_CHECK === "1" && !TRADINGVIEW_IPS.has(ip)) {
    console.log(JSON.stringify({ evt: "reject", reason: "ip_not_allowed", ip }));
    return json(403, { ok: false, error: "forbidden" });
  }

  const declared = Number(request.headers.get("content-length") || "0");
  if (declared > MAX_BODY_BYTES) {
    console.log(JSON.stringify({ evt: "reject", reason: "too_large", bytes: declared, ip }));
    return json(413, { ok: false, error: "payload_too_large" });
  }
  const buf = await request.arrayBuffer();
  if (buf.byteLength > MAX_BODY_BYTES) {
    console.log(JSON.stringify({ evt: "reject", reason: "too_large", bytes: buf.byteLength, ip }));
    return json(413, { ok: false, error: "payload_too_large" });
  }

  let payload;
  try {
    payload = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(buf));
  } catch {
    console.log(JSON.stringify({ evt: "reject", reason: "malformed_json", bytes: buf.byteLength, ip }));
    return json(400, { ok: false, error: "malformed_json" });
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    console.log(JSON.stringify({ evt: "reject", reason: "not_an_object", ip }));
    return json(400, { ok: false, error: "json_object_required" });
  }

  const expected = process.env.TV_SHARED_SECRET;
  if (!expected) {
    console.log(JSON.stringify({ evt: "reject", reason: "relay_secret_not_configured" }));
    return json(500, { ok: false, error: "relay_not_configured" });
  }
  if (typeof payload.secret !== "string" || !safeEqual(payload.secret, expected)) {
    console.log(JSON.stringify({ evt: "reject", reason: "bad_secret", ip }));
    return json(401, { ok: false, error: "unauthorized" });
  }

  const { secret: _drop, ...clean } = payload;
  clean.relay_received_at = new Date().toISOString();
  const meta = {
    ip,
    ticker: typeof clean.ticker === "string" ? clean.ticker.slice(0, 32) : undefined,
    keys: Object.keys(clean).slice(0, 30),
  };

  const url = process.env.ROUTINE_WEBHOOK_URL;
  const auth = process.env.ROUTINE_AUTH_HEADER;
  if (isPlaceholder(url) || isPlaceholder(auth) || !/^https:\/\//i.test(url)) {
    console.log(JSON.stringify({ evt: "accepted", forward: "forward not configured", ...meta }));
    return json(200, { ok: true, forwarded: false, note: "forward not configured" });
  }

  waitUntil(forward(url, auth, clean, meta));
  console.log(JSON.stringify({ evt: "accepted", forward: "queued", ...meta }));
  return json(200, { ok: true, forwarded: "queued" });
}

export async function POST(request) {
  return handle(request);
}
export async function GET(request) {
  return handle(request);
}
export async function PUT(request) {
  return handle(request);
}
export async function DELETE(request) {
  return handle(request);
}
export async function PATCH(request) {
  return handle(request);
}
