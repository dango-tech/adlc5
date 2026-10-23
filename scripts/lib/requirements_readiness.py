"""Revision-bound requirements evidence; not authentication against local writers."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from lib.policies_load import load_policies, find_policies_path, profile_name, profile_risk_errors
from lib.state_v2 import load_feature_state, atomic_write_json

NAME = 'requirements-readiness.json'
COVERAGE = {'behavior', 'contradictions', 'negative_cases', 'assumptions'}
PLACEHOLDER = re.compile(r'(?im)^\s*(?:[-*]\s*)?(?:TBD|TODO|FIXME|\[TODO\]|\[TBD\])(?:\b|\s|$)')


def folder(workspace: Path, feature: str) -> Path:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', feature):
        raise ValueError('feature must be kebab-case')
    return safe_path(workspace, f'.adlc5/{feature}', directory=True)


def safe_path(workspace: Path, name: str, *, directory=False) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('evidence path must be workspace-relative without traversal')
    path = workspace / name
    if not path.resolve().is_relative_to(workspace.resolve()):
        raise ValueError('evidence path escapes workspace')
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f'missing evidence path: {name}')
    return path


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def source(workspace: Path, name: str) -> dict:
    path = safe_path(workspace, name)
    return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def context(workspace: Path, feature: str) -> tuple[dict, list[str]]:
    folder(workspace, feature)
    state = load_feature_state(workspace, feature)
    if not isinstance(state, dict) or state.get('schema_version') != '3.0' or state.get('feature') != feature:
        raise ValueError('canonical state missing')
    policies = load_policies(workspace, feature)
    names = [f'.adlc5/{feature}/spec-handoff.md', f'.adlc5/{feature}/risk.json']
    if profile_name(policies) == 'tiny':
        names.append(f'.adlc5/{feature}/change.md')
    policy = find_policies_path(workspace, feature)
    if policy:
        names.append(str(policy.relative_to(workspace)))
    names += [name for name in ('AGENTS.md', '.agents/architecture.yaml', '.agents/boundaries.yaml', '.agents/commands.yaml')
              if (workspace / name).exists()]
    # Lifecycle position and implementation status deliberately do not affect intent.
    return {'scope': state.get('scope'), 'scale_nfrs': state.get('scale_nfrs'), 'policies': policies}, sorted(names)


def prepare(workspace: Path, feature: str, extra_sources=()) -> dict:
    inputs, names = context(workspace, feature)
    if any(not isinstance(name, str) for name in extra_sources):
        raise ValueError('additional intent sources must be file paths')
    names = sorted(set(names) | set(extra_sources))
    sources = [source(workspace, name) for name in names]
    return {'schema_version': 1, 'feature': feature, 'sources': sources,
            'intent_sha256': digest({'sources': sources, 'context': inputs}),
            'requirements': [], 'decisions': [],
            'review': {'author_session_id': '', 'reviewer_session_id': '',
                       'disposition': 'revise', 'coverage': [], 'findings': []}}


def object_keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('invalid readiness object fields: expected ' + ', '.join(required))


def text(value, label):
    if not isinstance(value, str) or not value.strip() or PLACEHOLDER.search(value):
        raise ValueError(f'{label} must contain non-placeholder text')


def items(value, label, *, nonempty=False):
    if not isinstance(value, list) or nonempty and not value:
        raise ValueError(f'{label} must be {"a nonempty" if nonempty else "an"} array')
    return value


def unique(records, label):
    ids = []
    for item in records:
        if not isinstance(item, dict):
            raise ValueError(f'{label} entries must be objects')
        text(item.get('id'), label + ' id')
        ids.append(item['id'])
    if len(set(ids)) != len(ids):
        raise ValueError(f'duplicate {label} ids')
    return set(ids)


def document(path: Path):
    content = path.read_text(encoding='utf-8')
    if PLACEHOLDER.search(content):
        raise ValueError(f'unresolved placeholder in {path.name}')
    lines = content.splitlines()
    headings = [(n, len(m[1])) for n, line in enumerate(lines)
                if (m := re.match(r'^(#{1,6})\s+', line))]
    for n, level in headings:
        end = next((i for i, depth in headings if i > n and depth <= level), len(lines))
        body = '\n'.join(line for line in lines[n + 1:end] if not re.match(r'^#{1,6}\s+', line)).strip()
        if not body:
            raise ValueError(f'empty requirement section in {path.name}: {lines[n]}')
    if not '\n'.join(line for line in lines if not re.match(r'^#{1,6}\s+', line)).strip():
        raise ValueError(f'empty requirements document: {path.name}')


def validate(workspace: Path, feature: str, value: dict):
    object_keys(value, ('schema_version', 'feature', 'sources', 'intent_sha256', 'requirements', 'decisions', 'review'), ('delivery',))
    if type(value['schema_version']) is not int or value['schema_version'] != 1 or value['feature'] != feature:
        raise ValueError('unsupported readiness schema or feature identity')
    inputs, required = context(workspace, feature)
    risk_errors = profile_risk_errors(workspace, feature, inputs['policies'])
    if risk_errors:
        raise ValueError('; '.join(risk_errors))
    sources = items(value['sources'], 'sources', nonempty=True)
    names = []
    for entry in sources:
        object_keys(entry, ('path', 'sha256'))
        name = entry['path']
        if not isinstance(name, str) or Path(name).name in (NAME, 'state.json'):
            raise ValueError('intent source cannot reference readiness or mutable lifecycle state')
        if source(workspace, name) != entry:
            raise ValueError(f'stale source: {name}; prepare and reassess current intent')
        names.append(name)
    if len(set(names)) != len(names) or not set(required) <= set(names):
        raise ValueError('duplicate or missing mandatory intent sources')
    if value['intent_sha256'] != digest({'sources': sources, 'context': inputs}):
        raise ValueError('stale intent review: scope or effective policy changed')
    for name in required:
        if name.endswith(('spec-handoff.md', 'change.md')):
            document(safe_path(workspace, name))
    requirements = items(value['requirements'], 'requirements', nonempty=True)
    requirement_ids = unique(requirements, 'requirement')
    for item in requirements:
        object_keys(item, ('id', 'source', 'acceptance'))
        if not isinstance(item['source'], str) or item['source'] not in names or not item['source'].endswith('.md'):
            raise ValueError('requirement source must reference a declared intent document')
        for scenario in items(item['acceptance'], 'acceptance', nonempty=True):
            text(scenario, 'acceptance scenario')
        document(safe_path(workspace, item['source']))
    decisions = items(value['decisions'], 'decisions')
    unique(decisions, 'decision')
    for item in decisions:
        object_keys(item, ('id', 'requirement_ids', 'disposition', 'status', 'blocking', 'rationale', 'evidence', 'revisit_when'), ('answer',))
        refs = items(item['requirement_ids'], 'requirement_ids', nonempty=True)
        if any(not isinstance(ref, str) or ref not in requirement_ids for ref in refs):
            raise ValueError('unknown requirement in decision')
        if type(item['blocking']) is not bool or item['status'] != 'resolved':
            raise ValueError('unresolved decision: resolve or remove out-of-scope intent before progression')
        if item['disposition'] not in ('inspect', 'research', 'experiment', 'ask', 'assume'):
            raise ValueError('unknown decision disposition')
        text(item['rationale'], 'decision rationale')
        text(item['revisit_when'], 'decision revisit condition')
        evidence = items(item['evidence'], 'decision evidence')
        for entry in evidence:
            object_keys(entry, ('path', 'sha256'))
            if source(workspace, entry['path']) != entry:
                raise ValueError('stale decision evidence')
        if item['disposition'] in ('inspect', 'research', 'experiment', 'ask') and not evidence:
            raise ValueError('investigated or user decisions need source evidence')
        if item['disposition'] in ('ask', 'assume'):
            answer = item.get('answer')
            object_keys(answer, ('source', 'text'))
            text(answer['text'], 'answer')
            expected = 'user' if item['disposition'] == 'ask' else 'agent'
            if answer['source'] != expected:
                raise ValueError('user decisions and agent assumptions must remain distinct')
            if item['disposition'] == 'assume' and item['blocking']:
                raise ValueError('blocking decisions cannot be resolved by an assumption')
    if any('[ASSUMPTION]' in safe_path(workspace, name).read_text(encoding='utf-8')
           for name in {item['source'] for item in requirements}):
        if not any(item['disposition'] == 'assume' for item in decisions):
            raise ValueError('tagged assumptions require explicit decision records')
    review = value['review']
    object_keys(review, ('author_session_id', 'reviewer_session_id', 'disposition', 'coverage', 'findings'))
    for key in ('author_session_id', 'reviewer_session_id'):
        text(review[key], key)
        if review[key].strip().lower() in ('unknown', 'inherit', 'host default', 'agent', 'user'):
            raise ValueError('review requires actual session identities')
    coverage = items(review['coverage'], 'review coverage')
    if any(not isinstance(name, str) for name in coverage) or set(coverage) != COVERAGE or len(coverage) != len(COVERAGE):
        raise ValueError('review must cover behavior, contradictions, negative_cases, assumptions')
    if review['disposition'] != 'pass':
        raise ValueError('requirements review has not passed')
    if profile_name(inputs['policies']) == 'high_risk' and review['author_session_id'] == review['reviewer_session_id']:
        raise ValueError('high-risk requirements need an independent review session')
    findings = items(review['findings'], 'review findings')
    unique(findings, 'finding')
    for finding in findings:
        object_keys(finding, ('id', 'blocking', 'resolution'))
        if type(finding['blocking']) is not bool:
            raise ValueError('finding blocking must be boolean')
        text(finding['resolution'], 'finding resolution')
    if 'delivery' in value:
        validate_delivery(workspace, feature, value, phase='record')


OBLIGATIONS = {'authorization', 'migration', 'compatibility', 'concurrency', 'performance',
               'network', 'deployment', 'accessibility'}


def validate_delivery(workspace: Path, feature: str, value: dict, *, phase: str):
    """Plan applicability first; require traceability and evidence as work progresses."""
    delivery = value.get('delivery')
    object_keys(delivery, ('obligations', 'traceability', 'conformance', 'constraints'))
    requirements = {r['id'] for r in value['requirements']}
    decisions = {d['id'] for d in value['decisions']}
    for constraint in items(delivery['constraints'], 'delivery constraints'):
        object_keys(constraint, ('requirement_ids', 'text', 'source'))
        refs = items(constraint['requirement_ids'], 'constraint requirements', nonempty=True)
        if any(not isinstance(ref, str) or ref not in requirements for ref in refs):
            raise ValueError('unknown constraint requirement')
        text(constraint['text'], 'mandatory implementation constraint')
        object_keys(constraint['source'], ('path', 'sha256'))
        if source(workspace, constraint['source']['path']) != constraint['source']:
            raise ValueError('stale implementation constraint')
    obligations = items(delivery['obligations'], 'operational obligations')
    ids = unique(obligations, 'obligation')
    if ids != OBLIGATIONS:
        raise ValueError('assess all operational categories: ' + ', '.join(sorted(OBLIGATIONS)))
    risk = load_record(folder(workspace, feature) / 'risk.json')
    triggered = {'auth': 'authorization', 'secrets': 'authorization', 'migration': 'migration',
                 'concurrency': 'concurrency', 'public_compatibility': 'compatibility'}
    mandatory = {triggered[c] for c in risk['categories'] if c in triggered}
    for item in obligations:
        object_keys(item, ('id', 'status', 'rationale', 'requirement_ids', 'method', 'evidence'))
        text(item['rationale'], 'obligation rationale')
        refs = items(item['requirement_ids'], 'obligation requirements')
        if any(not isinstance(ref, str) or ref not in requirements for ref in refs):
            raise ValueError('unknown operational requirement')
        if item['status'] not in ('pending', 'satisfied', 'non_applicable', 'blocked'):
            raise ValueError('unknown operational evidence status')
        if item['id'] in mandatory and item['status'] == 'non_applicable':
            raise ValueError('declared risk requires operational evidence: ' + item['id'])
        if item['status'] != 'non_applicable':
            if not refs:
                raise ValueError('applicable obligations need affected requirements')
            text(item['method'], 'operational validation method')
        evidence = items(item['evidence'], 'operational evidence')
        for entry in evidence:
            object_keys(entry, ('path', 'sha256'))
            if source(workspace, entry['path']) != entry:
                raise ValueError('stale operational evidence')
        if item['status'] == 'satisfied' and not evidence:
            raise ValueError('satisfied obligations require evidence')
        if phase == 'complete' and item['status'] not in ('satisfied', 'non_applicable'):
            raise ValueError(f"unverified operational obligation: {item['id']}")
        if phase in ('tasks', 'complete') and item['status'] == 'blocked':
            raise ValueError(f"blocked operational obligation: {item['id']}")
    traces = items(delivery['traceability'], 'traceability')
    stories = {s['id'] for s in (load_feature_state(workspace, feature).get('tasks') or {}).get('stories', [])
               if s.get('type') != 'integration'}
    mapped = set()
    covered = set()
    for entry in traces:
        object_keys(entry, ('story_id', 'requirement_ids', 'decision_ids', 'acceptance_criteria'))
        story = entry['story_id']
        if not isinstance(story, str) or story in mapped or story not in stories:
            raise ValueError('unknown or duplicate story traceability')
        mapped.add(story)
        refs = items(entry['requirement_ids'], 'story requirements', nonempty=True)
        if any(not isinstance(ref, str) or ref not in requirements for ref in refs):
            raise ValueError('unknown requirement in story traceability')
        covered.update(refs)
        refs = items(entry['decision_ids'], 'story decisions')
        if any(not isinstance(ref, str) or ref not in decisions for ref in refs):
            raise ValueError('unknown decision in story traceability')
        if any(not set(d['requirement_ids']) & set(entry['requirement_ids']) for d in value['decisions'] if d['id'] in refs):
            raise ValueError('story decision must affect a mapped requirement')
        for criterion in items(entry['acceptance_criteria'], 'story acceptance', nonempty=True):
            text(criterion, 'acceptance reference')
    policies = load_policies(workspace, feature)
    if phase in ('tasks', 'complete') and profile_name(policies) != 'tiny':
        if not stories or mapped != stories or covered != requirements:
            raise ValueError('every story and requirement needs explicit traceability before implementation')
        if any(not any(d['id'] in t['decision_ids'] for t in traces) for d in value['decisions']):
            raise ValueError('every decision needs an affected story')
        from lib.simple_yaml import load_frontmatter
        specs = {}
        for directory in ('tasks/code-spec', 'delivery/code-spec'):
            for path in (folder(workspace, feature) / directory).glob('*.md'):
                safe_path(workspace, str(path.relative_to(workspace)))
                spec, _ = load_frontmatter(path.read_text(encoding='utf-8'))
                if isinstance(spec, dict) and isinstance(spec.get('story_id'), str):
                    if spec['story_id'] in specs:
                        raise ValueError('duplicate story code specs')
                    specs[spec['story_id']] = spec
        for entry in traces:
            spec = specs.get(entry['story_id'])
            if not isinstance(spec, dict) or set(entry['acceptance_criteria']) != set(spec.get('acceptance_criteria') or []):
                raise ValueError('traceability acceptance must match the story code spec')
    conformance = delivery['conformance']
    if conformance is not None:
        object_keys(conformance, ('reviewer_session_id', 'coverage', 'requirements', 'evidence'))
        text(conformance['reviewer_session_id'], 'conformance reviewer session')
        categories = items(conformance['coverage'], 'conformance coverage')
        if len(categories) != 5 or set(categories) != {'missing', 'partial', 'contradictory', 'unrequested', 'constraints'}:
            raise ValueError('conformance review must assess missing, partial, contradictory, unrequested behavior and constraints')
        refs = items(conformance['requirements'], 'reviewed requirements')
        if len(refs) != len(requirements) or set(refs) != requirements:
            raise ValueError('conformance review must cover every requirement')
        evidence = items(conformance['evidence'], 'conformance evidence', nonempty=True)
        for entry in evidence:
            object_keys(entry, ('path', 'sha256'))
            if source(workspace, entry['path']) != entry:
                raise ValueError('stale conformance evidence')
    if phase == 'complete' and conformance is None:
        raise ValueError('implementation needs an explicit intent conformance review')


def delivery_check(workspace: Path, feature: str, phase: str) -> dict:
    try:
        value = load_record(folder(workspace, feature) / NAME)
        validate(workspace, feature, value)
        validate_delivery(workspace, feature, value, phase=phase)
        return {'id': 'delivery_obligations', 'status': 'pass', 'message': f'{phase} obligations and traceability validated'}
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {'id': 'delivery_obligations', 'status': 'fail', 'message': str(exc)}


def record(workspace: Path, feature: str, value: dict):
    validate(workspace, feature, value)
    path = folder(workspace, feature) / NAME
    if path.is_symlink():
        raise ValueError('readiness artifact must not be a symlink')
    if path.is_file():
        previous = load_record(path)
        history = folder(workspace, feature) / 'evidence/readiness-history' / (digest(previous) + '.json')
        if not history.resolve().is_relative_to(workspace.resolve()):
            raise ValueError('readiness history escapes workspace')
        if history.exists() and load_record(history) != previous:
            raise ValueError('readiness history conflict; preserve and inspect existing evidence')
        if not history.exists():
            atomic_write_json(history, previous)
    atomic_write_json(path, value)


def delivery_draft(workspace: Path, feature: str) -> dict:
    value = load_record(folder(workspace, feature) / NAME)
    validate(workspace, feature, value)
    value.setdefault('delivery', {'obligations': [
        {'id': name, 'status': 'pending', 'rationale': '', 'requirement_ids': [r['id'] for r in value['requirements']],
         'method': '', 'evidence': []} for name in sorted(OBLIGATIONS)], 'traceability': [], 'conformance': None, 'constraints': []})
    return value


def impact(workspace: Path, feature: str) -> dict:
    value = load_record(folder(workspace, feature) / NAME)
    current = prepare(workspace, feature, [entry['path'] for entry in value['sources']])
    changed = value['intent_sha256'] != current['intent_sha256']
    return {'status': 'stale' if changed else 'current', 'previous_intent': value['intent_sha256'],
            'current_intent': current['intent_sha256'], 'changed_sources': [entry['path'] for entry in current['sources']
                if entry not in value['sources']],
            'affected_requirements': [r['id'] for r in value['requirements']] if changed else [],
            'affected_stories': [s['id'] for s in (load_feature_state(workspace, feature).get('tasks') or {}).get('stories', [])] if changed else [],
            'action': 'Reassess risk, decisions, operational obligations and traceability; record a new review. Preserve code and anchors; rerun affected evidence.' if changed else 'No intent change detected.'}


def load_record(path: Path) -> dict:
    def mapping(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f'duplicate readiness field: {key}')
            value[key] = item
        return value
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=mapping)


def check(workspace: Path, feature: str) -> dict:
    try:
        path = folder(workspace, feature) / NAME
        if path.is_symlink():
            raise ValueError('readiness artifact must not be a symlink')
        value = load_record(path)
        validate(workspace, feature, value)
        return {'id': 'requirements_readiness', 'status': 'pass', 'message': 'current intent and decision review recorded'}
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {'id': 'requirements_readiness', 'status': 'fail',
                'message': f'{exc}; use adlc5 readiness prepare, review the record, then readiness record --file PATH'}
