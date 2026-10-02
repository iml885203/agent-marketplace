# Agent Marketplace

A personally maintained marketplace of skills for Claude Code and Codex, plus Claude Code mods. Both platforms share the same skill instructions and use separate manifests. The `text-summary` example summarizes text supplied by the user and includes no MCP servers, hooks, external services, or additional permissions.

| Plugin | Kind | Platforms |
| --- | --- | --- |
| `text-summary` | skill | Claude Code, Codex |
| [`shanshenbu`](plugins/shanshenbu) | mod (a 閃身步 pet above the prompt) | Claude Code v2.1.287+ |

## Installation

In a Claude Code session:

```text
/plugin marketplace add iml885203/agent-marketplace
/plugin install text-summary@agent-marketplace
/text-summary:summarize Summarize the following text: …
/plugin install shanshenbu@agent-marketplace
```

With the Codex CLI:

```sh
codex plugin marketplace add iml885203/agent-marketplace --ref main
codex plugin add text-summary@agent-marketplace
```

Start a new session, invoke `$summarize`, and provide the text to summarize. In the Codex app, browse configured marketplaces through Plugins. The interface and availability of repository sources vary by version.

You can also clone this repository and replace `iml885203/agent-marketplace` with its local path. The installation commands above update the settings of the person running them. This repository's generation and validation scripts do not install plugins.

## Structure and adding plugins

- `catalog.json`: the single source of truth for plugin names, versions, and descriptions.
- `plugins/<name>/skills/<skill>/SKILL.md`: shared Claude Code and Codex instructions. Keep supporting scripts and resources inside the same plugin directory; do not reference files outside the repository.
- `scripts/sync.py`: generates both platforms' marketplace files and plugin manifests.
- `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`: the platform-specific catalogs.
- `plugins/<name>/hooks/`: a Claude Code mod's hooks module, for a catalog entry with `"kind": "mod"`. Mods are listed in the Claude catalog only. When `types/index.d.ts` exists, its path is included in the Claude manifest; this file is required by Claude when a mod uses `$.state` or extends the mods API. An entry may set `license` when it is not MIT.

Add an entry to `catalog.json` and select its platforms:

- Omit `platforms` on a skill entry to keep the default of `["claude", "codex"]`.
- Set `"platforms": ["claude"]` or `"platforms": ["codex"]` for a platform-specific skill.
- Set `"kind": "mod"` for a Claude Mod. Existing mod entries default to `["claude"]`; an explicit platform list must also be `["claude"]`.
- Only `claude` and `codex` are accepted. Empty or duplicate platform lists are rejected. Catalog controls such as `platforms` and `kind` are not copied into plugin manifests.

Create the corresponding skill with `name` and `description` in its frontmatter. Claude-only entries can instead contain `hooks/hooks.json` without any skills. A Mod declares `"modules": ["./register.tsx"]` in that file, with one JavaScript or TypeScript module exporting `register`. Module paths resolve from the hooks configuration directory and must remain inside the plugin directory. The supported extensions are `.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.mts`, `.cts`, and `.tsx`.

The tooling also accepts Claude-only command settings hooks under `hooks`, using event matcher groups with `type`, `command`, and optional positive `timeout` fields. Other settings hook types and options are outside this validator's supported subset. Hooks or Mods cannot be advertised to Codex by this tooling, including when the same plugin also contains skills.

Increment the semantic version of any changed plugin, then run:

```sh
python3 scripts/sync.py
python3 scripts/sync.py --check
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
node --test tests/shanshenbu-turn-complete.test.mjs
claude plugin validate .
claude plugin validate ./plugins/text-summary
claude plugin validate ./plugins/shanshenbu
claude plugin test ./plugins/shanshenbu
```

The Python scripts require only Python 3.9+ and its standard library. Commit the generated files; CI checks their consistency. The generator owns the two marketplace files and `plugins/*/.claude-plugin/plugin.json` / `plugins/*/.codex-plugin/plugin.json`. When a plugin changes platforms or leaves the catalog, `sync.py` removes its obsolete generated manifests while preserving source files and directories. Do not keep manually authored manifests at these reserved paths. `--check` reports missing, changed, or obsolete generated files without writing anything. Inputs and output paths are checked before generation or cleanup.

The validator checks the supported catalog and hooks schema subset, module existence and extensions, containment, symlinks, skill frontmatter, and generated metadata consistency. It does not parse or execute hook modules, follow their imports, verify their `register` export, type-check state declarations, validate event names, or parse shell commands and their referenced paths. Use Claude's native validation and tests for those platform checks. The Python unit tests use temporary fixtures and never execute a Mod. The Node.js 22+ regression tests execute the actual `shanshenbu` completion callback body with state and clock stubs, using only built-in Node modules; they do not load Claude, render its UI, or establish full Mod runtime compatibility. CI runs both suites. The native band regression test still requires a compatible Claude version. Actual agent output and UI behavior still need a manual smoke test.

## Support scope

The official formats were checked on October 2, 2026, with Codex CLI 0.159.2 and Claude Code 2.1.251 installed locally. This repository uses the supported Codex `.codex-plugin/plugin.json` compatibility layout. The newer portable format uses a root-level `plugin.json` with a different schema; migration requires more than renaming the file. Skills are shared across both platforms; mods are Claude Code only. The repository does not claim that hooks, MCP servers, apps, or all platform features are interchangeable. Installation was not tested against the user's global settings. Mods require Claude Code v2.1.287 or newer; the local v2.1.251 validator cannot establish compatibility or execute the Mod test suite. The Python checks and CI validate packaging structure only, not Mod runtime behavior.

Official references: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), and [Claude Mods reference](https://code.claude.com/docs/en/plugins/mods/reference). The structure draws inspiration from the generation consistency strategy in [dashed/claude-marketplace](https://github.com/dashed/claude-marketplace) and the dual-platform layout in [duyet/codex-claude-plugins](https://github.com/duyet/codex-claude-plugins). Their scripts were neither copied nor executed.

This repository contains only newly written, general-purpose content. It includes no personal memories, chats, company code, or credentials. Licensed under MIT, except the `shanshenbu` sprites, which are for non-commercial use only (see its [LICENSE](plugins/shanshenbu/LICENSE)).
