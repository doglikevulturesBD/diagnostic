import json
from pathlib import Path

def load_json(path: str):
    p = Path(path)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)
