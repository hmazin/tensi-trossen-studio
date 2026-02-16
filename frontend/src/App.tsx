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
  const [status, setStatus] = useState<ProcessStatus>({
    mode: 'idle',
    running: false,
    pid: null,
    logs: [],
    error: null,
  })
  const [settingsOpen, setSettingsOpen] = useState(false)

  useEffect(() => {
    getConfig().then(setConfig).catch(() => {})
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
