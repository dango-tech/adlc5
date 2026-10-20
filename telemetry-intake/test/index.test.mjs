import test from "node:test";
import assert from "node:assert/strict";
import { EVENT_BUCKETS, STATUS_BUCKETS, handleRequest, validateAggregate, validateFeedback } from "../src/index.mjs";

const aggregate = () => ({
  schema_version: 1,
  kind: "aggregate",
  events: Object.fromEntries(EVENT_BUCKETS.map(key => [key, 0])),
  statuses: Object.fromEntries(STATUS_BUCKETS.map(key => [key, 0])),
});

function envFor(calls = []) {
  return {
    RATE_LIMITER: { limit: async ({ key }) => { calls.push(["rate", key]); return { success: true }; } },
    DB: { prepare: sql => ({ bind: (...args) => ({ run: async () => { calls.push([sql, ...args]); return {}; } }) }) },
  };
}

const request = (path, payload, headers = {}) => new Request(`https://example.test${path}`, {
  method: "POST",
  headers: { "content-type": "application/json", "cf-connecting-ip": "192.0.2.1", ...headers },
  body: JSON.stringify(payload),
});

test("aggregate schema rejects unknown fields and counts outside bounds", () => {
  const valid = aggregate();
  assert.equal(validateAggregate(valid), true);
  assert.equal(validateAggregate({ ...valid, feature: "secret" }), false);
  assert.equal(validateAggregate({ ...valid, events: { ...valid.events, private: 1 } }), false);
  assert.equal(validateAggregate({ ...valid, events: { ...valid.events, other: -1 } }), false);
  assert.equal(validateAggregate({ ...valid, events: { ...valid.events, other: 1.5 } }), false);
});

test("feedback has separate strict schema and bounded text", () => {
  assert.equal(validateFeedback({ schema_version: 1, kind: "feedback", rating: 5, category: "idea", text: "ok" }), true);
  assert.equal(validateFeedback({ schema_version: 1, kind: "feedback", rating: 5, category: "idea", user_id: "persistent" }), false);
  assert.equal(validateFeedback({ schema_version: 1, kind: "feedback", rating: 5, category: "idea", text: "x".repeat(1001) }), false);
  assert.equal(validateFeedback({ schema_version: 1, kind: "feedback", rating: 0, category: "idea" }), false);
});

test("intake stores only allowlisted aggregate and uses transient rate key", async () => {
  const calls = [];
  const payload = aggregate();
  const response = await handleRequest(request("/v1/aggregate", payload, { "idempotency-key": "e6a9c348-20ab-450e-868c-e879d7437a38" }), envFor(calls));
  assert.equal(response.status, 202);
  assert.deepEqual(calls[0], ["rate", "192.0.2.1"]);
  assert.equal(calls.length, 2);
  assert.equal(calls[1][0].startsWith("INSERT OR IGNORE INTO aggregates"), true);
  assert.equal(calls[1].at(-1), JSON.stringify(payload));
  assert.doesNotMatch(JSON.stringify(calls.slice(1)), /192\.0\.2\.1/);
});

test("unknown fields are rejected before database write", async () => {
  const calls = [];
  const response = await handleRequest(request("/v1/aggregate", { ...aggregate(), prompt: "secret" }), envFor(calls));
  assert.equal(response.status, 400);
  assert.equal(calls.filter(([sql]) => typeof sql === "string" && sql.startsWith("INSERT")).length, 0);
});

test("oversized and rate-limited requests fail closed", async () => {
  const tooLarge = await handleRequest(new Request("https://example.test/v1/feedback", {
    method: "POST", headers: { "content-type": "application/json", "cf-connecting-ip": "192.0.2.1" }, body: " ".repeat(4097),
  }), envFor());
  assert.equal(tooLarge.status, 413);
  const limited = await handleRequest(request("/v1/feedback", { schema_version: 1, kind: "feedback", rating: 5, category: "idea" }), {
    RATE_LIMITER: { limit: async () => ({ success: false }) }, DB: { prepare: () => { throw new Error("must not write"); } },
  });
  assert.equal(limited.status, 429);
});

test("database failure returns generic error without reflecting payload", async () => {
  const response = await handleRequest(request("/v1/feedback", { schema_version: 1, kind: "feedback", rating: 5, category: "idea", text: "private words" }), {
    RATE_LIMITER: { limit: async () => ({ success: true }) }, DB: { prepare: () => { throw new Error("private database detail"); } },
  });
  assert.equal(response.status, 503);
  assert.doesNotMatch(await response.text(), /private/);
});

test("feedback counts Unicode code points and accepts UTF-8 emoji requests", async () => {
  const payload = { schema_version: 1, kind: "feedback", rating: 5, category: "idea", text: "😀".repeat(600) };
  assert.equal(validateFeedback({ ...payload, text: "😀".repeat(1000) }), true);
  assert.equal(validateFeedback({ ...payload, text: "😀".repeat(1001) }), false);
  assert.equal((await handleRequest(request("/v1/feedback", payload), envFor())).status, 202);
});
