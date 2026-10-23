"""Frozen incomplete starting point for interaction and recovery evaluation."""


def display_name(value):
    return value.title()


def ordered(items):
    return sorted(items, key=lambda item: item['name'])


def export_records(records, tenant, role):
    return records


def migrate(path):
    raise NotImplementedError('schema version two migration')


def deliver(send, payload, key, delivered):
    return send(payload, key)
