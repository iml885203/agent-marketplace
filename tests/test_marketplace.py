"""Temporary fixtures test metadata tooling; no hook code is ever executed."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from marketplace import load_catalog
from sync import outputs, sync


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = {"name": "test-market", "owner": "example", "plugins": [
            {"name": "shared", "version": "0.1.0", "description": "Shared skill."}
        ]}
        self.save_catalog()
        self.put("plugins/shared/skills/summary/SKILL.md", "---\nname: summary\ndescription: Summarize supplied text.\n---\n\nUse the supplied text.\n")

    def put(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def save_catalog(self):
        self.put("catalog.json", json.dumps(self.catalog))

    def add_mod(self, platforms=None):
        self.catalog["plugins"].append({"name": "fixture-mod", "version": "0.1.0", "description": "Test fixture only.", "platforms": platforms if platforms is not None else ["claude"]})
        self.save_catalog()
        self.put("plugins/fixture-mod/hooks/hooks.json", json.dumps({"modules": ["./register.js"]}))
        self.put("plugins/fixture-mod/hooks/register.js", "export function register(on) {}\n")

    def rendered(self, relative):
        return json.loads(outputs(self.root)[relative])

    def test_default_both_matches_explicit_both(self):
        default = outputs(self.root)
        self.catalog["plugins"][0]["platforms"] = ["claude", "codex"]
        self.save_catalog()
        self.assertEqual(default, outputs(self.root))
        for platform in ("claude", "codex"):
            self.assertIn(f"plugins/shared/.{platform}-plugin/plugin.json", default)
        self.assertNotIn("platforms", json.loads(default["plugins/shared/.claude-plugin/plugin.json"]))

    def test_single_platform_skills(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                self.catalog["plugins"][0]["platforms"] = [platform]
                self.save_catalog()
                result = outputs(self.root)
                other = "codex" if platform == "claude" else "claude"
                self.assertIn(f"plugins/shared/.{platform}-plugin/plugin.json", result)
                self.assertNotIn(f"plugins/shared/.{other}-plugin/plugin.json", result)
                marketplace = ".agents/plugins/marketplace.json" if other == "codex" else ".claude-plugin/marketplace.json"
                self.assertEqual(json.loads(result[marketplace])["plugins"], [])

    def test_claude_only_mod_needs_no_skill(self):
        self.add_mod()
        sync(self.root)
        sync(self.root, check=True)
        claude = self.rendered(".claude-plugin/marketplace.json")["plugins"]
        codex = self.rendered(".agents/plugins/marketplace.json")["plugins"]
        self.assertEqual([p["name"] for p in claude], ["shared", "fixture-mod"])
        self.assertEqual([p["name"] for p in codex], ["shared"])
        self.assertFalse((self.root / "plugins/fixture-mod/.codex-plugin/plugin.json").exists())
        self.assertNotIn("skills", self.rendered("plugins/fixture-mod/.claude-plugin/plugin.json"))

    def test_command_hooks_without_skill(self):
        self.add_mod()
        self.put("plugins/fixture-mod/hooks/hooks.json", json.dumps({"hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "echo fixture", "timeout": 10}]}]}}))
        sync(self.root)
        sync(self.root, check=True)

    def test_module_paths_resolve_from_hooks_config(self):
        self.add_mod()
        self.put("plugins/fixture-mod/scripts/register.ts", "export function register(on) {}\n")
        self.put("plugins/fixture-mod/hooks/hooks.json", json.dumps({"modules": ["../scripts/register.ts"]}))
        sync(self.root)

    def test_existing_mod_catalog_preserves_license_and_types(self):
        self.add_mod()
        mod = self.catalog["plugins"][-1]
        del mod["platforms"]
        mod.update(kind="mod", license="SEE LICENSE IN LICENSE")
        self.save_catalog()
        self.put("plugins/fixture-mod/types/index.d.ts", "export type State = boolean;\n")
        manifest = self.rendered("plugins/fixture-mod/.claude-plugin/plugin.json")
        self.assertEqual(manifest["types"], "./types/index.d.ts")
        self.assertEqual(manifest["license"], "SEE LICENSE IN LICENSE")
        self.assertNotIn("kind", manifest)
        self.assertNotIn("platforms", manifest)
        self.assertNotIn("plugins/fixture-mod/.codex-plugin/plugin.json", outputs(self.root))

    def test_mod_types_optional_without_state(self):
        self.add_mod()
        self.catalog["plugins"][-1]["kind"] = "mod"
        self.save_catalog()
        self.assertNotIn("types", self.rendered("plugins/fixture-mod/.claude-plugin/plugin.json"))

    def test_invalid_mod_metadata(self):
        self.add_mod()
        valid = copy.deepcopy(self.catalog)
        for fields in ({"kind": "unknown"}, {"license": 42}, {"license": " "}, {"kind": "mod", "platforms": ["codex"]}):
            self.catalog = copy.deepcopy(valid)
            self.catalog["plugins"][-1].update(fields)
            self.save_catalog()
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                outputs(self.root)

    def test_mod_requires_modules_and_types_must_not_be_empty(self):
        self.add_mod()
        self.catalog["plugins"][-1]["kind"] = "mod"
        self.save_catalog()
        self.put("plugins/fixture-mod/types/index.d.ts", " ")
        with self.assertRaisesRegex(ValueError, "Empty or invalid types"):
            outputs(self.root)
        self.put("plugins/fixture-mod/types/index.d.ts", "export type State = boolean;")
        self.put("plugins/fixture-mod/hooks/hooks.json", json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo x"}]}]}}))
        with self.assertRaisesRegex(ValueError, "Mod requires a hooks module"):
            outputs(self.root)

    def test_invalid_platform_configurations(self):
        for value in ([], "claude", ["unknown"], ["claude", "claude"], [1], [None], [["claude"]]):
            with self.subTest(value=value):
                self.catalog["plugins"][0]["platforms"] = value
                self.save_catalog()
                with self.assertRaises(ValueError):
                    outputs(self.root)

    def test_invalid_catalog(self):
        valid = copy.deepcopy(self.catalog)
        mutations = [
            lambda c: c.update(plugins={}),
            lambda c: c.update(name="../escape"),
            lambda c: c.update(owner=42),
            lambda c: c["plugins"].append(copy.deepcopy(c["plugins"][0])),
            lambda c: c["plugins"][0].update(name="../escape"),
            lambda c: c["plugins"][0].update(version=1),
            lambda c: c["plugins"][0].update(description=" "),
            lambda c: c["plugins"][0].update(extra=True),
        ]
        for mutation in mutations:
            self.catalog = copy.deepcopy(valid)
            mutation(self.catalog)
            self.save_catalog()
            with self.subTest(catalog=self.catalog), self.assertRaises(ValueError):
                load_catalog(self.root)

    def test_mod_cannot_be_advertised_to_codex(self):
        for platforms in (["claude", "codex"], ["codex"]):
            with self.subTest(platforms=platforms):
                self.catalog["plugins"] = self.catalog["plugins"][:1]
                self.add_mod(platforms)
                with self.assertRaisesRegex(ValueError, "Claude hooks/Mods require"):
                    outputs(self.root)

    def test_empty_plugin_and_missing_plugin_directory(self):
        self.catalog["plugins"][0]["name"] = "empty"
        self.save_catalog()
        with self.assertRaisesRegex(ValueError, "Missing plugin directory"):
            outputs(self.root)
        (self.root / "plugins/empty").mkdir()
        with self.assertRaisesRegex(ValueError, "requires skills or Claude hooks"):
            outputs(self.root)

    def test_invalid_hooks_structures(self):
        self.add_mod()
        configs = [[], {}, {"description": "Only a description"}, {"modules": []},
                   {"modules": "./register.js"}, {"modules": ["./register.js", "./register.js"]},
                   {"modules": [None]}, {"modules": ["./register.js"], "unexpected": True},
                   {"hooks": []}, {"hooks": {}}, {"hooks": {"Stop": []}},
                   {"hooks": {"Stop": [{"hooks": []}]}},
                   {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": ""}]}]}},
                   {"hooks": {"Stop": [{"hooks": [{"type": "prompt", "prompt": "x"}]}]}},
                   {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo x", "timeout": True}]}]}}]
        for config in configs:
            self.put("plugins/fixture-mod/hooks/hooks.json", json.dumps(config))
            with self.subTest(config=config), self.assertRaises(ValueError):
                outputs(self.root)

    def test_invalid_module_paths(self):
        self.add_mod()
        self.put("outside.js", "export function register() {}")
        self.put("plugins/fixture-mod/hooks/register.txt", "non-module")
        self.put("plugins/fixture-mod/hooks/empty.js", " ")
        for path in ("./missing.js", "/tmp/register.js", "../../../outside.js", "https://example.com/register.js", "C:\\register.js", "./register.txt", "./empty.js"):
            self.put("plugins/fixture-mod/hooks/hooks.json", json.dumps({"modules": [path]}))
            with self.subTest(path=path), self.assertRaises(ValueError):
                outputs(self.root)

    def test_symlink_module_and_output_parent_rejected(self):
        self.add_mod()
        module = self.root / "plugins/fixture-mod/hooks/register.js"
        module.unlink()
        module.symlink_to(self.put("outside.js", "export function register() {}"))
        with self.assertRaisesRegex(ValueError, "Unexpected symlink"):
            sync(self.root)
        module.unlink()
        self.put("plugins/fixture-mod/hooks/register.js", "export function register() {}")
        (self.root / ".agents").symlink_to(self.root / "plugins", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unexpected symlink"):
            sync(self.root)

    def test_invalid_skill_frontmatter(self):
        for text in ("No frontmatter", "---\nname: summary\n", "---\nname: wrong\ndescription: valid\n---\nBody", "---\nname: summary\ndescription: valid\nname: summary\n---\nBody"):
            self.put("plugins/shared/skills/summary/SKILL.md", text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                outputs(self.root)

    def test_check_detects_drift_without_writing(self):
        sync(self.root)
        target = self.put("plugins/shared/.codex-plugin/plugin.json", "{}\n")
        with self.assertRaisesRegex(ValueError, "Stale generated files"):
            sync(self.root, check=True)
        self.assertEqual(target.read_text(), "{}\n")
        sync(self.root)
        sync(self.root, check=True)

    def test_platform_switch_prunes_only_obsolete_manifest(self):
        sync(self.root)
        marker = self.put("plugins/shared/.codex-plugin/keep.txt", "Keep this source")
        self.catalog["plugins"][0]["platforms"] = ["claude"]
        self.save_catalog()
        stale = self.root / "plugins/shared/.codex-plugin/plugin.json"
        with self.assertRaisesRegex(ValueError, "Stale generated files"):
            sync(self.root, check=True)
        self.assertTrue(stale.exists())
        sync(self.root)
        self.assertFalse(stale.exists())
        self.assertTrue(marker.exists())
        self.assertTrue((self.root / "plugins/shared/skills/summary/SKILL.md").exists())
        sync(self.root, check=True)
        self.catalog["plugins"][0]["platforms"] = ["claude", "codex"]
        self.save_catalog()
        sync(self.root)
        self.assertTrue(stale.exists())

    def test_removed_plugin_prunes_manifests_preserves_sources(self):
        self.add_mod()
        sync(self.root)
        self.catalog["plugins"] = self.catalog["plugins"][:1]
        self.save_catalog()
        with self.assertRaisesRegex(ValueError, "Stale generated files"):
            sync(self.root, check=True)
        sync(self.root)
        self.assertFalse((self.root / "plugins/fixture-mod/.claude-plugin/plugin.json").exists())
        self.assertTrue((self.root / "plugins/fixture-mod/hooks/register.js").exists())

    def test_invalid_input_does_not_mutate_outputs(self):
        sync(self.root)
        before = (self.root / ".claude-plugin/marketplace.json").read_bytes()
        self.catalog["plugins"][0]["platforms"] = []
        self.save_catalog()
        with self.assertRaises(ValueError):
            sync(self.root)
        self.assertEqual((self.root / ".claude-plugin/marketplace.json").read_bytes(), before)

    def test_output_directory_conflict_does_not_mutate_outputs(self):
        sync(self.root)
        before = (self.root / ".claude-plugin/marketplace.json").read_bytes()
        self.add_mod()
        (self.root / "plugins/fixture-mod/.claude-plugin/plugin.json").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "not a file"):
            sync(self.root)
        self.assertEqual((self.root / ".claude-plugin/marketplace.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
