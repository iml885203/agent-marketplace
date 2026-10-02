import type { On, TurnCompleteInput } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

const BAND = {
  plugin: 'shanshenbu',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 30,
    bodyColumns: 120,
    scroll: { offset: 0, bodyRows: 29 },
    view: {},
  },
} as const

// Stands in for the engine beneath the mod
function engine(on: On) {
  mock.clock(on)
  mock.store(on)
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)

    return <Box />
  })
}

async function start($: Engine) {
  await $.session.start({ cwd: '/tmp', surface: 'terminal', isInteractive: true })
}

test('draws the pet and waves on session start', async ($, on) => {
  engine(on)
  await start($)
  const band = await $.ui.mount(BAND)

  expect((await band.find({ key: 'pet' }))?.type).toBe('Raster')
  expect((await band.find({ type: 'Text' }))?.text).toBe('閃身步 · 嗨')
})

test('kicks while Claude edits a file, then settles', async ($, on) => {
  engine(on)
  let during: string | undefined
  const label = async () => (await band.find({ type: 'Text' }))?.text
  on('tool.call', async () => {
    during = await label()

    return { result: 'written' }
  })
  await start($)
  const band = await $.ui.mount(BAND)

  await $.tool.call({ tool: 'Write', file_path: '/tmp/a', content: '' })

  expect(during).toBe('浪子踢球 · 改檔中')
  expect(await label()).toBe('閃身步 · 待命')
})

test('/shanshenbu hides the band', async ($, on) => {
  engine(on)
  await start($)
  await $.command.run({
    command: 'shanshenbu',
    args: '',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 120 },
  })
  const band = await $.ui.mount(BAND)

  expect(await band.find({ key: 'pet' })).toBeUndefined()
})

test('subagent completions preserve the main working mood until the main turn ends', async ($, on) => {
  engine(on)
  on('turn.start', ($, e) => ({ turnId: e.turnId }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('tool.call', () => ({ result: 'read' }))
  await start($)
  const band = await $.ui.mount(BAND)
  const label = async () => (await band.find({ type: 'Text' }))?.text
  await $.turn.start({ text: 'Fixture main turn', turnId: 'main-turn' })

  const child = { agentId: 'child-agent', turnId: 'child-turn', answer: 'Child result', durationMs: 1 }
  const completions: TurnCompleteInput[] = [
    { ...child, reason: 'answer', isAborted: false },
    { ...child, reason: 'aborted', isAborted: true },
    { ...child, reason: 'error', isAborted: false },
    { ...child, reason: 'refusal', isAborted: false, refusal: { category: null, explanation: null } },
  ]
  for (const completion of completions) {
    expect((await $.turn.complete(completion)).text).toBe('Child result')
    expect(await label()).toBe('閃身步 · 工作中')
  }

  // A subsequent tool settling must still return to the main working mood.
  await $.tool.call({ tool: 'Read', file_path: '/tmp/fixture' })
  expect(await label()).toBe('閃身步 · 工作中')
  await $.turn.complete({ turnId: 'main-turn', answer: 'Main result', durationMs: 2, isAborted: false, reason: 'answer' })
  expect(await label()).toBe('閃身步 · 完成！')
})
