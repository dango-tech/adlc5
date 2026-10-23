import type { EngineInterface, Register } from 'claude-code'

type Feature = {
  id: string
  archive_id?: string | null
  lifecycle?: { stage?: string; step?: string }
  evidence?: {
    checks?: { status?: string; recorded_passed?: number; required?: number }
    review?: { status?: string }
    pr_ready?: { status?: string }
  }
  usage?: { known_cost_usd?: number | null; status?: string }
  evaluation?: { success_rate_pct?: number | null; successful?: number; runs?: number; savings_pct?: number | null; reason?: string; escaped_defects?: number | null; rework?: number | null }
  next_action?: { label?: string }
}

type Snapshot = { status?: string; generated_at?: string; features?: Feature[] }

let cwd = ''
let pluginRoot = ''
let featureFilter = ''
let snapshot: Snapshot | undefined
let showDetails = false
let loading = false
let snapshotProblem = 'waiting for refresh'

async function refresh($: EngineInterface) {
  loading = true
  try {
    snapshotProblem = 'workspace lookup failed'
    cwd = cwd || await $.session.cwd()
    snapshotProblem = 'plugin runtime unavailable'
    pluginRoot = $.plugin.root
    snapshotProblem = 'feature selection failed'
    featureFilter = featureFilter || await $.env.get('ADLC5_FEATURE') || ''
    if (!cwd || !pluginRoot) throw new Error('Pulse runtime is unavailable')
    const args = ['python3', `${pluginRoot}/scripts/adlc5`, 'pulse', 'snapshot', '--workspace', cwd]
    if (featureFilter) args.push('--feature', featureFilter)
    snapshotProblem = 'snapshot process could not start'
    const result = await $.process.run(args)
    snapshotProblem = `snapshot process exited ${result.exitCode}`
    if (result.exitCode !== 0 || result.stdout.length > 1024 * 1024) throw new Error('Pulse snapshot failed')
    snapshotProblem = 'snapshot output invalid'
    const value = JSON.parse(result.stdout)
    if (!value || typeof value !== 'object' || !Array.isArray(value.features)) throw new Error('Invalid Pulse snapshot')
    snapshot = value as Snapshot
    snapshotProblem = ''
  } catch {
    snapshot = undefined
  } finally {
    loading = false
  }
}

function selected(): Feature | undefined {
  const rows = snapshot?.features ?? []
  if (featureFilter) return rows.find(item => item.id === featureFilter || item.archive_id === featureFilter)
  return rows.length === 1 ? rows[0] : undefined
}

const statusColor = (status: string | undefined) =>
  status === 'pass' || status === 'current' ? '#34d399' :
  status === 'fail' || status === 'stale' ? '#ff8a80' : '#a6a8b1'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    await refresh($)
    $.ui.invalidate('ui.render')
    return result
  }).catch(($, e, next) => next(e))

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    await refresh($)
    $.ui.invalidate('ui.render')
    return result
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const below = await next(e).catch(() => undefined)
    const { Box, Text, Button } = $.ui.resolve(e)
    const feature = selected()
    const featureId = feature?.archive_id ?? feature?.id
    const features = snapshot?.features ?? []
    const line = feature
      ? `${feature.id} · ${feature.lifecycle?.stage ?? 'stage unknown'}`
      : featureFilter
        ? `Feature ${featureFilter} not found in this snapshot`
      : features.length > 1
        ? `${features.length} features · set ADLC5_FEATURE to pin one`
        : features.length === 0
          ? loading ? 'Reading workspace snapshot…' : snapshot ? 'No feature data in this workspace' : `Snapshot unavailable · ${snapshotProblem}`
          : `Snapshot unavailable · ${snapshotProblem}`
    const knownCost = feature?.usage?.known_cost_usd
    const metrics = feature?.evaluation
    const savings = typeof metrics?.savings_pct === 'number' ? `${metrics.savings_pct.toFixed(1)}% observed` : 'Not measured'
    const quality = typeof metrics?.success_rate_pct === 'number' ? `${metrics.success_rate_pct.toFixed(1)}% (n=${metrics.runs})` : 'Not measured'
    const detail = feature
      ? `${feature.lifecycle?.step ?? 'step unknown'} · review ${feature.evidence?.review?.status ?? 'unavailable'} · usage ${feature.usage?.status ?? 'unavailable'} · ${snapshot?.generated_at ?? 'capture time unavailable'} · next: ${feature.next_action?.label ?? 'inspect current step'} · defects ${metrics?.escaped_defects ?? 'Not measured'} · rework ${metrics?.rework ?? 'Not measured'} · ${metrics?.reason ?? 'Accuracy is not measured'}`
      : featureFilter
        ? 'Change ADLC5_FEATURE to an active feature label or archive ID, then start or finish a turn.'
        : 'Set ADLC5_FEATURE to pin one feature, then start or finish a turn to refresh Pulse.'
    const openBoard = async () => {
      if (!cwd || !pluginRoot) return
      const args = ['python3', `${pluginRoot}/scripts/adlc5`, 'pulse', 'board', '--workspace', cwd, '--host', 'claude', '--open']
      if (featureId) args.push('--feature', featureId)
      const result = await $.process.run(args).catch(() => undefined)
      $.ui.toast(result?.exitCode === 0 ? 'ADLC5 Pulse board opened' : 'ADLC5 Pulse board could not be opened')
    }
    const mine = (
      <Box flexDirection="column" width={e.props.bodyColumns}>
        <Box flexDirection="row" alignItems="center" gap={2}>
          <Text color="#34d399" bold>&gt; | ADLC5 Pulse</Text>
          <Text wrap="truncate-middle">{line}</Text>
          {feature && <Text color={statusColor(feature.evidence?.checks?.status)}>checks {feature.evidence?.checks?.status ?? 'unavailable'}</Text>}
          {feature && <Text color={statusColor(feature.evidence?.pr_ready?.status)}>gate {feature.evidence?.pr_ready?.status ?? 'unavailable'}</Text>}
          {typeof knownCost === 'number' && Number.isFinite(knownCost) && <Text>${knownCost.toFixed(2)} known</Text>}
          <Box flexGrow={1} />
          <Button key="review" plain onPress={() => $.command.run({ command: 'adlc5:craftsmanship-code-review', args: featureId ?? '' }).catch(error => $.ui.toast(`Pulse Review failed: ${String(error).slice(0, 160)}`))}>Review</Button>
          <Button key="audit" plain onPress={() => $.command.run({ command: 'adlc5:qa', args: featureId ?? '' }).catch(error => $.ui.toast(`Pulse Audit failed: ${String(error).slice(0, 160)}`))}>Audit</Button>
          <Button key="board" plain onPress={openBoard}>Board</Button>
          <Button key="details" plain onPress={() => { showDetails = !showDetails; $.ui.invalidate('ui.render') }}>{showDetails ? 'Hide' : 'Details'}</Button>
        </Box>
        {feature && <Text dimColor wrap="wrap">Projected savings {savings} · outcome success {quality}</Text>}
        {showDetails && <Text dimColor wrap="wrap">{detail}</Text>}
      </Box>
    )
    return below ? <Box flexDirection="column">{mine}{below}</Box> : mine
  }).catch(($, e, next) => next(e))
}
