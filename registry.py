from __future__ import annotations
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass
class ModelVersion:
    name: str
    version: str
    sport: str
    target: str
    features: list[str]
    metrics: dict
    artifact: dict
    created_at: str
    status: str = "candidate"

class ModelRegistry:
    def __init__(self,path="data/model_registry.json"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def load(self):
        if not self.path.exists(): return []
        return json.loads(self.path.read_text(encoding="utf-8"))
    def register(self, model: ModelVersion):
        rows=self.load(); rows=[r for r in rows if not (r["name"]==model.name and r["version"]==model.version)]; rows.append(asdict(model)); self.path.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding="utf-8")
    def promote(self,name,version):
        rows=self.load()
        for r in rows:
            if r["name"]==name: r["status"]="production" if r["version"]==version else "archived"
        self.path.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding="utf-8")
