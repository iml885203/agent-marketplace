"""Validate the supported skills-and-mods schema subset, paths, and generated files."""
import json
import re
from pathlib import Path
from sync import ROOT, outputs


def require(condition, message):
    if not condition:
        raise SystemExit(message)

catalog = json.loads((ROOT / "catalog.json").read_text())
require(set(catalog) == {"name", "owner", "plugins"}, "Invalid catalog fields")
require(catalog["plugins"], "Empty plugin catalog")
names = [p["name"] for p in catalog["plugins"]]
require(len(names) == len(set(names)), "Duplicate plugin names")
for item in catalog["plugins"]:
    require({"name", "version", "description"} <= set(item) <= {"name", "version", "description", "kind", "license"}, "Invalid plugin fields")
    require(item.get("kind", "skills") in {"skills", "mod"}, "Invalid plugin kind")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["name"]), "Invalid plugin name")
    require(re.fullmatch(r"\d+\.\d+\.\d+", item["version"]), "Invalid version")
    require(isinstance(item["description"], str) and item["description"], "Missing description")
    plugin = ROOT / "plugins" / item["name"]
    require(plugin.resolve().is_relative_to(ROOT), "Plugin escapes root")
    if item.get("kind") == "mod":
        hooks = plugin / "hooks" / "hooks.json"
        require(hooks.is_file(), "Missing hooks/hooks.json")
        modules = json.loads(hooks.read_text()).get("modules")
        require(modules and all((hooks.parent / m).is_file() for m in modules), "Missing hooks module")
        require((plugin / "types" / "index.d.ts").is_file(), "Missing types/index.d.ts")
        continue
    skills = list((plugin / "skills").glob("*/SKILL.md"))
    require(skills, "Missing skills")
    for skill in skills:
        text = skill.read_text()
        require(text.startswith("---\n"), "Missing frontmatter")
        front, body = text[4:].split("\n---\n", 1)
        fields = dict(line.split(": ", 1) for line in front.splitlines())
        require(set(fields) == {"name", "description"}, "Invalid skill frontmatter")
        require(fields["name"] == skill.parent.name, "Skill name mismatch")
        require(fields["description"] and body.strip(), "Empty skill")
for relative, expected in outputs().items():
    path = ROOT / relative
    require(path.is_file() and path.read_text() == expected, f"Stale metadata: {relative}")
    json.loads(path.read_text())
for path in ROOT.rglob("*"):
    require(not path.is_symlink(), f"Unexpected symlink: {path}")
print("PASS: schema subset, JSON, unique names, paths, skills, mods, generation consistency")
