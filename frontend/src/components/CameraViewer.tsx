import { useEffect, useState } from 'react'
import { detectCameras, getCameraStatus, getCameraStreamUrl, type AppConfig, type CameraDetectResult, type CameraStatusResult, type ProcessStatus } from '../api/client'

interface CameraViewerProps {
  config: AppConfig | null
  status: ProcessStatus
}

export function CameraViewer({ config, status }: CameraViewerProps) {
  const [errors, setErrors] = useState<Record<string, boolean>>({})
  const [diagnostics, setDiagnostics] = useState<CameraDetectResult | null>(null)
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false)
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false)
  const [cameraStatus, setCameraStatus] = useState<CameraStatusResult | null>(null)

  const cameras = config?.robot?.cameras ?? {}
  const hasOperatorCamera = Boolean(config?.robot?.operator_camera)
  // Always show at least wrist and top when we have config, so camera section is visible even if cameras object was empty
  const baseKeys = Object.keys(cameras).length > 0 ? Object.keys(cameras) : (config?.robot ? ['wrist', 'top'] : [])
  const cameraKeys = [...baseKeys, ...(hasOperatorCamera ? ['operator'] : [])]

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const st = await getCameraStatus()
        setCameraStatus(st)
      } catch {
        // Ignore
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const runDiagnostics = async () => {
    setDiagnosticsLoading(true)
    setDiagnosticsOpen(true)
    try {
      const r = await detectCameras()
      setDiagnostics(r)
    } catch (e) {
      setDiagnostics({ detected: [], error: String(e) })
    } finally {
      setDiagnosticsLoading(false)
    }
  }

  if (cameraKeys.length === 0) {
    return (
      <div className="rounded-xl border border-gray-700/50 bg-gray-800/30 p-4">
        <h2 className="mb-4 text-sm font-semibold text-gray-300">Camera Feed</h2>
        <p className="text-sm text-gray-500">
          No camera config loaded. Open Settings to set wrist and top camera serials (and optionally enable Operator camera), then save. If you already did, reload the page or check that the backend is running.
        </p>
      </div>
    )
  }

  const handleError = (key: string) => {
    setErrors((prev) => ({ ...prev, [key]: true }))
  }

  const handleLoad = (key: string) => {
    setErrors((prev) => ({ ...prev, [key]: false }))
  }

  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/30 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
          <h2 className="text-sm font-semibold text-gray-300">Camera Feed</h2>
        </div>
        <button
          type="button"
          onClick={runDiagnostics}
          disabled={diagnosticsLoading}
          className="rounded-lg border border-gray-600 bg-gray-700/50 px-3 py-1 text-xs text-gray-400 hover:bg-gray-600 hover:text-white disabled:opacity-50"
        >
          {diagnosticsLoading ? 'Checking…' : 'Detect cameras'}
        </button>
      </div>
      {diagnosticsOpen && diagnostics && (
        <div className="mb-4 rounded border border-gray-600 bg-gray-900/80 p-3 text-sm">
          <div className="font-medium text-gray-300">Camera diagnostics</div>
          {diagnostics.error && (
            <p className="mt-1 text-amber-400">{diagnostics.error}</p>
          )}
          {diagnostics.detected.length > 0 ? (
            <div className="mt-2 space-y-1">
              <span className="text-gray-500">Detected:</span>
              <ul className="list-inside list-disc text-gray-400">
                {diagnostics.detected.map((d) => (
                  <li key={d.serial}>
                    {d.serial} ({d.name})
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mt-1 text-amber-400">No RealSense cameras detected</p>
          )}
          {diagnostics.configured && Object.keys(diagnostics.configured).length > 0 && (
            <div className="mt-2">
              <span className="text-gray-500">Configured:</span>
              <ul className="list-inside list-disc text-gray-400">
                {Object.entries(diagnostics.configured).map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}
                    {diagnostics.detected.some((d) => d.serial === v)
                      ? ' ✓'
                      : ' — not detected'}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cameraKeys.map((key) => {
          const camStatus = cameraStatus?.cameras?.[key]
          const hasHardwareError = camStatus?.error_type === 'hardware_timeout'
          const isOperator = key === 'operator'
          return (
            <div key={key} className="flex flex-col gap-2">
              <span className="text-sm font-medium capitalize text-gray-400">
                {isOperator ? 'Operator view' : key}
                {isOperator && (
                  <span className="ml-2 rounded bg-gray-600/70 px-1.5 py-0.5 text-xs text-gray-400">HMI only</span>
                )}
                {hasHardwareError && (
                  <span className="ml-2 text-xs text-red-400">⚠ Hardware issue</span>
                )}
              </span>
              <div className="relative aspect-video overflow-hidden rounded-lg border border-gray-600 bg-gray-900">
                {errors[key] || hasHardwareError ? (
                  <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-sm">
                    {hasHardwareError ? (
                      <>
                        <span className="text-red-400">⚠ Camera hardware timeout</span>
                        <span className="text-xs text-gray-500">
                          {camStatus?.message}
                        </span>
                        <span className="text-xs text-gray-600">
                          Serial: {camStatus?.details?.serial}
                        </span>
                      </>
                    ) : status.running ? (
                      <span className="text-amber-400">Camera in use by teleoperation</span>
                    ) : (
                      <span className="text-amber-400">Camera unavailable</span>
                    )}
                  </div>
                ) : (
                  <img
                    src={getCameraStreamUrl(key)}
                    alt={`${key} camera`}
                    className="h-full w-full object-contain"
                    onError={() => handleError(key)}
                    onLoad={() => handleLoad(key)}
                  />
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
