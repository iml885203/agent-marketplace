import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Mood } from '../types'
import { COLUMNS, FRAMES, ROWS } from './frames'

const mood = atom({ plugin: 'shanshenbu', key: 'mood' } as const, 'idle')
const isHidden = atom({ plugin: 'shanshenbu', key: 'isHidden' } as const, false)

const FRAME_MS = 125
const FAILED_MS = 3000
const HIDDEN_KEY = 'isHidden'

const LABELS: Record<Mood, string> = {
  idle: '閃身步 · 待命',
  working: '閃身步 · 工作中',
  review: '閃身步 · 檢查中',
  kick: '浪子踢球 · 改檔中',
  waiting: '狗熊哆嗦毛 · 等你回覆',
  failed: '閃身步 · 出錯了',
  jump: '閃身步 · 完成！',
  wave: '閃身步 · 嗨',
}

// How many loops a one-shot mood plays before falling back to the base mood
const ONE_SHOT_LOOPS: Partial<Record<Mood, number>> = { wave: 2, jump: 1 }

const READ_TOOLS = new Set(['Read', 'Grep', 'Glob', 'LS', 'WebFetch', 'WebSearch'])
const EDIT_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit'])

let current: Mood = 'idle'
let frame = 0
let isTurnRunning = false
let isKickingRight = true
let bandId: string | undefined
let failedUntil = 0

function framesOf(m: Mood): string[] {
  if (m === 'kick') {
    return isKickingRight ? FRAMES.runRight : FRAMES.runLeft
  }

  return FRAMES[m]
}

function cellsNow(): string {
  const frames = framesOf(current)

  return frames[frame % frames.length] ?? ''
}

function baseMood(): Mood {
  return isTurnRunning ? 'working' : 'idle'
}

async function setMood($: EngineInterface, next: Mood) {
  if (next === current) {
    return
  }
  current = next
  frame = 0
  await update($, mood, () => next)
}

async function tick($: EngineInterface) {
  frame += 1
  const frames = framesOf(current)
  const loops = ONE_SHOT_LOOPS[current]

  if (loops !== undefined && frame >= frames.length * loops) {
    await setMood($, baseMood())
  } else if (current === 'failed' && (await $.clock.now()) >= failedUntil) {
    await setMood($, baseMood())
  }

  if (bandId === undefined) {
    return
  }
  await $.ui.blit({ requestId: bandId, key: 'pet', cells: cellsNow() })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'shanshenbu',
      description: '顯示或隱藏閃身步寵物',
    })
    const hidden = (await $.store.get(HIDDEN_KEY)) === true
    await update($, isHidden, () => hidden)
    await setMood($, 'wave')
    $.clock.every(FRAME_MS, () => void tick($))

    return next(e)
  })

  on('command.run', { command: 'shanshenbu' }, async $ => {
    const hidden = !(await read($, isHidden))
    await update($, isHidden, () => hidden)
    await $.store.set(HIDDEN_KEY, hidden)

    return { text: hidden ? '閃身步休息了。' : '閃身步回來了。' }
  })

  on('turn.start', async ($, e, next) => {
    isTurnRunning = true
    await setMood($, 'working')

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    isTurnRunning = false
    if (e.reason === 'answer') {
      await setMood($, 'jump')
    } else if (e.reason === 'aborted') {
      await setMood($, 'idle')
    } else {
      failedUntil = (await $.clock.now()) + FAILED_MS
      await setMood($, 'failed')
    }

    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const tool = String(e.tool)
    if (tool === 'AskUserQuestion') {
      await setMood($, 'waiting')
    } else if (EDIT_TOOLS.has(tool)) {
      isKickingRight = !isKickingRight
      await setMood($, 'kick')
    } else if (READ_TOOLS.has(tool)) {
      await setMood($, 'review')
    } else {
      await setMood($, 'working')
    }

    const result = await next(e)
    await setMood($, baseMood())

    return result
  })

  on('classic.PermissionRequest', async ($, e, next) => {
    await setMood($, 'waiting')

    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.surface !== 'terminal') {
      return next(e)
    }
    const hidden = await read($, isHidden)
    const shownMood = await read($, mood)
    if (hidden || e.props.hasSurvey || e.props.maxRows < ROWS) {
      bandId = undefined

      return next(e)
    }
    bandId = e.requestId
    const { Box, Raster, Text } = $.ui.resolve(e)

    return (
      <Box flexDirection="row">
        <Raster key="pet" columns={COLUMNS} rows={ROWS} cells={cellsNow()} />
        <Box flexDirection="column" justifyContent="flex-end" paddingLeft={1}>
          <Text dimColor>{LABELS[shownMood]}</Text>
        </Box>
      </Box>
    )
  })
}
