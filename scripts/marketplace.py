"""Catalog and source validation for skills and Claude-only hooks/Mods."""
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("claude", "codex")
MODULE_EXTENSIONS = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".mts", ".cts", ".tsx"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read JSON at {path}: {error}") from error


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value)


def selected_platforms(item):
    return item.get("platforms", ["claude"] if item.get("kind") == "mod" else list(PLATFORMS))


def load_catalog(root=ROOT):
    catalog = read_json(root / "catalog.json")
    require(isinstance(catalog, dict) and set(catalog) == {"name", "owner", "plugins"}, "Invalid catalog fields")
    require(identifier(catalog["name"]), "Invalid marketplace name")
    require(isinstance(catalog["owner"], str) and re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", catalog["owner"]), "Invalid owner")
    require(isinstance(catalog["plugins"], list) and catalog["plugins"], "Expected a nonempty plugin array")
    names = set()
    for item in catalog["plugins"]:
        required = {"name", "version", "description"}
        require(isinstance(item, dict) and required <= set(item) <= required | {"platforms", "kind", "license"}, "Invalid plugin fields")
        require(identifier(item["name"]), "Invalid plugin name")
        require(item["name"] not in names, "Duplicate plugin names")
        names.add(item["name"])
        require(isinstance(item["version"], str) and re.fullmatch(r"\d+\.\d+\.\d+", item["version"]), "Invalid version")
        require(isinstance(item["description"], str) and item["description"].strip(), "Missing description")
        require(item.get("kind", "skills") in ("skills", "mod"), "Invalid plugin kind")
        require(isinstance(item.get("license", "MIT"), str) and item.get("license", "MIT").strip(), "Invalid plugin license")
        platforms = selected_platforms(item)
        require(isinstance(platforms, list) and platforms, "platforms must be a nonempty array")
        require(all(isinstance(p, str) and p in PLATFORMS for p in platforms), "Unsupported platform; use claude or codex")
        require(len(platforms) == len(set(platforms)), "Duplicate platforms")
        if item.get("kind") == "mod":
            require(platforms == ["claude"], "Mods support only the claude platform")
    return catalog


def validate_tree(root):
    # Reject directory links too: never follow a plugin or output path outside this repo.
    for path in root.rglob("*"):
        if path.relative_to(root).parts[0] != ".git":
            require(not path.is_symlink(), f"Unexpected symlink: {path}")


def module_path(plugin, config, value):
    require(isinstance(value, str) and value and "\\" not in value, "Module path must be a relative POSIX path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ":" not in value, "Module path must be local and relative")
    target = config.parent / value
    require(target.resolve().is_relative_to(plugin.resolve()), f"Module escapes plugin root: {value}")
    require(target.is_file(), f"Missing hook module: {value}")
    require(target.suffix in MODULE_EXTENSIONS, f"Unsupported hook module extension: {value}")
    require(target.read_text(encoding="utf-8").strip(), f"Empty hook module: {value}")
    return target


def validate_hooks(plugin):
    config = plugin / "hooks" / "hooks.json"
    data = read_json(config)
    require(isinstance(data, dict) and data and set(data) <= {"modules", "hooks", "description"}, "Invalid hooks configuration fields")
    if "description" in data:
        require(isinstance(data["description"], str), "Invalid hooks description")
    present = False
    if "modules" in data:
        modules = data["modules"]
        require(isinstance(modules, list) and len(modules) == 1, "modules must contain exactly one module path")
        module_path(plugin, config, modules[0])
        present = True
    if "hooks" in data:
        events = data["hooks"]
        require(isinstance(events, dict) and events, "hooks must be a nonempty event object")
        for event, groups in events.items():
            require(isinstance(event, str) and event.strip() and isinstance(groups, list) and groups, "Invalid hook event groups")
            for group in groups:
                require(isinstance(group, dict) and set(group) <= {"matcher", "hooks"} and "hooks" in group, "Invalid hook matcher group")
                if "matcher" in group:
                    require(isinstance(group["matcher"], str), "Hook matcher must be a string")
                handlers = group["hooks"]
                require(isinstance(handlers, list) and handlers, "Hook handlers must be a nonempty array")
                for handler in handlers:
                    require(isinstance(handler, dict) and set(handler) <= {"type", "command", "timeout"} and handler.get("type") == "command", "Only command settings hooks with type, command, and optional timeout are supported; use modules for Mods")
                    require(isinstance(handler.get("command"), str) and handler["command"].strip(), "Missing hook command")
                    if "timeout" in handler:
                        timeout = handler["timeout"]
                        require(type(timeout) in (int, float) and timeout > 0, "Hook timeout must be positive")
        present = True
    require(present, "Hooks configuration has no modules or handlers")


def validate_skill(skill):
    text = skill.read_text(encoding="utf-8")
    require(text.startswith("---\n"), f"Missing skill frontmatter: {skill}")
    sections = text[4:].split("\n---\n", 1)
    require(len(sections) == 2, f"Unterminated skill frontmatter: {skill}")
    front, body = sections
    lines = front.splitlines()
    require(all(": " in line for line in lines), f"Invalid skill frontmatter: {skill}")
    pairs = [line.split(": ", 1) for line in lines]
    fields = dict(pairs)
    require(len(fields) == len(pairs) and set(fields) == {"name", "description"}, f"Invalid skill fields: {skill}")
    require(identifier(fields["name"]) and fields["name"] == skill.parent.name, f"Skill name mismatch: {skill}")
    require(fields["description"].strip() and body.strip(), f"Empty skill: {skill}")


def validate_sources(root, catalog):
    validate_tree(root)
    for item in catalog["plugins"]:
        plugin = root / "plugins" / item["name"]
        require(plugin.is_dir(), f"Missing plugin directory: {item['name']}")
        skills = list((plugin / "skills").glob("*/SKILL.md"))
        for skill in skills:
            validate_skill(skill)
        hooks = plugin / "hooks" / "hooks.json"
        types = plugin / "types" / "index.d.ts"
        if item.get("kind") == "mod":
            require(hooks.is_file(), f"Missing hooks/hooks.json: {item['name']}")
            data = read_json(hooks)
            require(isinstance(data, dict) and "modules" in data, f"Mod requires a hooks module: {item['name']}")
        if types.exists():
            require(types.is_file() and types.read_text(encoding="utf-8").strip(), f"Empty or invalid types/index.d.ts: {item['name']}")
        if hooks.exists():
            require(selected_platforms(item) == ["claude"], f"Claude hooks/Mods require platforms: [claude]: {item['name']}")
            validate_hooks(plugin)
        require(skills or hooks.is_file(), f"Plugin requires skills or Claude hooks: {item['name']}")
