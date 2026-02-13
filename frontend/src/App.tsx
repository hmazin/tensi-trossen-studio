import { useCallback, useEffect, useState } from 'react'
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
    if (!status.running) return
    const id = setInterval(refreshStatus, 1500)
    return () => clearInterval(id)
  }, [status.running, refreshStatus])

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white">TENSI Trossen Studio</h1>
        <p className="mt-1 text-gray-400">
          Web GUI for LeRobot Trossen — teleoperation, recording, training, replay
        </p>
      </header>
      <div className="space-y-6">
        <ConfigForm config={config} onConfigChange={setConfig} />
        <ActionPanel
          config={config}
          status={status}
          onAction={refreshStatus}
        />
        <CameraViewer config={config} status={status} />
        <ProcessLog status={status} />
      </div>
    </div>
  )
}

export default App
