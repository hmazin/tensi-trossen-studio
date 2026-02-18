import { useCallback, useEffect, useState } from 'react'
import { StatusBar } from './components/StatusBar'
import { ActionPanel } from './components/ActionPanel'
import { CameraViewer } from './components/CameraViewer'
import { ConfigForm } from './components/ConfigForm'
import { ProcessLog } from './components/ProcessLog'
import { getConfig, getProcessStatus } from './api/client'
import type { AppConfig, ProcessStatus } from './api/client'

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [configError, setConfigError] = useState<string | null>(null)
  const [status, setStatus] = useState<ProcessStatus>({
    mode: 'idle',
    running: false,
    pid: null,
    logs: [],
    error: null,
  })
  const [settingsOpen, setSettingsOpen] = useState(false)

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
      // Backend may be down
    }
  }, [])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    const id = setInterval(refreshStatus, status.running ? 1500 : 3000)
    return () => clearInterval(id)
  }, [status.running, refreshStatus])

  return (
    <div className="flex h-screen flex-col bg-gray-950">
      {configError && (
        <div className="bg-amber-900/50 border-b border-amber-600/50 px-4 py-2 text-sm text-amber-200 flex items-center justify-between gap-4">
          <span>Cannot reach backend: {configError}. Check that you are using PC1’s IP (e.g. http://192.168.2.140:5173) and that the backend is running on PC1.</span>
          <button type="button" onClick={() => { setConfigError(null); getConfig().then(setConfig).catch((e) => setConfigError(e instanceof Error ? e.message : 'Failed')) }} className="rounded bg-amber-700 px-2 py-1 text-xs hover:bg-amber-600">Retry</button>
        </div>
      )}
      <StatusBar
        config={config}
        status={status}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-y-auto">
          {/* Top: cameras + actions side by side */}
          <div className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-5">
            {/* Camera feeds - takes more space */}
            <div className="lg:col-span-3">
              <CameraViewer config={config} status={status} />
            </div>

            {/* Actions panel */}
            <div className="lg:col-span-2">
              <ActionPanel
                config={config}
                status={status}
                onAction={refreshStatus}
              />
            </div>
          </div>

          {/* Bottom: process log full width */}
          <div className="px-4 pb-4">
            <ProcessLog status={status} />
          </div>
        </div>
      </div>

      {/* Settings drawer */}
      <ConfigForm
        config={config}
        onConfigChange={setConfig}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  )
}

export default App
