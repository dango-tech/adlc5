"""Small inventory utility; intentionally incomplete frozen evaluation starting point."""
import json
from pathlib import Path


def label(name):
    return name.strip().title()


def total(items):
    return sum(item['quantity'] for item in items)


def search(items, query):
    return [item for item in items if query in item['name']]


def export(items):
    return json.dumps(items)


def read_item(root, name):
    return (Path(root) / name).read_text()


def save_items(path, items):
    Path(path).write_text(json.dumps(items))
