import json
from pathlib import Path


def load_module(body_part: str):
    path = Path("modules") / f"{body_part}.json"
    if not path.exists():
        raise FileNotFoundError(f"No module found for {body_part}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

