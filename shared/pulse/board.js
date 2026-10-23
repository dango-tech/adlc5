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

function renderWorkflow() {
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
    button.addEventListener("click", () => { selectedStage = name; renderWorkflow(); panel.querySelector('.p-stage[aria-pressed="true"]')?.focus(); });
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
    button.addEventListener("click", () => { selectedEvent = index; renderWorkflow(); panel.querySelector(`.p-events button:nth-of-type(${index + 1})`)?.focus(); });
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


const fleet = document.getElementById("fleet");
const nav = document.getElementById("navigation");
const link = (text, route) => {
  const node = make("a", "p-link", text);
  node.href = "#" + route;
  return node;
};
for (const [name, route] of [["Projects", "projects"], ["Activity", "activity"], ["Settings", "settings"]]) nav.append(link(name, route));
selector.addEventListener("change", () => { location.hash = "workflow/" + encodeURIComponent(selector.value); });
function table(headings, rows) {
  const scroll = make("div", "p-table-scroll");
  const node = make("table");
  const header = make("tr");
  for (const name of headings) header.append(make("th", "", name));
  node.append(header);
  for (const row of rows) {
    const tr = make("tr");
    for (const value of row) {
      const td = make("td");
      td.append(value instanceof Node ? value : document.createTextNode(value ?? "Not recorded"));
      tr.append(td);
    }
    node.append(tr);
  }
  scroll.append(node);
  return scroll;
}
const workspaces = data.fleet?.workspace_inventory || [];
const projects = data.fleet?.projects || [];
const hostsFor = keys => [...new Set(workspaces.filter(w => keys.includes(w.key)).flatMap(w => w.hosts))];
function showProjects() {
  fleet.append(make("h1", "", "Your projects"), make("p", "muted", "Applications first. Open a project to inspect its workflows and worktrees."));
  const cards = make("div", "p-projects");
  for (const project of projects) {
    const features = data.features.filter(f => f.project_id === project.id);
    const card = make("article", "p-project");
    card.append(link(project.name, "project/" + project.id), hostBadges(hostsFor(project.workspace_keys)));
    card.append(make("p", "muted", `${features.filter(f => !f.archive_id).length} active workflows · ${features.filter(f => f.archive_id).length} archived · ${project.workspace_keys.length} worktrees`));
    const blockers = features.filter(f => !f.archive_id && f.evidence.pr_ready.status === "fail").length;
    card.append(make("p", "", blockers ? `${blockers} workflows have failing local PR-ready evidence` : "Open to inspect delivery evidence"));
    const recent = (data.fleet?.sessions || []).filter(s => s.workspace_keys?.some(key => project.workspace_keys.includes(key))).map(s => s.last).filter(Boolean).sort().at(-1);
    card.append(make("small", "muted", "Last ADLC5 session evidence: " + (recent || "Not recorded")));
    cards.append(card);
  }
  if (!projects.length) cards.append(make("p", "p-empty", "No projects found in the captured sources."));
  fleet.append(cards);
}
function showProject(id) {
  const project = projects.find(p => p.id === id);
  if (!project) return fleet.append(make("p", "p-empty", "Project not found in this snapshot."));
  fleet.append(link("Projects", "projects"), make("h1", "", project.name), hostBadges(hostsFor(project.workspace_keys)));
  const filter = make("select");
  filter.setAttribute("aria-label", "Workflow archive filter");
  for (const [value, title] of [["active", "Active workflows"], ["archived", "Archived workflows"], ["all", "All workflows"]]) {
    const option = make("option", "", title); option.value = value; filter.append(option);
  }
  filter.value = "active";
  const workflows = make("div");
  function list() {
    workflows.replaceChildren();
    const rows = data.features.filter(f => f.project_id === id && (filter.value === "all" || Boolean(f.archive_id) === (filter.value === "archived")));
    workflows.append(table(["Workflow", "Worktree", "Agents", "Stage", "Local PR-ready", "Next action"], rows.map(f => [
      link(f.archive_id || f.id, "workflow/" + encodeURIComponent(f.identity)), f.workspace_label, hostBadges(f.hosts), f.lifecycle.step, f.evidence.pr_ready.status, f.next_action.label])));
    if (!rows.length) workflows.append(make("p", "p-empty", "No workflows match this filter."));
  }
  filter.addEventListener("change", list); list();
  fleet.append(filter, workflows, make("h2", "", "Worktrees"));
  fleet.append(table(["Worktree", "Recorded agents", "Settings"], workspaces.filter(w => w.project_id === id).map(w => [w.label, hostBadges(w.hosts), link("Inspect overrides", "settings/worktree:" + w.key)])));
  fleet.append(link("Project settings", "settings/project:" + id));
}
function showActivity() {
  fleet.append(make("h1", "", "Activity"), make("p", "muted", data.fleet?.scope || "Captured source records"));
  const kind = make("select"); kind.setAttribute("aria-label", "Activity type");
  for (const [value, title] of [["sessions", "Host sessions"], ["attempts", "Runner attempts"]]) { const option = make("option", "", title); option.value = value; kind.append(option); }
  kind.value = "sessions";
  const search = make("input"); search.type = "search"; search.placeholder = "Search activity"; search.setAttribute("aria-label", "Search activity");
  const body = make("div"); let page = 0;
  function list() {
    body.replaceChildren();
    const rows = (data.fleet?.[kind.value] || []).filter(row => [row.project, row.id, row.host, hostNames[row.host]].join(" ").toLowerCase().includes(search.value.toLowerCase()));
    const visible = rows.slice(page * 25, page * 25 + 25);
    body.append(make("p", "muted", `${rows.length} records · page ${page + 1} of ${Math.max(1, Math.ceil(rows.length / 25))}`));
    body.append(kind.value === "sessions" ? table(["Project", "Agent", "Session", "Last evidence", "Whole-session tokens", "Outcome"], visible.map(s => [s.project, hostBadges([s.host]), s.id, s.last, s.tokens == null ? "Not measured" : s.tokens.toLocaleString(), s.outcome]))
      : table(["Project", "Feature", "Attempt", "Agent", "Worker status", "Model"], visible.map(a => [a.project, a.feature, a.id, hostBadges([a.host]), a.status, a.model])));
    for (const [title, delta] of [["Previous", -1], ["Next", 1]]) {
      const button = make("button", "", title); button.disabled = page + delta < 0 || (page + delta) * 25 >= rows.length;
      button.addEventListener("click", () => { page += delta; list(); }); body.append(button);
    }
  }
  for (const node of [kind, search]) node.addEventListener(node === kind ? "change" : "input", () => { page = 0; list(); });
  fleet.append(kind, search, body); list();
}
function showSettings(scope = "machine") {
  fleet.append(make("h1", "", "Settings"), make("p", "muted", "Read-only effective configuration at capture time. Explicit options override local defaults; enforced machine settings remain in force. Per-run options remain in workflow records. Derived caches are never configuration authority."));
  const selector = make("select"); selector.setAttribute("aria-label", "Settings scope");
  const scopes = data.settings?.scopes || {};
  const names = {machine: "Machine"};
  for (const p of projects) names["project:" + p.id] = "Project · " + p.name;
  for (const w of workspaces) names["worktree:" + w.key] = "Worktree · " + w.label;
  for (const key of Object.keys(scopes)) { const option = make("option", "", names[key] || key); option.value = key; selector.append(option); }
  selector.value = scopes[scope] ? scope : "machine";
  if (scope !== "machine" && !scopes[scope]) fleet.append(make("p", "p-warning", "Settings for this scope were not captured; showing machine settings."));
  selector.addEventListener("change", () => { location.hash = "settings/" + selector.value; }); fleet.append(selector);
  const settings = scopes[selector.value];
  if (!settings) return fleet.append(make("p", "p-empty", "Settings were not captured. Regenerate the board."));
  if (settings.error) fleet.append(make("p", "p-warning", settings.error));
  fleet.append(table(["Setting", "Effective value", "State", "Source", "Previous layers"], settings.rows.map(r => [r.key, JSON.stringify(r.value), r.status, r.source, r.history.map(h => `${h.layer}: ${JSON.stringify(h.value)}`).join(" → ")])));
  fleet.append(make("h2", "", "Configuration layers"), table(["Layer", "Source", "Available"], settings.layers.map(l => [l.layer, l.path, l.present ? "Yes" : "No"])));
  fleet.append(make("h2", "", "Storage"), table(["Purpose", "Location"], Object.entries(settings.storage)));
  fleet.append(make("h2", "", "Shared runtime"), table(["Property", "Value"], Object.entries(data.settings.shared_runtime || {})));
  fleet.append(make("h2", "", "Reporting and telemetry"), make("p", "", settings.telemetry), make("p", "muted", "Scan roots: " + data.settings.scan_roots.join(" · ")));
  fleet.append(make("h2", "", "Credential availability"), table(["Credential", "State"], Object.entries(settings.credentials)));
  fleet.append(make("h2", "", "Host integrations"), make("p", "muted", "Cached versions do not establish which plugin is active in an existing host process."));
  fleet.append(table(["Agent", "CLI on PATH", "Cached plugin versions", "Board runtime", "Observation"], data.settings.integrations.map(i => [hostBadges([i.host]), i.cli_available ? "Yes" : "No", i.cached_versions.join(", ") || "Not established", i.runtime_version, i.status])));
}
function route() {
  let parts;
  try { parts = location.hash.slice(1).split("/").map(decodeURIComponent); } catch { parts = ["projects"]; }
  const [view, id] = parts;
  panel.hidden = true; panel.replaceChildren(); fleet.hidden = false; fleet.replaceChildren();
  document.getElementById("workflow-picker").hidden = view !== "workflow";
  for (const item of nav.children) item.setAttribute("aria-current", item.href.endsWith("#" + (view === "project" || view === "workflow" ? "projects" : view || "projects")) ? "page" : "false");
  if (view === "workflow") {
    const feature = data.features.find(f => f.identity === id);
    if (!feature) return fleet.append(make("p", "p-empty", "Workflow not found in this snapshot."));
    fleet.append(link("Projects", "projects"), document.createTextNode(" / "), link(feature.project, "project/" + feature.project_id));
    selector.value = id; selectedStage = null; selectedEvent = null; panel.hidden = false; renderWorkflow();
  } else if (view === "project") showProject(id);
  else if (view === "activity") showActivity();
  else if (view === "settings") showSettings(id);
  else showProjects();
  const heading = (panel.hidden ? fleet : panel).querySelector("h1");
  if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus({preventScroll: true}); }
  window.scrollTo?.(0, 0);
}
window.addEventListener("hashchange", route);
if (!location.hash && data.selected_feature) location.hash = "workflow/" + encodeURIComponent(data.selected_feature);
route();
