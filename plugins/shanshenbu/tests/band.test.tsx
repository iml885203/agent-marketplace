import type { On } from 'claude-code'
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
