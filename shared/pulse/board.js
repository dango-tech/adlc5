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
const hostNames = {claude: "Claude Code", codex: "Codex", cursor: "Cursor", hermes: "Hermes Agent"};
const hostMarks = {
  claude: "M12 2v20M2 12h20M5 5l14 14M5 19L19 5M8 3l8 18M3 8l18 8",
  codex: "M9 5l-7 7 7 7M15 5l7 7-7 7M14 3l-4 18",
  cursor: "M4 2l16 12-8 1-3 7zM12 15l6 6",
  hermes: "M12 4v17M4 5l8 4 8-4M2 9l10 4 10-4M5 14l7 3 7-3",
};
function hostBadges(hosts = []) {
  const group = make("span", "p-hosts");
  if (!hosts.length) return make("span", "muted", "Host not recorded");
  for (const host of hosts) {
    const badge = make("span", `p-host p-host-${host}`);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", hostMarks[host] || "M4 4h16v16H4z");
    svg.append(path);
    badge.append(svg, make("span", "", hostNames[host] || host));
    group.append(badge);
  }
  return group;
}
let selectedStage = null;
let selectedEvent = null;

document.getElementById("capture").textContent = `Captured ${data.generated_at} · on demand; continuous monitoring is off`;
for (const feature of data.features) {
  const option = make("option", "", `${feature.project ? feature.project + " · " : ""}${feature.archive_id ? "Archived · " : ""}${feature.id}${feature.workspace_key ? " · " + feature.workspace_key : ""}`);
  option.value = feature.identity;
  selector.append(option);
}
if (data.selected_feature) selector.value = data.selected_feature;

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
  if (feature.workspace_label) titleGroup.append(make("div", "sub", feature.workspace_label));
  if (feature.hosts) titleGroup.append(hostBadges(feature.hosts));
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

if (data.fleet) {
  const fleet = document.getElementById("fleet");
  fleet.hidden = false;
  fleet.append(make("h1", "", "Your ADLC5 activity"), make("p", "muted", data.fleet.scope));
  fleet.append(make("p", "muted", "Agent badges show recorded usage of the exact worktree, not live presence. Multiple badges mean multiple hosts have used that tree."));
  const metrics = make("div", "p-metrics");
  for (const [name, count] of [["Workspaces", data.fleet.workspaces], ["Feature snapshots", data.features.length],
    ["Host sessions", data.fleet.sessions.length], ["Runner attempts", data.fleet.attempts.length]]) {
    const metric = make("div", "p-metric");
    metric.append(make("label", "", name), make("strong", "p-value", count));
    metrics.append(metric);
  }
  fleet.append(metrics);
  const search = make("input");
  search.type = "search";
  search.placeholder = "Search projects, features, sessions or hosts";
  search.setAttribute("aria-label", "Search all activity");
  fleet.append(search);
  const view = make("div");
  fleet.append(view);
  function inventory() {
    view.replaceChildren();
    const query = search.value.toLowerCase();
    const tables = [
      ["Workspaces and recorded agents", ["Worktree", "Identity", "Agents observed using this tree"],
        (data.fleet.workspace_inventory || []).map(w => [w.label, w.key, hostBadges(w.hosts)])],
      ["Feature snapshots", ["Project", "Feature", "Agents", "Stage", "PR-ready evidence", "Recorded cost subtotal"],
        data.features.map(f => [f.project, `${f.archive_id || f.id} · ${f.workspace_key}`, hostBadges(f.hosts), f.lifecycle.step || "Not recorded", f.evidence.pr_ready.status,
          f.usage.known_cost_usd === null ? "Not measured" : `${money(f.usage.known_cost_usd)} · incomplete coverage`])],
      ["Host sessions with explicit ADLC5 evidence", ["Project", "Host", "Session", "Last evidence", "Evidence", "Whole-session token subtotal", "Independent outcome"],
        data.fleet.sessions.map(s => [s.project, hostBadges([s.host]), s.id, s.last || "Not recorded", s.evidence,
          s.tokens === null ? "Not measured" : `${s.tokens.toLocaleString()} · ${s.token_source}`, s.outcome])],
      ["Runner attempts", ["Project", "Feature", "Attempt", "Host", "Worker status", "Model"],
        data.fleet.attempts.map(a => [a.project, a.feature, a.id, hostBadges([a.host]), a.status || "Not recorded", a.model])],
    ];
    for (const [title, headings, rows] of tables) {
      const section = make("details", "p-inventory");
      const filtered = rows.filter(row => row.map(cell => cell instanceof Node ? cell.textContent : cell).join(" ").toLowerCase().includes(query));
      section.open = true;
      section.append(make("summary", "", `${title} · ${filtered.length}`));
      const scroll = make("div", "p-table-scroll");
      const table = make("table");
      const head = make("tr");
      for (const heading of headings) head.append(make("th", "", heading));
      table.append(head);
      for (const row of filtered) {
        const tr = make("tr");
        for (const cell of row) {
          const td = make("td");
          td.append(cell instanceof Node ? cell : document.createTextNode(cell ?? "Not recorded"));
          tr.append(td);
        }
        table.append(tr);
      }
      scroll.append(table);
      section.append(scroll);
      if (!filtered.length) section.append(make("p", "muted", "No matching recorded activity."));
      view.append(section);
    }
  }
  search.addEventListener("input", inventory);
  inventory();
  if (data.warnings?.length) fleet.append(make("p", "muted", `Coverage warnings: ${data.warnings.join(" · ")}`));
  fleet.append(make("h2", "", "Selected feature details"));
}
render();
