"""Generate platform metadata from catalog.json; Python standard library only."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def outputs():
    catalog = json.loads((ROOT / "catalog.json").read_text())
    name, owner = catalog["name"], catalog["owner"]
    claude_entries, codex_entries, files = [], [], {}
    for item in catalog["plugins"]:
        plugin = item["name"]
        common = dict(item, author={"name": owner}, repository=f"https://github.com/{owner}/{name}", license="MIT")
        files[f"plugins/{plugin}/.claude-plugin/plugin.json"] = common
        files[f"plugins/{plugin}/.codex-plugin/plugin.json"] = dict(common, skills="./skills/", interface={"displayName": plugin.replace("-", " ").title(), "shortDescription": item["description"], "developerName": owner, "category": "Productivity"})
        claude_entries.append({"name": plugin, "source": f"./plugins/{plugin}", "description": item["description"]})
        codex_entries.append({"name": plugin, "source": {"source": "local", "path": f"./plugins/{plugin}"}, "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"})
    files[".claude-plugin/marketplace.json"] = {"name": name, "description": "Personal skills for Claude Code and Codex.", "owner": {"name": owner}, "plugins": claude_entries}
    files[".agents/plugins/marketplace.json"] = {"name": name, "interface": {"displayName": "Agent Marketplace"}, "plugins": codex_entries}
    return {path: json.dumps(value, indent=2) + "\n" for path, value in files.items()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for relative, content in outputs().items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_text() != content:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if stale:
        raise SystemExit("Stale generated files: " + ", ".join(stale))
    print("Generated metadata is consistent." if args.check else "Generated platform metadata.")
