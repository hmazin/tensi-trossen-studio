import { useCallback, useEffect, useState } from 'react'
import type { AppConfig, ProcessStatus, LeaderServiceStatus } from '../api/client'
import { getLeaderServiceStatus } from '../api/client'

interface StatusBarProps {
  config: AppConfig | null
  status: ProcessStatus
  onSettingsClick: () => void
}

export function StatusBar({ config, status, onSettingsClick }: StatusBarProps) {
  const isRemote = config?.robot?.remote_leader === true
  const [leaderStatus, setLeaderStatus] = useState<LeaderServiceStatus>({ status: 'unknown' })

  const refreshLeader = useCallback(() => {
    if (!isRemote) return
    getLeaderServiceStatus()
      .then(setLeaderStatus)
      .catch(() => setLeaderStatus({ status: 'unknown' }))
  }, [isRemote])

  useEffect(() => {
    refreshLeader()
    if (!isRemote) return
    const id = setInterval(refreshLeader, 5000)
    return () => clearInterval(id)
  }, [isRemote, refreshLeader])

  const modeLabels: Record<string, string> = {
    idle: 'Idle',
    teleoperate: 'Teleoperating',
    record: 'Recording',
    train: 'Training',
    replay: 'Replaying',
  }

  const modeColors: Record<string, string> = {
    idle: 'bg-gray-700/80 text-gray-400',
    teleoperate: 'bg-emerald-900/60 text-emerald-300 ring-1 ring-emerald-500/30',
    record: 'bg-blue-900/60 text-blue-300 ring-1 ring-blue-500/30',
    train: 'bg-violet-900/60 text-violet-300 ring-1 ring-violet-500/30',
    replay: 'bg-amber-900/60 text-amber-300 ring-1 ring-amber-500/30',
  }

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-gray-700/50 bg-gray-950/90 px-6 py-3 backdrop-blur-md">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold tracking-tight text-white">TENSI Trossen Studio</h1>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${status.running ? (modeColors[status.mode] || modeColors.idle) : modeColors.idle}`}>
          {status.running && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
            </span>
          )}
          {!status.running && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-60" />}
          {modeLabels[status.mode] || status.mode}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden items-center gap-2 lg:flex">
          <Chip label="Follower" value={config?.robot?.follower_ip} dot="blue" />
          {isRemote ? (
            <Chip
              label="Leader Svc"
              value={`${config?.robot?.remote_leader_host}:${config?.robot?.remote_leader_port}`}
              dot={leaderStatus.status === 'running' ? 'green' : leaderStatus.status === 'stopped' ? 'red' : 'yellow'}
            />
          ) : (
            <Chip label="Leader" value={config?.robot?.leader_ip} dot="blue" />
          )}
        </div>
        <button
          onClick={onSettingsClick}
          className="ml-1 rounded-lg border border-gray-700 bg-gray-800/80 p-2 text-gray-400 transition hover:border-gray-500 hover:text-white"
          title="Settings"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
        </button>
      </div>
    </header>
  )
}

function Chip({ label, value, dot }: { label: string; value?: string; dot: 'green' | 'red' | 'yellow' | 'blue' }) {
  const colors = { green: 'bg-green-400', red: 'bg-red-400', yellow: 'bg-yellow-400', blue: 'bg-blue-400' }
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-gray-700/50 bg-gray-800/50 px-2 py-1">
      <span className={`h-1.5 w-1.5 rounded-full ${colors[dot]}`} />
      <span className="text-[11px] text-gray-500">{label}</span>
      {value && <span className="font-mono text-[11px] text-gray-400">{value}</span>}
    </div>
  )
}
