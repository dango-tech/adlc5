"""Synthetic intent reviews for kernel tests, never live review attestations."""
import json
from lib.requirements_readiness import prepare, record, OBLIGATIONS, source
from lib.simple_yaml import load_frontmatter


def reviewed_fixture(workspace, feature='demo'):
    base = workspace / '.adlc5' / feature
    for name in ('spec-handoff.md', 'change.md'):
        path = base / name
        if not path.exists():
            path.write_text('# Behavior\nPreserve the fixture behavior.\n# Acceptance\nThe independent fixture checks pass.\n')
    risk = base / 'risk.json'
    if not risk.exists():
        risk.write_text(json.dumps({'categories': [], 'uncertain': False, 'rationale': 'synthetic bounded fixture'}))
    value = prepare(workspace, feature)
    value['requirements'] = [{'id': 'FIXTURE-1', 'source': f'.adlc5/{feature}/spec-handoff.md',
                              'acceptance': ['Existing independent fixture assertions pass.']}]
    value['review'] = {'author_session_id': 'synthetic-fixture-author',
                       'reviewer_session_id': 'synthetic-fixture-reviewer', 'disposition': 'pass',
                       'coverage': ['behavior', 'contradictions', 'negative_cases', 'assumptions'], 'findings': []}
    traces = []
    for path in sorted((base / 'tasks/code-spec').glob('*.md')):
        frontmatter, _ = load_frontmatter(path.read_text())
        if frontmatter and 'acceptance_criteria' in frontmatter:
            traces.append({'story_id': frontmatter['story_id'], 'requirement_ids': ['FIXTURE-1'],
                           'decision_ids': [], 'acceptance_criteria': frontmatter['acceptance_criteria']})
    value['delivery'] = {
        'obligations': [{'id': name, 'status': 'non_applicable', 'rationale': 'Synthetic kernel fixture has no operational change.',
                         'requirement_ids': [], 'method': '', 'evidence': []} for name in sorted(OBLIGATIONS)],
        'traceability': traces, 'constraints': [],
        'conformance': {'reviewer_session_id': 'reviewer',
                        'coverage': ['missing', 'partial', 'contradictory', 'unrequested', 'constraints'],
                        'requirements': ['FIXTURE-1'], 'evidence': [source(workspace, f'.adlc5/{feature}/spec-handoff.md')]}}
    triggers = {'auth': 'authorization', 'secrets': 'authorization', 'migration': 'migration',
                'concurrency': 'concurrency', 'public_compatibility': 'compatibility'}
    required = {triggers[c] for c in json.loads(risk.read_text())['categories'] if c in triggers}
    for item in value['delivery']['obligations']:
        if item['id'] in required:
            item.update(status='satisfied', requirement_ids=['FIXTURE-1'], method='Synthetic fixture assertion.',
                        evidence=[source(workspace, f'.adlc5/{feature}/spec-handoff.md')])
    record(workspace, feature, value)
