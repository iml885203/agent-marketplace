# Agent Marketplace

個人維護的 Claude Code / Codex skills-only marketplace。共用同一份 skill；各平台保留獨立 manifest。示範 `text-summary` 只整理使用者提供的文字，沒有 MCP、hooks、外部服務或額外權限。

## 安裝

Claude Code（在 session 內）：

```text
/plugin marketplace add iml885203/agent-marketplace
/plugin install text-summary@agent-marketplace
/text-summary:summarize 請摘要以下文字：…
```

Codex CLI：

```sh
codex plugin marketplace add iml885203/agent-marketplace --ref main
codex plugin add text-summary@agent-marketplace
```

重開 session，使用 `$summarize` 並提供文字。Codex app 可從 Plugins 瀏覽已設定 marketplace；介面與 repo source 可用性依版本而異。

也可以 clone 後以本地路徑取代 `iml885203/agent-marketplace`。上面的安裝命令會變更執行者自己的設定；本 repo 的生成與驗證腳本不會安裝插件。

## 結構與新增插件

- `catalog.json`：插件名稱、版本與描述的單一來源。
- `plugins/<name>/skills/<skill>/SKILL.md`：Claude / Codex 共用指示；支援的 scripts/resources 放在相同插件目錄內，不引用 repo 外部檔案。
- `scripts/sync.py`：生成兩套 marketplace 與 plugin manifests。
- `.claude-plugin/marketplace.json` / `.agents/plugins/marketplace.json`：兩平台 catalog。

新增 `catalog.json` entry，建立對應 skill（frontmatter 必須含 `name` 與 `description`），提高有變更插件的 semantic version，再執行：

```sh
python3 scripts/sync.py
python3 scripts/sync.py --check
python3 scripts/validate.py
claude plugin validate .
claude plugin validate ./plugins/text-summary
```

只需 Python 3.9+ 標準函式庫。提交生成檔；CI 檢查相同內容。驗證器檢查本 skeleton 使用的 schema 子集合與路徑，不聲稱完整驗證平台所有功能。實際 agent 輸出仍需人工 smoke test。

## 支援範圍

2026-10-02 核對官方格式；本機 CLI 為 Codex 0.159.2 / Claude Code 2.1.251。使用 Codex 仍支援的 `.codex-plugin/plugin.json` compatibility layout；新版 portable root `plugin.json` 是不同格式，不直接重新命名。本 skeleton 僅共享 skills，未宣稱 hooks、MCP、apps 或平台功能全部通用。未對使用者全域設定進行安裝測試。

官方參考：[OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)、[Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)。結構靈感：[dashed/claude-marketplace](https://github.com/dashed/claude-marketplace) 的生成一致性策略與 [duyet/codex-claude-plugins](https://github.com/duyet/codex-claude-plugins) 的雙平台結構；沒有複製或執行其 scripts。

僅含本次新寫的通用內容，不含個人記憶、聊天、公司程式或憑證。MIT license。
