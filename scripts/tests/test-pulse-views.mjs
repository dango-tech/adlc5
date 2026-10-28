// DOM-contract unit test: routes, project grouping, pagination, and read-only settings.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
class Element {
  children = []; listeners = {}; attributes = {}; dataset = {}; hidden = false; value = ''; text = '';
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(n => n.textContent ?? n).join(' '); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.text = ''; this.children = nodes; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, value) { this.listeners[key] = value; }
  querySelector() { return null; }
}
const ids = Object.fromEntries(['snapshot', 'feature', 'features', 'capture', 'fleet', 'navigation', 'workflow-picker'].map(id => [id, new Element()]));
const feature = {id: 'export', identity: 'wf-1', project_id: 'p1', project: 'Application', workspace_key: 'w1', workspace_label: '~/app/worktree', hosts: ['claude', 'codex'], archive_id: null,
  lifecycle: {stage: 'specify', step: 'specify-2-requirements'}, evidence: {pr_ready: {status: 'unavailable'}, checks: {status: 'unavailable'}, review: {status: 'unavailable'}},
  usage: {known_cost_usd: null}, capture: {}, events: [], receipts: [], next_action: {label: 'Clarify requirements'}};
const stale = {...feature, id: 'alexa', identity: 'wf-2', lifecycle: {stage: 'implement', step: 'implement-2-verify', stage_status: {implement: 'in_progress'}},
  evidence: {pr_ready: {status: 'historical'}, checks: {status: 'stale', recorded_passed: 1, required: 1}, review: {status: 'fail'}}, capture: {stable: true, freshness: 'available'},
  usage: {known_cost_usd: null}, evaluation: {reason: 'No complete evaluation records'}, next_action: {label: 'Rerun the required checks', reason_code: 'evidence_stale'},
  summary: {spec: {title: 'Alexa caregiver experience', summary: 'Hands-free shared history.'}, stories: [{id: 'S-1', title: 'Read API', status: 'implementation_complete', done: true}, {id: 'S-2', title: 'Undo', status: 'pending', done: false}], stories_done: 1,
    delivery: {branch: 'feat/alexa', base: 'main', pr_url: null, substeps: {qa: 'pending'}}, checks: {time: '2026-10-13T07:47:00Z', results: [{id: 'lint', status: 'pass', required: true, exit_code: 0, log: 'evidence/check-0.log'}]},
    review: {disposition: 'fail', time: '2026-10-13T05:24:00Z', blocking_findings: ['Missing auth check'], notes: []}, gate: {last_result: 'fail', step: 'implement-2-verify'}, pending_questions: 0}};
const settings = {rows: [{key: 'defaults.summary', value: 'brief', status: 'inherited', source: '~/.adlc5/config.yaml', history: []}], layers: [], storage: {}, credentials: {}, telemetry: 'Not enabled'};
ids.snapshot.textContent = JSON.stringify({generated_at: 'fixture', features: [feature, stale], fleet: {scope: 'Captured history', projects: [{id: 'p1', name: 'Application', workspace_keys: ['w1', 'w2']}, {id: 'p2', name: 'Framework', workspace_keys: ['w3']}], workspace_inventory: [{key: 'w1', project_id: 'p1', label: '~/app/worktree', hosts: ['claude', 'codex']}],
  sessions: Array.from({length: 60}, (_, i) => ({id: 'session-' + i, project: 'Application', host: 'codex', outcome: 'Not measured', workspace_keys: ['w1'], workspace_labels: {w1: '~/app/worktree'},
    ...(i === 0 ? {title: 'Ship Alexa reminders', actions: ['adlc5:implement', 'gate'], features: ['alexa'], tokens: 2500000} : {})})), attempts: []},
  home_uri: 'file:///home/u',
  settings: {scopes: {machine: settings}, integrations: [], scan_roots: [], shared_runtime: {version: 'fixture'}}});
const events = {};
const context = vm.createContext({document: {getElementById: id => ids[id], createElement: () => new Element(), createElementNS: () => new Element(), createTextNode: value => ({textContent: String(value)})}, Node: Element, location: {hash: ''}, window: {addEventListener: (name, fn) => events[name] = fn}});
vm.runInContext(fs.readFileSync(new URL('../../shared/pulse/board.js', import.meta.url), 'utf8'), context);
const navigate = hash => { context.location.hash = '#' + hash; events.hashchange(); };
assert.match(ids.fleet.textContent, /Your projects/);
assert.equal(ids.features.hidden, true);
navigate('project/p1'); assert.match(ids.fleet.textContent, /export/); assert.match(ids.fleet.textContent, /Claude Code/); assert.match(ids.fleet.textContent, /Codex/);
navigate('workflow/wf-1'); assert.equal(ids.features.hidden, false); assert.match(ids.features.textContent, /Clarify requirements/);
navigate('workflow/wf-2'); const page = ids.features.textContent;
for (const text of ['Alexa caregiver experience', 'Hands-free shared history.', 'Branch feat/alexa → main', 'No pull request yet', 'Blocked', 'Check results are out of date', 'They passed 2026-10-13 07:47 UTC',
  'Review blocked by 1 finding', 'Missing auth check', 'Last PR-ready gate run failed at implement-2-verify', '1 story not finished', '1 of 2 done', 'S-2 · Undo', 'qa · pending', 'evidence/check-0.log'])
  assert.ok(page.includes(text), 'workflow page shows: ' + text);
assert.match(page, /Not measured yet: Known usage cost, Agent cost \(transcripts\), Outcome success, Projected cost savings, Escaped defects, Rework/);
assert.match(page, /Agent tokens \(transcripts\) 2\.5M 1 session/);
const hrefs = node => [node.href, ...(node.children || []).flatMap(hrefs)].filter(Boolean);
assert.ok(hrefs(ids.features).includes('file:///home/u/app/worktree'), 'worktree links to its folder');
assert.doesNotMatch(page, /Host not recorded/);
assert.match(page, /Agent sessions on this feature/); assert.match(page, /Ship Alexa reminders/);
navigate('activity'); assert.equal(ids.features.hidden, true); assert.match(ids.fleet.textContent, /60 records/);
assert.match(ids.fleet.textContent, /Ship Alexa reminders session-0/); assert.match(ids.fleet.textContent, /adlc5:implement, gate/);
assert.match(ids.fleet.textContent, /alexa implement-2-verify · Check results are out of date/); assert.match(ids.fleet.textContent, /Untitled session session-1/); assert.match(ids.fleet.textContent, /session-24/); assert.doesNotMatch(ids.fleet.textContent, /session-25/);
navigate('settings'); assert.match(ids.fleet.textContent, /defaults.summary/); assert.match(ids.fleet.textContent, /adlc5 config set defaults.summary 'brief' --scope machine/); assert.doesNotMatch(ids.fleet.textContent, /session-0/);
navigate('project/p2'); assert.match(ids.fleet.textContent, /No ADLC5 workflows have been started in this project yet/); assert.doesNotMatch(ids.fleet.textContent, /No workflows match this filter/);
navigate('project/p1'); assert.match(ids.fleet.textContent, /Recent ADLC5 sessions \(10 of 60\)/);
navigate('project/missing'); assert.match(ids.fleet.textContent, /Project not found/);
console.log('PASS: project, workflow status summary, activity pagination and settings routes');
