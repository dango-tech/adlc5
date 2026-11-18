"""Consumer used by the nightly stock report."""
import json
from pathlib import Path


def read_stock(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("stock must be a JSON array")
    return [(row["sku"], row["quantity"]) for row in rows]
