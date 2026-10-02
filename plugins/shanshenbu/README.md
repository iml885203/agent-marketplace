# shanshenbu（閃身步）

A Claude Code mod: a chibi 閃身步 dancer above the prompt that moves with what Claude is doing.

| Claude is | The pet does |
| --- | --- |
| working | 閃身步 side-steps |
| reading or searching | checks, hand on chin |
| editing a file | 浪子踢球, alternating left and right |
| waiting for you (permission prompt, AskUserQuestion) | 狗熊哆嗦毛 |
| done with a turn | jumps once |
| failing (API error, refusal) | slumps for three seconds |
| starting a session | waves |

It draws a 21×14-cell half-block `Raster`, so it works in any truecolor terminal, no kitty graphics needed. The desktop app, the VS Code chat panel and `claude -p` show nothing.

## Install

Needs Claude Code v2.1.287 or newer.

```text
/plugin marketplace add iml885203/agent-marketplace
/plugin install shanshenbu@agent-marketplace
/reload-plugins
```

`/shanshenbu` hides or shows the pet; the choice is kept across sessions. The band also collapses with ctrl+x ctrl+a.

## Sprites

`spritesheet.webp` is the 閃身步 V2 Codex pet ([legeling/awesome-codex-pet#230](https://github.com/legeling/awesome-codex-pet/pull/230)). `hooks/frames.ts` is generated from it:

```bash
python3 slice.py 14 hooks/frames.ts spritesheet.webp [preview.png]   # needs Pillow
```

The first argument is the height in terminal rows; the width follows.

## Develop

```bash
claude plugin validate plugins/shanshenbu
claude plugin test plugins/shanshenbu
claude --plugin-dir plugins/shanshenbu
```

## License

The code is MIT. The sprites (`spritesheet.webp`, and `hooks/frames.ts` generated from it) are AI-generated and for **non-commercial use only**. See [LICENSE](LICENSE).
