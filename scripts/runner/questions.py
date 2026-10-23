"""Revision-bound product questions, separate from host permission requests."""
from __future__ import annotations

from pathlib import Path
import json

from lib.requirements_readiness import NAME, load_record, prepare, text


class StaleQuestion(ValueError):
    """Current inputs no longer match the decision being answered."""


def intent(workspace: Path, feature: str) -> str:
    path = workspace / '.adlc5' / feature / NAME
    sources = [entry['path'] for entry in load_record(path)['sources']] if path.is_file() else []
    return prepare(workspace, feature, sources)['intent_sha256']


def pending(workspace: Path, feature: str, result: dict, attempt_id: str, step: str, host: str) -> dict:
    question = result.get('question', 'Human input required')
    denials = result.get('denied_actions', [])
    if not isinstance(denials, list) or any(not isinstance(item, dict) for item in denials):
        raise ValueError('denied_actions must be an array of permission denials')
    base = {'id': attempt_id, 'step': step, 'host': host, 'denied_actions': denials}
    if denials:
        if not isinstance(question, str):
            raise ValueError('permission request must contain a text question')
        from lib.completion_evidence import fingerprint
        return {**base, 'category': 'permission', 'question': question,
                'input_sha256': fingerprint(workspace, feature)}
    if isinstance(question, str):
        text(question, 'question')
        # shortcut: old workers lack decision references; retain text with revision safety during migration.
        return {**base, 'category': 'product', 'question': question, 'intent_sha256': intent(workspace, feature)}
    if not isinstance(question, dict):
        raise ValueError('question must be text or a structured product decision')
    required = {'decision_id', 'category', 'text', 'rationale', 'recommendation', 'alternatives', 'requirement_ids', 'intent_sha256'}
    if set(question) != required or question['category'] != 'product':
        raise ValueError('invalid structured product question fields')
    for key in ('decision_id', 'text', 'rationale', 'recommendation'):
        text(question[key], key)
    for key in ('alternatives', 'requirement_ids'):
        if not isinstance(question[key], list) or key == 'requirement_ids' and not question[key]:
            raise ValueError(f'{key} must be an array, with affected requirements supplied')
        for value in question[key]:
            text(value, key)
    if question['intent_sha256'] != intent(workspace, feature):
        raise ValueError('question references stale intent; reassess before asking')
    if any(entry.get('decision_id') == question['decision_id'] for entry in current_answers(workspace, feature)):
        raise ValueError('decision already answered for this intent; reuse the recorded answer')
    return {**base, **question, 'question': question['text']}


def check_current(workspace: Path, feature: str, question: dict) -> None:
    if question.get('category') == 'permission' and question.get('input_sha256'):
        from lib.completion_evidence import fingerprint
        if question['input_sha256'] != fingerprint(workspace, feature):
            raise StaleQuestion('permission request references superseded inputs; request current authorization')
    if question.get('category') == 'product':
        if question.get('denied_actions'):
            raise ValueError('product decisions cannot authorize commands')
        if question.get('intent_sha256') != intent(workspace, feature):
            raise StaleQuestion('question references superseded intent; reassess and ask a new question')


def current_answers(workspace: Path, feature: str) -> list[dict]:
    path = workspace / '.adlc5' / feature / 'pilot/answers.jsonl'
    if not path.exists():
        return []
    entries = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if any(not isinstance(entry, dict) for entry in entries):
        raise ValueError('answer journal entries must be objects')
    legacy = [dict(entry, legacy_unbound=True) for entry in entries if entry.get('category') in (None, 'legacy')]
    if not any(entry.get('category') == 'product' for entry in entries):
        return legacy
    current = intent(workspace, feature)
    return legacy + [entry for entry in entries if entry.get('category') == 'product' and entry.get('intent_sha256') == current]
