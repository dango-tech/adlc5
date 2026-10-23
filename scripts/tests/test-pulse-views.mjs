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
const settings = {rows: [{key: 'defaults.summary', value: 'brief', status: 'inherited', source: '~/.adlc5/config.yaml', history: []}], layers: [], storage: {}, credentials: {}, telemetry: 'Not enabled'};
ids.snapshot.textContent = JSON.stringify({generated_at: 'fixture', features: [feature], fleet: {scope: 'Captured history', projects: [{id: 'p1', name: 'Application', workspace_keys: ['w1', 'w2']}], workspace_inventory: [{key: 'w1', project_id: 'p1', label: '~/app/worktree', hosts: ['claude', 'codex']}],
  sessions: Array.from({length: 60}, (_, i) => ({id: 'session-' + i, project: 'Application', host: 'codex', outcome: 'Not measured', workspace_keys: ['w1']})), attempts: []},
  settings: {scopes: {machine: settings}, integrations: [], scan_roots: [], shared_runtime: {version: 'fixture'}}});
const events = {};
const context = vm.createContext({document: {getElementById: id => ids[id], createElement: () => new Element(), createElementNS: () => new Element(), createTextNode: value => ({textContent: String(value)})}, Node: Element, location: {hash: ''}, window: {addEventListener: (name, fn) => events[name] = fn}});
vm.runInContext(fs.readFileSync(new URL('../../shared/pulse/board.js', import.meta.url), 'utf8'), context);
const navigate = hash => { context.location.hash = '#' + hash; events.hashchange(); };
assert.match(ids.fleet.textContent, /Your projects/);
assert.equal(ids.features.hidden, true);
navigate('project/p1'); assert.match(ids.fleet.textContent, /export/); assert.match(ids.fleet.textContent, /Claude Code/); assert.match(ids.fleet.textContent, /Codex/);
navigate('workflow/wf-1'); assert.equal(ids.features.hidden, false); assert.match(ids.features.textContent, /Clarify requirements/);
navigate('activity'); assert.equal(ids.features.hidden, true); assert.match(ids.fleet.textContent, /60 records/); assert.match(ids.fleet.textContent, /session-24/); assert.doesNotMatch(ids.fleet.textContent, /session-25/);
navigate('settings'); assert.match(ids.fleet.textContent, /defaults.summary/); assert.match(ids.fleet.textContent, /Read-only effective configuration/); assert.doesNotMatch(ids.fleet.textContent, /session-0/);
navigate('project/missing'); assert.match(ids.fleet.textContent, /Project not found/);
console.log('PASS: project, workflow, activity pagination and settings routes');
