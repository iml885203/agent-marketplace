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
- `plugins/<name>/hooks/`: a Claude Code mod's hooks module, for a catalog entry with `"kind": "mod"`. Mods are listed in the Claude catalog only, and their manifest names `types/index.d.ts` as the state contract. An entry may set `license` when it is not MIT.

Add an entry to `catalog.json`, create the corresponding skill with `name` and `description` in its frontmatter, and increment the semantic version of any changed plugin. Then run:

```sh
python3 scripts/sync.py
python3 scripts/sync.py --check
python3 scripts/validate.py
claude plugin validate .
claude plugin validate ./plugins/text-summary
claude plugin validate ./plugins/shanshenbu
claude plugin test ./plugins/shanshenbu
```

The Python scripts require only Python 3.9+ and its standard library. Commit the generated files; CI checks their consistency. The validator checks the schema subset and paths used by this skeleton, rather than every feature supported by either platform. Actual agent output still needs a manual smoke test.

## Support scope

The official formats were checked on October 2, 2026, with Codex CLI 0.159.2 and Claude Code 2.1.251 installed locally. This repository uses the supported Codex `.codex-plugin/plugin.json` compatibility layout. The newer portable format uses a root-level `plugin.json` with a different schema; migration requires more than renaming the file. Skills are shared across both platforms; mods are Claude Code only. The repository does not claim that hooks, MCP servers, apps, or all platform features are interchangeable. Installation was not tested against the user's global settings.

Official references: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins) and [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces). The structure draws inspiration from the generation consistency strategy in [dashed/claude-marketplace](https://github.com/dashed/claude-marketplace) and the dual-platform layout in [duyet/codex-claude-plugins](https://github.com/duyet/codex-claude-plugins). Their scripts were neither copied nor executed.

This repository contains only newly written, general-purpose content. It includes no personal memories, chats, company code, or credentials. Licensed under MIT, except the `shanshenbu` sprites, which are for non-commercial use only (see its [LICENSE](plugins/shanshenbu/LICENSE)).
