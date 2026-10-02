"""Generate platform metadata; --check reports drift without changing files."""
import argparse
import json
from pathlib import Path

from marketplace import ROOT, load_catalog, require, selected_platforms, validate_sources


def outputs(root=ROOT):
    catalog = load_catalog(root)
    validate_sources(root, catalog)
    name, owner = catalog["name"], catalog["owner"]
    claude_entries, codex_entries, files = [], [], {}
    for item in catalog["plugins"]:
        plugin = item["name"]
        # Catalog controls must not leak into platform manifests.
        common = {key: item[key] for key in ("name", "version", "description")}
        common.update(author={"name": owner}, repository=f"https://github.com/{owner}/{name}", license=item.get("license", "MIT"))
        platforms = selected_platforms(item)
        if "claude" in platforms:
            claude_manifest = dict(common)
            if item.get("kind") == "mod" and (root / "plugins" / plugin / "types/index.d.ts").is_file():
                claude_manifest["types"] = "./types/index.d.ts"
            files[f"plugins/{plugin}/.claude-plugin/plugin.json"] = claude_manifest
            claude_entries.append({"name": plugin, "source": f"./plugins/{plugin}", "description": item["description"]})
        if "codex" in platforms:
            files[f"plugins/{plugin}/.codex-plugin/plugin.json"] = dict(common, skills="./skills/", interface={"displayName": plugin.replace("-", " ").title(), "shortDescription": item["description"], "developerName": owner, "category": "Productivity"})
            codex_entries.append({"name": plugin, "source": {"source": "local", "path": f"./plugins/{plugin}"}, "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"})
    files[".claude-plugin/marketplace.json"] = {"name": name, "description": "Personal skills and mods for Claude Code and Codex.", "owner": {"name": owner}, "plugins": claude_entries}
    files[".agents/plugins/marketplace.json"] = {"name": name, "interface": {"displayName": "Agent Marketplace"}, "plugins": codex_entries}
    return {path: json.dumps(value, indent=2) + "\n" for path, value in files.items()}


def obsolete_outputs(root, expected):
    # These exact manifest filenames are generator-owned, including removed plugins.
    found = set()
    for platform in ("claude", "codex"):
        for path in root.glob(f"plugins/*/.{platform}-plugin/plugin.json"):
            found.add(path.relative_to(root).as_posix())
    return sorted(found - set(expected))


def sync(root=ROOT, check=False):
    root = Path(root)
    expected = outputs(root)  # Validate all inputs before writing or deleting anything.
    obsolete = obsolete_outputs(root, expected)
    # Preflight every target to avoid overwriting directories or following links.
    for relative in list(expected) + obsolete:
        path = root / relative
        require(not path.exists() or path.is_file(), f"Generated output is not a file: {relative}")
        require(path.resolve().is_relative_to(root.resolve()), f"Output escapes root: {relative}")
        for parent in path.parents:
            if parent == root:
                break
            require(not parent.exists() or parent.is_dir(), f"Output parent is not a directory: {parent}")
    changed = [relative for relative, content in expected.items()
               if not (root / relative).is_file() or (root / relative).read_text(encoding="utf-8") != content]
    if check:
        require(not changed and not obsolete, "Stale generated files: " + ", ".join(changed + obsolete))
        return
    for relative, content in expected.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for relative in obsolete:
        (root / relative).unlink()  # Keep source files and directories intact.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        sync(check=args.check)
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error
    print("Generated metadata is consistent." if args.check else "Generated platform metadata and removed obsolete manifests.")
