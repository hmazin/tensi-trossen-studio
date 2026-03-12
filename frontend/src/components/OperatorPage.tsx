import { useCallback, useEffect, useState } from 'react'
import { getConfig, getProcessStatus, getCameraStreamUrl, startTeleoperate, stopTeleoperate } from '../api/client'
import type { AppConfig, ProcessStatus } from '../api/client'

export function OperatorPage() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [configError, setConfigError] = useState<string | null>(null)
  const [status, setStatus] = useState<ProcessStatus>({
    mode: 'idle',
    running: false,
    pid: null,
    logs: [],
    error: null,
  })
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    setConfigError(null)
    getConfig()
      .then(setConfig)
      .catch((e) => setConfigError(e instanceof Error ? e.message : 'Failed to load config'))
  }, [])

  const refreshStatus = useCallback(async () => {
    try {
      const s = await getProcessStatus()
      setStatus(s)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    const id = setInterval(refreshStatus, status.running ? 1500 : 3000)
    return () => clearInterval(id)
  }, [status.running, refreshStatus])

  const isTeleoperating = status.running && status.mode === 'teleoperate'

  const handleToggleTeleop = async () => {
    if (busy) return
    setBusy(true)
    setActionError(null)
    try {
      if (isTeleoperating) {
        await stopTeleoperate()
      } else {
        await startTeleoperate(true, config?.robot?.use_top_camera_only !== false)
      }
      await refreshStatus()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setActionError(msg)
    } finally {
      setBusy(false)
    }
  }

  const hasOperatorCamera = Boolean(config?.robot?.operator_camera)
  const streamUrl = getCameraStreamUrl('operator')
  const cameras = config?.robot?.cameras ?? {}
  const wristKey = cameras.right_wrist ? 'right_wrist' : cameras.left_wrist ? 'left_wrist' : null
  const wristLabel = wristKey === 'right_wrist' ? 'Right wrist' : wristKey === 'left_wrist' ? 'Left wrist' : ''

  return (
    <div className="fixed inset-0 flex flex-col bg-gray-950">
      {/* Top bar: back link + title + start/stop button */}
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-gray-700/50 bg-gray-900/95 px-4 py-2">
        <a
          href="/"
          className="text-sm text-gray-400 hover:text-white"
        >
          &larr; Back to Studio
        </a>
        <span className="text-sm font-medium text-gray-300">Operator view</span>
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={handleToggleTeleop}
            disabled={busy || configError != null}
            className={
              isTeleoperating
                ? 'rounded-lg bg-red-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50'
                : 'rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50'
            }
          >
            {busy ? '...' : isTeleoperating ? 'Stop teleoperation' : 'Start teleoperation'}
          </button>
          {actionError && (
            <p className="max-w-sm text-right text-xs text-red-400" role="alert">
              {actionError}
            </p>
          )}
        </div>
      </header>

      {/* Full-area camera or message */}
      <main className="relative flex flex-1 min-h-0">
        {configError && (
          <div className="flex flex-1 items-center justify-center p-6">
            <p className="text-center text-amber-400">{configError}</p>
          </div>
        )}

        {!configError && !config && (
          <div className="flex flex-1 items-center justify-center p-6">
            <p className="text-gray-500">Loading...</p>
          </div>
        )}

        {!configError && config && !hasOperatorCamera && (
          <div className="flex flex-1 items-center justify-center p-6">
            <p className="max-w-md text-center text-gray-400">
              Operator camera is not configured. On PC1 open Studio, go to Settings &rarr; Cameras, enable Operator view camera (USB), and save.
            </p>
          </div>
        )}

        {!configError && config && hasOperatorCamera && (
          <>
            <div className="absolute inset-0 flex items-center justify-center bg-black">
              <img
                src={streamUrl}
                alt="Operator camera"
                className="h-full w-full object-contain"
                style={{ maxHeight: '100vh' }}
              />
            </div>
            {wristKey && (
              <div className="absolute left-4 top-4 z-10 w-[380px] overflow-hidden rounded-lg border-2 border-gray-600 bg-gray-900 shadow-lg">
                <div className="bg-gray-800/90 px-2 py-1 text-xs font-medium text-gray-300">
                  {wristLabel}
                </div>
                <img
                  src={getCameraStreamUrl(wristKey)}
                  alt={wristLabel}
                  className="h-[220px] w-full object-contain bg-black"
                />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
