import { useState, useEffect, useCallback } from 'react'
import {
  startTeleoperate,
  startRecord,
  startTrain,
  startReplay,
  stopProcess,
  getLeaderServiceStatus,
  startLeaderService,
  stopLeaderService,
} from '../api/client'
import type { AppConfig, ProcessStatus, LeaderServiceStatus } from '../api/client'

interface ActionPanelProps {
  config: AppConfig | null
  status: ProcessStatus
  onAction: () => void
}

export function ActionPanel({ config, status, onAction }: ActionPanelProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const running = status.running

  const isRemote = config?.robot?.remote_leader === true
  const [leaderStatus, setLeaderStatus] = useState<LeaderServiceStatus>({ status: 'unknown' })
  const [leaderBusy, setLeaderBusy] = useState(false)

  const refreshLeader = useCallback(() => {
    if (!isRemote) return
    getLeaderServiceStatus().then(setLeaderStatus).catch(() => setLeaderStatus({ status: 'unknown' }))
  }, [isRemote])

  useEffect(() => {
    refreshLeader()
    if (!isRemote) return
    const id = setInterval(refreshLeader, 5000)
    return () => clearInterval(id)
  }, [isRemote, refreshLeader])

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
      onAction()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const handleLeaderToggle = async () => {
    setLeaderBusy(true)
    setError(null)
    try {
      if (leaderStatus.status === 'running') {
        if (running) { await stopProcess(); onAction() }
        await stopLeaderService()
      } else {
        const res = await startLeaderService()
        if (res.status === 'error') setError(res.message || 'Failed to start leader service')
      }
      refreshLeader()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLeaderBusy(false)
    }
  }

  if (running) {
    return (
      <div className="space-y-3">
        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
        <RunningCard status={status} busy={busy} onStop={() => run(stopProcess)} />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {isRemote && (
        <LeaderServiceCard
          status={leaderStatus}
          busy={leaderBusy}
          host={config?.robot?.remote_leader_host}
          port={config?.robot?.remote_leader_port}
          onToggle={handleLeaderToggle}
        />
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <TeleoperateCard
          busy={busy}
          leaderReady={!isRemote || leaderStatus.status === 'running'}
          onStart={() => run(() => startTeleoperate(true, config?.robot?.use_top_camera_only !== false))}
        />
        <RecordCard
          busy={busy}
          config={config}
          leaderReady={!isRemote || leaderStatus.status === 'running'}
          onStart={(p) => run(() => startRecord({ ...p, use_top_camera_only: config?.robot?.use_top_camera_only !== false }))}
        />
        <TrainCard busy={busy} onStart={(p) => run(() => startTrain(p))} />
        <ReplayCard busy={busy} onStart={(p) => run(() => startReplay(p))} />
      </div>
    </div>
  )
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-800/50 bg-red-950/40 px-4 py-3">
      <span className="mt-0.5 text-red-400">
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" /></svg>
      </span>
      <p className="flex-1 text-sm text-red-300">{message}</p>
      <button onClick={onDismiss} className="text-red-500 hover:text-red-300">&times;</button>
    </div>
  )
}

function LeaderServiceCard({ status, busy, host, port, onToggle }: {
  status: LeaderServiceStatus; busy: boolean; host?: string; port?: number; onToggle: () => void
}) {
  const isRunning = status.status === 'running'
  return (
    <div className={`flex items-center justify-between rounded-xl border px-4 py-3 transition ${isRunning ? 'border-green-800/40 bg-green-950/20' : 'border-gray-700/50 bg-gray-800/30'}`}>
      <div className="flex items-center gap-3">
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${isRunning ? 'bg-green-900/50 text-green-400' : 'bg-gray-700/50 text-gray-500'}`}>
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
          </svg>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-white">Leader Service</span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${isRunning ? 'bg-green-900/50 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isRunning ? 'bg-green-400' : 'bg-gray-500'}`} />
              {isRunning ? 'Running' : 'Stopped'}
            </span>
          </div>
          <span className="font-mono text-xs text-gray-500">{host}:{port}</span>
        </div>
      </div>
      <button
        onClick={onToggle}
        disabled={busy}
        className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${isRunning ? 'bg-red-600/80 text-white hover:bg-red-600' : 'bg-green-600/80 text-white hover:bg-green-600'}`}
      >
        {busy ? 'Working...' : isRunning ? 'Stop Leader' : 'Start Leader'}
      </button>
    </div>
  )
}

function RunningCard({ status, busy, onStop }: { status: ProcessStatus; busy: boolean; onStop: () => void }) {
  const labels: Record<string, string> = { teleoperate: 'Teleoperating', record: 'Recording', train: 'Training', replay: 'Replaying' }
  const colors: Record<string, string> = { teleoperate: 'border-emerald-700/40 bg-emerald-950/20', record: 'border-blue-700/40 bg-blue-950/20', train: 'border-violet-700/40 bg-violet-950/20', replay: 'border-amber-700/40 bg-amber-950/20' }
  return (
    <div className={`flex items-center justify-between rounded-xl border px-5 py-4 ${colors[status.mode] || 'border-gray-700 bg-gray-800/30'}`}>
      <div className="flex items-center gap-3">
        <span className="relative flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-40" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
        </span>
        <div>
          <span className="text-base font-semibold text-white">{labels[status.mode] || status.mode}</span>
          {status.pid && <span className="ml-2 font-mono text-xs text-gray-500">PID {status.pid}</span>}
        </div>
      </div>
      <button
        onClick={onStop}
        disabled={busy}
        className="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-red-900/30 transition hover:bg-red-500 disabled:opacity-50"
      >
        {busy ? 'Stopping...' : 'Stop'}
      </button>
    </div>
  )
}

function TeleoperateCard({ busy, leaderReady, onStart }: { busy: boolean; leaderReady: boolean; onStart: () => void }) {
  return (
    <ActionCard
      title="Teleoperate"
      description="Mirror leader arm movements to follower in real-time"
      color="emerald"
      icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" /></svg>}
    >
      <button
        onClick={onStart}
        disabled={busy || !leaderReady}
        title={!leaderReady ? 'Start leader service first' : ''}
        className="w-full rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-900/30 transition hover:bg-emerald-500 disabled:opacity-40 disabled:shadow-none"
      >
        Start Teleoperation
      </button>
      {!leaderReady && <p className="mt-1 text-center text-[11px] text-amber-400/80">Leader service must be running</p>}
    </ActionCard>
  )
}

function RecordCard({ busy, config, leaderReady, onStart }: {
  busy: boolean; config: AppConfig | null; leaderReady: boolean
  onStart: (p: { repo_id: string; num_episodes: number; single_task: string; push_to_hub: boolean }) => void
}) {
  const [repoId, setRepoId] = useState(config?.dataset?.repo_id || 'tensi/test_dataset')
  const [episodes, setEpisodes] = useState(config?.dataset?.num_episodes || 10)
  const [task, setTask] = useState(config?.dataset?.single_task || 'Grab the cube')

  return (
    <ActionCard
      title="Record"
      description="Record teleoperation episodes to a dataset"
      color="blue"
      icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.5" fill="currentColor" /></svg>}
    >
      <div className="space-y-2">
        <input type="text" value={repoId} onChange={(e) => setRepoId(e.target.value)} placeholder="Dataset repo ID" className="input-field" />
        <div className="grid grid-cols-2 gap-2">
          <input type="number" value={episodes} onChange={(e) => setEpisodes(Number(e.target.value))} className="input-field" title="Episodes" />
          <input type="text" value={task} onChange={(e) => setTask(e.target.value)} placeholder="Task" className="input-field" />
        </div>
        <button
          onClick={() => onStart({ repo_id: repoId, num_episodes: episodes, single_task: task, push_to_hub: false })}
          disabled={busy || !leaderReady}
          className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue-900/30 transition hover:bg-blue-500 disabled:opacity-40 disabled:shadow-none"
        >
          Start Recording
        </button>
      </div>
    </ActionCard>
  )
}

function TrainCard({ busy, onStart }: { busy: boolean; onStart: (p: { dataset_repo_id: string; output_dir: string; job_name: string }) => void }) {
  const [repoId, setRepoId] = useState('tensi/test_dataset')

  return (
    <ActionCard
      title="Train"
      description="Train an ACT policy on recorded data"
      color="violet"
      icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5" /></svg>}
    >
      <div className="space-y-2">
        <input type="text" value={repoId} onChange={(e) => setRepoId(e.target.value)} placeholder="Dataset repo ID" className="input-field" />
        <button
          onClick={() => onStart({ dataset_repo_id: repoId, output_dir: `outputs/train/act_${repoId.split('/').pop()}`, job_name: `act_${repoId.split('/').pop()}` })}
          disabled={busy}
          className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-violet-900/30 transition hover:bg-violet-500 disabled:opacity-40 disabled:shadow-none"
        >
          Start Training
        </button>
      </div>
    </ActionCard>
  )
}

function ReplayCard({ busy, onStart }: { busy: boolean; onStart: (p: { repo_id: string; episode: number }) => void }) {
  const [repoId, setRepoId] = useState('tensi/test_dataset')
  const [episode, setEpisode] = useState(0)

  return (
    <ActionCard
      title="Replay"
      description="Replay a recorded episode on the follower"
      color="amber"
      icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" /></svg>}
    >
      <div className="space-y-2">
        <div className="grid grid-cols-3 gap-2">
          <input type="text" value={repoId} onChange={(e) => setRepoId(e.target.value)} placeholder="repo_id" className="input-field col-span-2" />
          <input type="number" value={episode} onChange={(e) => setEpisode(Number(e.target.value))} className="input-field" title="Episode #" />
        </div>
        <button
          onClick={() => onStart({ repo_id: repoId, episode })}
          disabled={busy}
          className="w-full rounded-lg bg-amber-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-amber-900/30 transition hover:bg-amber-500 disabled:opacity-40 disabled:shadow-none"
        >
          Start Replay
        </button>
      </div>
    </ActionCard>
  )
}

function ActionCard({ title, description, color, icon, children }: {
  title: string; description: string; color: string; icon: React.ReactNode; children: React.ReactNode
}) {
  const borderColors: Record<string, string> = {
    emerald: 'border-emerald-800/30', blue: 'border-blue-800/30', violet: 'border-violet-800/30', amber: 'border-amber-800/30',
  }
  const iconBg: Record<string, string> = {
    emerald: 'bg-emerald-900/40 text-emerald-400', blue: 'bg-blue-900/40 text-blue-400', violet: 'bg-violet-900/40 text-violet-400', amber: 'bg-amber-900/40 text-amber-400',
  }
  return (
    <div className={`rounded-xl border bg-gray-800/30 p-4 ${borderColors[color] || 'border-gray-700/50'}`}>
      <div className="mb-3 flex items-center gap-2.5">
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${iconBg[color] || 'bg-gray-700 text-gray-400'}`}>
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          <p className="text-[11px] text-gray-500">{description}</p>
        </div>
      </div>
      {children}
    </div>
  )
}
