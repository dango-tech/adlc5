import { expect, mock, test } from 'claude-code/testing'

const BAND = {
  plugin: 'adlc5', component: 'AbovePrompt', requestId: 'pulse',
  viewport: { columns: 120, rows: 40 },
  props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 120, scroll: { offset: 0, bodyRows: 12 }, view: {} },
} as const

test('refresh completes before rendering; card actions work on desktop and terminal', async ($, on) => {
  const calls: string[][] = []
  const commands: string[] = []
  let measured = true
  let sessionCwd = '/fixture'
  mock.env(on, {})
  on('session.cwd', () => ({ value: sessionCwd }))
  on('session.start', () => ({ cwd: '/fixture' }))
  on('turn.complete', () => ({ text: '' }))
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['Other mod remains'] }))
  on('ui.toast', () => ({ value: undefined }))
  on('command.run', ($, e) => { commands.push(e.command); return { text: 'started' } })
  on('process.run', async ($, e) => {
    calls.push([...e.argv])
    return { value: { exitCode: 0, stderr: '', stdout: JSON.stringify({ features: [{
      id: 'fixture-feature', lifecycle: { stage: 'implement', step: 'implement-2-verify' },
      evaluation: measured ? { savings_pct: 40, success_rate_pct: 100, runs: 2, escaped_defects: 0, rework: 0 } : undefined,
    }] }) } }
  })
  await $.session.start({ surface: 'desktop', isInteractive: true, cwd: '/fixture' })
  expect(calls.length).toBe(1)
  expect(calls[0][0]).toBe('python3')
  expect(calls[0][1]).toMatch(/\/scripts\/adlc5$/)
  for (const surface of ['desktop', 'terminal'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect(await ui.find({ type: 'Text', text: 'fixture-feature · implement' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /40.0% observed/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'Other mod remains' })).toBeDefined()
    await ui.press({ key: 'details' })
    expect(await ui.find({ type: 'Text', text: /defects 0 · rework 0/ })).toBeDefined()
    await ui.press({ key: 'details' })
    expect(await ui.find({ type: 'Text', text: /defects 0 · rework 0/ })).toBeUndefined()
    await ui.press({ key: 'review' })
    await ui.press({ key: 'audit' })
    await ui.press({ key: 'board' })
    expect(calls[calls.length - 1]).toContain('--open')
    expect(calls[calls.length - 1]).toContain('fixture-feature')
    await ui.unmount()
  }
  expect(commands).toEqual(['adlc5:craftsmanship-code-review', 'adlc5:qa', 'adlc5:craftsmanship-code-review', 'adlc5:qa'])
  measured = false
  sessionCwd = '/fixture/.claude/worktrees/moved'
  await $.turn.complete({ turnId: 'refresh', answer: 'done', durationMs: 1, isAborted: false, usage: null })
  expect(calls[calls.length - 1]).toContain('/fixture/.claude/worktrees/moved')
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /Projected savings Not measured · outcome success Not measured/ })).toBeDefined()
  await ui.unmount()
})


test('archive selection and actions retain the archive ID when an active label also exists', async ($, on) => {
  const archiveId = 'fixture-feature-20261017'
  const calls: string[][] = []
  const commands: { command: string; args?: string }[] = []
  mock.env(on, { ADLC5_FEATURE: archiveId })
  on('session.cwd', () => ({ value: '/fixture' }))
  on('session.start', () => ({ cwd: '/fixture' }))
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['Other mod remains'] }))
  on('ui.toast', () => ({ value: undefined }))
  on('command.run', ($, e) => { commands.push({ command: e.command, args: e.args }); return { text: 'started' } })
  on('process.run', ($, e) => {
    calls.push([...e.argv])
    return { value: { exitCode: 0, stderr: '', stdout: JSON.stringify({ features: [
      { id: 'fixture-feature', archive_id: null, lifecycle: { stage: 'specify' } },
      { id: 'fixture-feature', archive_id: archiveId, lifecycle: { stage: 'implement', step: 'completed' } },
    ] }) } }
  })
  await $.session.start({ surface: 'desktop', isInteractive: true, cwd: '/fixture' })
  expect(calls[0]).toContain(archiveId)
  for (const surface of ['desktop', 'terminal'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect(await ui.find({ type: 'Text', text: 'fixture-feature · implement' })).toBeDefined()
    await ui.press({ key: 'details' })
    expect(await ui.find({ type: 'Text', text: /^completed · review/ })).toBeDefined()
    await ui.press({ key: 'details' })
    await ui.press({ key: 'review' })
    await ui.press({ key: 'audit' })
    await ui.press({ key: 'board' })
    expect(calls[calls.length - 1]).toContain(archiveId)
    expect(commands[commands.length - 2]).toEqual({ command: 'adlc5:craftsmanship-code-review', args: archiveId })
    expect(commands[commands.length - 1]).toEqual({ command: 'adlc5:qa', args: archiveId })
    await ui.unmount()
  }
})
