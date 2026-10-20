export const EVENT_BUCKETS = ["script_start", "script_end", "checkpoint", "gate_fail", "stage_picker", "phase_advance", "policy_decision", "other"];
export const STATUS_BUCKETS = ["pass", "fail", "blocked", "warn", "other"];
const FEEDBACK_CATEGORIES = ["bug", "idea", "positive", "other"];
const MAX_BODY = 4096;

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json", "cache-control": "no-store" },
});

export function validateAggregate(value) {
  if (!value || Object.getPrototypeOf(value) !== Object.prototype || Object.keys(value).sort().join(",") !== "events,kind,schema_version,statuses" || value.schema_version !== 1 || value.kind !== "aggregate") return false;
  for (const [field, allowed] of [["events", EVENT_BUCKETS], ["statuses", STATUS_BUCKETS]]) {
    const counts = value[field];
    if (!counts || Object.getPrototypeOf(counts) !== Object.prototype || Object.keys(counts).some(key => !allowed.includes(key)) || allowed.some(key => !Object.hasOwn(counts, key))) return false;
    if (Object.values(counts).some(count => !Number.isSafeInteger(count) || count < 0 || count > 1_000_000)) return false;
  }
  return true;
}

export function validateFeedback(value) {
  if (!value || Object.getPrototypeOf(value) !== Object.prototype || Object.keys(value).some(key => !["schema_version", "kind", "rating", "category", "text"].includes(key)) || !["schema_version", "kind", "rating", "category"].every(key => Object.hasOwn(value, key))) return false;
  return value.schema_version === 1 && value.kind === "feedback" && Number.isInteger(value.rating) && value.rating >= 1 && value.rating <= 5 && FEEDBACK_CATEGORIES.includes(value.category) && (value.text === undefined || typeof value.text === "string" && [...value.text].length <= 1000);
}

async function readBody(request) {
  const declared = Number(request.headers.get("content-length") || 0);
  if (declared > MAX_BODY) throw new Error("too_large");
  const reader = request.body?.getReader();
  if (!reader) throw new Error("invalid_body");
  const chunks = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY) {
      await reader.cancel();
      throw new Error("too_large");
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export async function handleRequest(request, env) {
  const url = new URL(request.url);
  if (request.method !== "POST" || !["/v1/aggregate", "/v1/feedback"].includes(url.pathname)) return json({ error: "not_found" }, 404);
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") return json({ error: "unsupported_media_type" }, 415);
  const clientAddress = request.headers.get("cf-connecting-ip");
  if (!clientAddress) return json({ error: "unavailable" }, 503);
  let success;
  try { ({ success } = await env.RATE_LIMITER.limit({ key: clientAddress })); }
  catch { return json({ error: "unavailable" }, 503); }
  if (!success) return json({ error: "rate_limited" }, 429);
  let value;
  try { value = await readBody(request); }
  catch (error) { return json({ error: error.message === "too_large" ? "payload_too_large" : "invalid_payload" }, error.message === "too_large" ? 413 : 400); }
  const aggregate = url.pathname === "/v1/aggregate";
  if (!(aggregate ? validateAggregate(value) : validateFeedback(value))) return json({ error: "invalid_payload" }, 400);
  try {
    if (aggregate) {
      const key = request.headers.get("idempotency-key");
      if (!key || !/^[0-9a-f-]{36}$/i.test(key)) return json({ error: "invalid_submission_id" }, 400);
      await env.DB.prepare("INSERT OR IGNORE INTO aggregates (submission_id, received_day, payload) VALUES (?, date('now'), ?)").bind(key, JSON.stringify(value)).run();
    } else {
      await env.DB.prepare("INSERT INTO feedback (received_day, rating, category, text) VALUES (date('now'), ?, ?, ?)").bind(value.rating, value.category, value.text ?? null).run();
    }
    return json({ status: "accepted" }, 202);
  } catch {
    return json({ error: "unavailable" }, 503);
  }
}

export default { fetch: handleRequest, scheduled };

export async function scheduled(_controller, env, ctx) {
  ctx.waitUntil(Promise.all([
    env.DB.prepare("DELETE FROM aggregates WHERE received_day < date('now', '-90 days')").run(),
    env.DB.prepare("DELETE FROM feedback WHERE received_day < date('now', '-90 days')").run(),
  ]));
}
