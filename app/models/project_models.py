from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict, field
from typing import Optional, List


@dataclass
class CopierItem:
    title: str
    target_dir: str
    history_dir: str = ""
    pattern: str = "*.csv"


@dataclass
class ScriptItem:
    path: str
    args: str = ""
    workdir: Optional[str] = None


@dataclass
class LinkItem:
    title: str
    target: str  # url or path


@dataclass
class ProcessDef:
    id: str
    name: str
    description: str
    is_pinned: bool
    scripts: List[ScriptItem] = field(default_factory=list)
    links: List[LinkItem] = field(default_factory=list)
    copiers: List[CopierItem] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "ProcessDef":
        # tolerate old singular key
        if "copier" in d and "copiers" not in d:
            d["copiers"] = d.pop("copier")

        raw_copiers = d.get("copiers", [])
        if isinstance(raw_copiers, dict):
            raw_copiers = [raw_copiers]

        return ProcessDef(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Sin nombre"),
            description=d.get("description", ""),
            is_pinned=d.get("is_pinned",False),
            scripts=[ScriptItem(**s) for s in d.get("scripts", [])],
            links=[LinkItem(**l) for l in d.get("links", [])],
            copiers=[CopierItem(**c) for c in raw_copiers],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "is_pinned":self.is_pinned,
            "description": self.description,
            "scripts": [asdict(s) for s in self.scripts],
            "links": [asdict(l) for l in self.links],
            "copiers": [asdict(c) for c in self.copiers],
        }
