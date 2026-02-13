import { useState } from 'react'
import {
  startTeleoperate,
  stopTeleoperate,
  startRecord,
  stopRecord,
  startTrain,
  stopTrain,
  startReplay,
  stopReplay,
  stopProcess,
} from '../api/client'
import type { AppConfig, ProcessStatus } from '../api/client'

interface ActionPanelProps {
  config: AppConfig | null
  status: ProcessStatus
  onAction: () => void
}

export function ActionPanel({ config, status, onAction }: ActionPanelProps) {
  const [recordRepoId, setRecordRepoId] = useState('tensi/test_dataset')
  const [recordEpisodes, setRecordEpisodes] = useState(10)
  const [recordTask, setRecordTask] = useState('Grab the cube')
  const [trainRepoId, setTrainRepoId] = useState('tensi/test_dataset')
  const [replayRepoId, setReplayRepoId] = useState('tensi/test_dataset')
  const [replayEpisode, setReplayEpisode] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const running = status.running

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4">
      <h2 className="mb-4 text-lg font-semibold text-white">Actions</h2>
      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      <div className="flex flex-wrap gap-4">
        {!running ? (
          <>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-gray-400">Teleoperate</span>
              <button
                onClick={() =>
                  run(
                    () =>
                      startTeleoperate(true, config?.robot?.use_top_camera_only !== false)
                  )
                }
                disabled={busy}
                className="rounded bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Start Teleoperate
              </button>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-gray-400">Record</span>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={recordRepoId}
                  onChange={(e) => setRecordRepoId(e.target.value)}
                  placeholder="repo_id"
                  className="w-40 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                />
                <input
                  type="number"
                  value={recordEpisodes}
                  onChange={(e) => setRecordEpisodes(Number(e.target.value))}
                  className="w-16 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                />
                <input
                  type="text"
                  value={recordTask}
                  onChange={(e) => setRecordTask(e.target.value)}
                  placeholder="task"
                  className="w-32 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                />
                <button
                  onClick={() =>
                    run(
                      () =>
                        startRecord({
                          repo_id: recordRepoId,
                          num_episodes: recordEpisodes,
                          single_task: recordTask,
                          push_to_hub: false,
                          use_top_camera_only: config?.robot?.use_top_camera_only !== false,
                        })
                    )
                  }
                  disabled={busy}
                  className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  Start Record
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-gray-400">Train</span>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={trainRepoId}
                  onChange={(e) => setTrainRepoId(e.target.value)}
                  placeholder="dataset repo"
                  className="w-48 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                />
                <button
                  onClick={() =>
                    run(() =>
                      startTrain({
                        dataset_repo_id: trainRepoId,
                        output_dir: `outputs/train/act_${trainRepoId.split('/').pop()}`,
                        job_name: `act_${trainRepoId.split('/').pop()}`,
                      })
                    )
                  }
                  disabled={busy}
                  className="rounded bg-violet-600 px-4 py-2 text-white hover:bg-violet-700 disabled:opacity-50"
                >
                  Start Train
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-gray-400">Replay</span>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={replayRepoId}
                  onChange={(e) => setReplayRepoId(e.target.value)}
                  placeholder="repo_id"
                  className="w-40 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                />
                <input
                  type="number"
                  value={replayEpisode}
                  onChange={(e) => setReplayEpisode(Number(e.target.value))}
                  className="w-16 rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-white"
                />
                <button
                  onClick={() =>
                    run(() =>
                      startReplay({ repo_id: replayRepoId, episode: replayEpisode })
                    )
                  }
                  disabled={busy}
                  className="rounded bg-amber-600 px-4 py-2 text-white hover:bg-amber-700 disabled:opacity-50"
                >
                  Replay
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-4">
            <span className="text-amber-400">
              Running: {status.mode} {status.pid && `(PID ${status.pid})`}
            </span>
            <button
              onClick={() => run(stopProcess)}
              disabled={busy}
              className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:opacity-50"
            >
              Stop
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
