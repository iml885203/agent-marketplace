// Runs the actual completion callback body with state/clock stubs, not Claude.
// No transpiler, model, UI, or third-party packages are needed.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../plugins/shanshenbu/hooks/register.tsx', import.meta.url), 'utf8')
const callback = source.match(/on\('turn\.complete', async \(\$, e, next\) => \{([\s\S]*?)\n  \}\)/)?.[1]
assert.ok(callback, 'Locate the actual turn.complete handler; update this harness if its declaration changes')

function harness() {
  // This callback contains ordinary JS despite living in a TSX module. Execute
  // its exact source in an isolated lexical scope; do not simulate its logic.
  return new Function(`
    let isTurnRunning = true
    let current = 'working'
    let failedUntil = 17
    const FAILED_MS = 3000
    const changes = []
    async function setMood($, mood) { current = mood; changes.push(mood) }
    return {
      complete: async ($, e, next) => { ${callback} },
      state: () => ({ isTurnRunning, current, failedUntil, changes: [...changes] })
    }
  `)()
}

function event(reason, agentId) {
  return { reason, turnId: agentId === undefined ? 'main-turn' : 'child-turn',
    ...(agentId === undefined ? {} : { agentId }), answer: 'result', durationMs: 1,
    isAborted: reason === 'aborted',
    ...(reason === 'refusal' ? { refusal: { category: null, explanation: null } } : {}) }
}

const clock = { clock: { now: async () => 100 } }

for (const reason of ['answer', 'aborted', 'refusal', 'error']) {
  test(`child ${reason} preserves all pet state and forwards the event exactly once`, async () => {
    const pet = harness()
    const before = pet.state()
    const input = event(reason, 'child-agent')
    const forwarded = []
    const result = { text: 'downstream result' }
    assert.equal(await pet.complete(clock, input, async e => { forwarded.push(e); return result }), result)
    assert.deepEqual(pet.state(), before)
    assert.equal(forwarded.length, 1)
    assert.equal(forwarded[0], input)
  })
}

for (const [reason, mood] of [['answer', 'jump'], ['aborted', 'idle'], ['refusal', 'failed'], ['error', 'failed']]) {
  test(`main ${reason} still ends the turn with ${mood}`, async () => {
    const pet = harness()
    const input = event(reason)
    let nextCalls = 0
    await pet.complete(clock, input, async e => { assert.equal(e, input); nextCalls += 1 })
    assert.equal(nextCalls, 1)
    assert.equal(pet.state().isTurnRunning, false)
    assert.equal(pet.state().current, mood)
    assert.deepEqual(pet.state().changes, [mood])
    assert.equal(pet.state().failedUntil, mood === 'failed' ? 3100 : 17)
  })
}

test('a child completion does not prevent the later main completion', async () => {
  const pet = harness()
  await pet.complete(clock, event('answer', 'child-agent'), async () => {})
  assert.equal(pet.state().isTurnRunning, true)
  await pet.complete(clock, event('answer'), async () => {})
  assert.equal(pet.state().isTurnRunning, false)
  assert.deepEqual(pet.state().changes, ['jump'])
})
