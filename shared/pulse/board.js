const data = JSON.parse(document.getElementById("snapshot").textContent);
const selector = document.getElementById("feature");
const panel = document.getElementById("features");
const stages = ["specify", "plan", "tasks", "implement"];
const make = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const money = value => typeof value === "number" ? `$${value.toFixed(2)}` : "Unavailable";
const label = value => value ? String(value).replaceAll("_", " ") : "Not recorded";
const statusClass = value => ["pass", "completed"].includes(value) ? "p-good" : ["fail", "unstable"].includes(value) ? "p-bad" : "p-warn";
const evidenceStatus = (title, value, detail = "") => ({ title, value: label(value), detail });
let selectedStage = null;
let selectedEvent = null;

document.getElementById("capture").textContent = `Captured ${data.generated_at} · on demand; continuous monitoring is off`;
for (const feature of data.features) {
  const option = make("option", "", `${feature.archive_id ? "Archived · " : ""}${feature.id}`);
  option.value = feature.identity;
  selector.append(option);
}

function render() {
  const feature = data.features.find(item => item.identity === selector.value);
  panel.replaceChildren();
  if (!feature) {
    panel.append(make("p", "p-empty", "No ADLC5 features were found in this workspace."));
    return;
  }
  const stage = feature.lifecycle.stage;
  const currentStatus = feature.evidence.pr_ready.status;
  selectedStage = stages.includes(selectedStage) ? selectedStage : stage;

  const heading = make("div", "heading");
  const titleGroup = make("div");
  titleGroup.append(make("div", "eyebrow", feature.archive_id ? `Archived feature · ${feature.archive_id}` : "Feature lifecycle"));
  titleGroup.append(make("h1", "", feature.id));
  titleGroup.append(make("div", "sub", `${label(stage)} / ${label(feature.lifecycle.step)} · fingerprint ${feature.capture.input_fingerprint || "unavailable"}`));
  const state = make("span", `status ${currentStatus === "pass" ? "" : currentStatus === "fail" ? "fail" : "warn"}`, `Local PR-ready · ${label(currentStatus)}`);
  heading.append(titleGroup, state);
  panel.append(heading);

  const metrics = make("div", "p-metrics");
  const checks = feature.evidence.checks;
  const usage = feature.usage;
  const evaluation = feature.evaluation || {};
  const percent = value => typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : "Not measured";
  const metricRows = [
    ["Required checks", checks.status === "unavailable" ? "Unavailable" : `${checks.recorded_passed || 0} / ${checks.required || 0}`, checks.status],
    ["Independent review", label(feature.evidence.review.status), "Current repository evidence"],
    ["Local PR-ready gate", label(currentStatus), "Remote CI and deployment are separate"],
    ["Known usage cost", money(usage.known_cost_usd), `${usage.accounted_records}/${usage.observed_records} records accounted · ${label(usage.status)}`],
    ["Outcome success", percent(evaluation.success_rate_pct), `${evaluation.successful || 0}/${evaluation.runs || 0} evaluated runs · ${evaluation.success_interval_pct ? `95% Wilson interval ${evaluation.success_interval_pct.join("–")}%` : label(evaluation.status)}`],
    ["Projected cost savings", percent(evaluation.savings_pct), evaluation.savings_pct == null ? "Not measured · comparable evaluation required" : `Observed vs direct agent · ${evaluation.matched_cases} matched cases · range ${evaluation.savings_range_pct.join("–")}%`],
    ["Escaped defects", evaluation.escaped_defects ?? "Not measured", "Recorded observation windows only"],
    ["Rework", evaluation.rework ?? "Not measured", "Recorded rework count"],
  ];
  for (const [name, value, detail] of metricRows) {
    const metric = make("div", "p-metric");
    metric.append(make("label", "", name), make("strong", "p-value", value), make("span", "sub", detail));
    metrics.append(metric);
  }
  panel.append(metrics);
  panel.append(make("p", "sub", `Evaluation · ${evaluation.reason || "Accuracy is not measured"} · source ${evaluation.source || "unavailable"}`));

  const stageHead = make("div", "p-panel-head");
  stageHead.append(make("h2", "", "Delivery path"), make("span", "sub", "Select a stage to inspect its receipts"));
  panel.append(stageHead);
  const rail = make("div", "p-stages");
  rail.setAttribute("aria-label", "ADLC5 lifecycle stages");
  for (const [index, name] of stages.entries()) {
    const status = feature.lifecycle.stage_status?.[name] || "not recorded";
    const button = make("button", "p-stage");
    button.type = "button";
    button.dataset.status = status;
    button.setAttribute("aria-pressed", String(selectedStage === name));
    if (stage === name) button.setAttribute("aria-current", "step");
    button.append(make("span", "p-stage-name", `${String(index + 1).padStart(2, "0")} / ${name}`));
    button.append(make("span", "p-stage-state", label(status)));
    button.addEventListener("click", () => { selectedStage = name; render(); panel.querySelector('.p-stage[aria-pressed="true"]')?.focus(); });
    rail.append(button);
  }
  panel.append(rail);

  const next = make("div", "p-next");
  const nextCopy = make("div");
  nextCopy.append(make("div", "eyebrow", "Suggested next action"), make("strong", "", feature.next_action.label), make("small", "", `Reason · ${label(feature.next_action.reason_code)}`));
  next.append(nextCopy);
  panel.append(next);

  const columns = make("div", "p-columns");
  const eventSection = make("section");
  const eventHead = make("div", "p-panel-head");
  const allEvents = [...feature.events].reverse();
  eventHead.append(make("h2", "", "Recorded events"), make("span", "sub", `${Math.min(8, allEvents.length)} latest of ${allEvents.length} · source records`));
  eventSection.append(eventHead);
  const eventList = make("ol", "p-events");
  const events = allEvents.slice(0, 8);
  for (const [index, event] of events.entries()) {
    const item = make("li");
    const button = make("button", "", `${label(event.kind)} · ${label(event.status)}`);
    button.type = "button";
    button.setAttribute("aria-pressed", String(selectedEvent === index));
    button.addEventListener("click", () => { selectedEvent = index; render(); panel.querySelector(`.p-events button:nth-of-type(${index + 1})`)?.focus(); });
    const time = make("time", "", event.time || event.id || "Time unavailable");
    item.append(button, time);
    eventList.append(item);
  }
  eventSection.append(eventList);
  if (events.length) {
    const event = events[selectedEvent ?? 0];
    const receipt = make("div", "p-receipt");
    receipt.append(make("strong", "", "Selected source record"), make("span", "", `${event.id || "Source unavailable"} · ${event.source || "source unavailable"}${event.line ? `:${event.line}` : ""}`));
    eventSection.append(receipt);
  } else {
    eventSection.append(make("p", "p-empty", "No recorded events are available in this snapshot."));
  }
  columns.append(eventSection);

  const evidenceSection = make("section");
  const evidenceHead = make("div", "p-panel-head");
  evidenceHead.append(make("h2", "", "Evidence, with provenance"), make("span", "sub", "Current snapshot"));
  evidenceSection.append(evidenceHead);
  const table = make("table", "p-evidence");
  table.setAttribute("aria-label", "Evidence status and provenance");
  const body = make("tbody");
  const rows = [
    evidenceStatus("Checks", checks.status, checks.status === "unavailable" ? "No current check receipt" : `${checks.recorded_passed || 0} passed · ${checks.required || 0} required`),
    evidenceStatus("Independent review", feature.evidence.review.status),
    evidenceStatus("Local PR-ready gate", currentStatus, feature.evidence.pr_ready.reason || "Gate receipt bound to current inputs"),
    evidenceStatus("Capture", feature.capture.stable ? feature.capture.freshness : "unstable", feature.capture.input_fingerprint || "Input fingerprint unavailable"),
  ];
  for (const row of rows) {
    const tr = make("tr");
    tr.append(make("th", "", row.title));
    const td = make("td");
    td.append(make("strong", statusClass(row.value), row.value), make("div", "sub", row.detail));
    tr.append(td);
    body.append(tr);
  }
  table.append(body);
  evidenceSection.append(table);
  const selectedReceipts = feature.receipts.filter(item => !selectedStage || !item.stage || item.stage === selectedStage);
  const receipt = make("div", "p-receipt");
  receipt.append(make("strong", "", `${label(selectedStage)} receipts`));
  receipt.append(make("span", "", selectedReceipts.length
    ? selectedReceipts.map(item => `${label(item.kind)} · ${label(item.status)} · ${item.id || "source unavailable"}`).join("\n")
    : "No recorded receipts for this stage."));
  evidenceSection.append(receipt);
  columns.append(evidenceSection);
  panel.append(columns);

  if (feature.warnings?.length) panel.append(make("p", "p-warning muted", `Capture warnings · ${feature.warnings.join(" · ")}`));
}

selector.addEventListener("change", () => { selectedStage = null; selectedEvent = null; render(); });
render();
