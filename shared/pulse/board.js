const data = JSON.parse(document.getElementById("snapshot").textContent);
const selector = document.getElementById("feature");
const overview = document.getElementById("overview");
const panel = document.getElementById("features");
document.getElementById("capture").textContent = `Snapshot captured ${data.generated_at} · on demand; continuous monitoring is off`;

for (const feature of data.features) {
  const option = document.createElement("option");
  option.value = feature.identity;
  option.textContent = `${feature.archive_id ? "Archived · " : ""}${feature.id}`;
  selector.append(option);
  const item = document.createElement("li");
  const choose = document.createElement("button");
  const cost = feature.usage.known_cost_usd === null ? "cost unavailable" : `$${feature.usage.known_cost_usd}`;
  choose.textContent = `${feature.archive_id ? "Archived · " : ""}${feature.id} · ${feature.lifecycle.stage || "stage unknown"} · ${cost}`;
  choose.addEventListener("click", () => { selector.value = feature.identity; render(); });
  item.append(choose);
  overview.append(item);
}

function render() {
  const feature = data.features.find(item => item.identity === selector.value);
  panel.replaceChildren();
  if (!feature) {
    const empty = document.createElement("p");
    empty.textContent = "No ADLC5 features were found in this workspace.";
    panel.append(empty);
    return;
  }
  const title = document.createElement("h2");
  title.id = "feature-title";
  title.textContent = `${feature.id}${feature.archive_id ? ` · archived ${feature.archive_id}` : ""}`;
  panel.append(title);
  const summary = document.createElement("p");
  summary.textContent = `${feature.lifecycle.stage || "Stage unknown"} · ${feature.lifecycle.step || "step unknown"} · checks ${feature.evidence.checks.status} · review ${feature.evidence.review.status} · local gate ${feature.evidence.pr_ready.status}`;
  panel.append(summary);
  const next = document.createElement("p");
  next.textContent = `Next: ${feature.next_action.label}`;
  panel.append(next);
  const usage = document.createElement("p");
  usage.textContent = `Usage: ${feature.usage.status}; ${feature.usage.accounted_records}/${feature.usage.observed_records} records accounted; known subtotal ${feature.usage.known_cost_usd === null ? "unavailable" : `$${feature.usage.known_cost_usd}`}`;
  panel.append(usage);
  if (feature.usage.token_records) {
    const tokens = document.createElement("p");
    const breakdown = feature.usage.tokens;
    tokens.textContent = `Normalized token counters (${feature.usage.token_records} records): ${Object.entries(breakdown).map(([key, value]) => `${key} ${value}`).join(", ")}. Thinking is informational and may overlap output.`;
    panel.append(tokens);
  }

  const rail = document.createElement("ol");
  rail.className = "rail";
  for (const stage of ["specify", "plan", "tasks", "implement"]) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = `${stage} · ${(feature.lifecycle.stage_status || {})[stage] || "not recorded"}`;
    button.setAttribute("aria-current", feature.lifecycle.stage === stage ? "step" : "false");
    button.addEventListener("click", () => showReceipts(feature, stage));
    li.append(button);
    rail.append(li);
  }
  panel.append(rail);
  const replay = document.createElement("details");
  const summary2 = document.createElement("summary");
  summary2.textContent = "Recorded event replay";
  replay.append(summary2);
  const events = document.createElement("select");
  events.setAttribute("aria-label", "Select recorded event");
  const allEvents = [...feature.receipts, ...feature.events];
  for (const [index, event] of allEvents.entries()) {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = [event.kind, event.status, event.time || event.id].filter(Boolean).join(" · ");
    events.append(option);
  }
  const replayDetail = document.createElement("p");
  replayDetail.className = "muted";
  events.addEventListener("change", () => {
    const event = allEvents[Number(events.value)];
    replayDetail.textContent = event ? `Recorded then · ${event.id || "source unavailable"} · ${event.time || "time unknown"}` : "No event selected";
  });
  replay.append(events, replayDetail);
  panel.append(replay);
  showReceipts(feature, feature.lifecycle.stage);
  const warnings = document.createElement("p");
  warnings.className = "muted";
  warnings.textContent = (feature.warnings || []).join(" · ") || "No capture warnings";
  panel.append(warnings);
}

function showReceipts(feature, stage) {
  let output = document.getElementById("stage-receipts");
  if (!output) {
    output = document.createElement("p");
    output.id = "stage-receipts";
    output.className = "muted";
    panel.append(output);
  }
  const rows = feature.receipts.filter(item => !stage || !item.stage || item.stage === stage);
  output.textContent = `${stage || "Stage"} receipts: ${rows.length ? rows.map(item => `${item.kind} · ${item.status} · ${item.id || "source unavailable"}`).join("; ") : "no recorded receipts"}`;
}

selector.addEventListener("change", render);
render();
