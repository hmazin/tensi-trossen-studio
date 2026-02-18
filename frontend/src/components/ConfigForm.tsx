import { useState, useEffect } from 'react'
import type { AppConfig, UsbVideoDevice } from '../api/client'
import { saveConfig, getUsbVideoDevices } from '../api/client'

interface ConfigFormProps {
  config: AppConfig | null
  onConfigChange: (config: AppConfig) => void
  open: boolean
  onClose: () => void
}

export function ConfigForm({ config, onConfigChange, open, onClose }: ConfigFormProps) {
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [usbDevices, setUsbDevices] = useState<UsbVideoDevice[] | null>(null)
  const [usbDevicesLoading, setUsbDevicesLoading] = useState(false)
  const [usbDevicesError, setUsbDevicesError] = useState<string | null>(null)

  useEffect(() => {
    if (open) setMessage(null)
  }, [open])

  const handleSave = () => {
    if (!config) return
    setSaving(true)
    setMessage(null)
    saveConfig(config)
      .then((res) => {
        onConfigChange(res.config)
        setMessage('Config saved.')
      })
      .catch((e) => setMessage(`Failed to save: ${e}`))
      .finally(() => setSaving(false))
  }

  if (!config) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
        onClick={onClose}
      />

      {/* Panel */}
      <div className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-md transform flex-col border-l border-gray-700/50 bg-gray-900 shadow-2xl transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-700/50 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">Settings</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 transition hover:bg-gray-800 hover:text-white">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="space-y-6">
            {/* Robot Section */}
            <Section title="Robot">
              <Field label="Follower IP">
                <input type="text" value={config.robot.follower_ip} onChange={(e) => onConfigChange({ ...config, robot: { ...config.robot, follower_ip: e.target.value } })} className="input-field" placeholder="192.168.1.5" />
              </Field>

              <div className="rounded-lg border border-gray-700/50 bg-gray-800/30 p-3">
                <label className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={config.robot.remote_leader === true}
                    onChange={(e) => onConfigChange({ ...config, robot: { ...config.robot, remote_leader: e.target.checked } })}
                    className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-white">Remote Leader Mode</span>
                    <p className="text-[11px] text-gray-500">Leader on a separate PC running leader_service.py</p>
                  </div>
                </label>

                {config.robot.remote_leader ? (
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <Field label="Leader Service Host">
                      <input type="text" value={config.robot.remote_leader_host ?? '192.168.2.138'} onChange={(e) => onConfigChange({ ...config, robot: { ...config.robot, remote_leader_host: e.target.value } })} className="input-field" />
                    </Field>
                    <Field label="Port">
                      <input type="number" value={config.robot.remote_leader_port ?? 5555} onChange={(e) => onConfigChange({ ...config, robot: { ...config.robot, remote_leader_port: Number(e.target.value) } })} className="input-field" />
                    </Field>
                  </div>
                ) : (
                  <div className="mt-3">
                    <Field label="Leader IP (direct)">
                      <input type="text" value={config.robot.leader_ip} onChange={(e) => onConfigChange({ ...config, robot: { ...config.robot, leader_ip: e.target.value } })} className="input-field" placeholder="192.168.1.2" />
                    </Field>
                  </div>
                )}
              </div>
            </Section>

            {/* Camera Section */}
            <Section title="Cameras">
              <label className="flex items-center gap-2.5">
                <input
                  type="checkbox"
                  checked={config.robot.use_top_camera_only !== false}
                  onChange={(e) => onConfigChange({ ...config, robot: { ...config.robot, use_top_camera_only: e.target.checked } })}
                  className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-300">Use top camera only</span>
              </label>
              <Field label="Wrist camera serial">
                <input
                  type="text"
                  value={config.robot.cameras?.wrist?.serial_number_or_name ?? ''}
                  onChange={(e) => {
                    const cameras = { ...config.robot.cameras }
                    cameras.wrist = { ...(cameras.wrist ?? { type: 'intelrealsense', width: 640, height: 480, fps: 30 }), serial_number_or_name: e.target.value }
                    onConfigChange({ ...config, robot: { ...config.robot, cameras } })
                  }}
                  className="input-field"
                  placeholder="218622275782"
                />
              </Field>
              <Field label="Top camera serial">
                <input
                  type="text"
                  value={config.robot.cameras?.top?.serial_number_or_name ?? ''}
                  onChange={(e) => {
                    const cameras = { ...config.robot.cameras }
                    cameras.top = { ...(cameras.top ?? { type: 'intelrealsense', width: 640, height: 480, fps: 30 }), serial_number_or_name: e.target.value }
                    onConfigChange({ ...config, robot: { ...config.robot, cameras } })
                  }}
                  className="input-field"
                  placeholder="218622278263"
                />
              </Field>

              {/* Operator view camera - USB, not RealSense; not used for teleop/recording */}
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/30 p-3">
                <label className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={config.robot.operator_camera != null}
                    onChange={(e) => {
                      const operator_camera = e.target.checked
                        ? { type: 'usb', device_index: 0, width: 640, height: 480, fps: 30 }
                        : null
                      onConfigChange({ ...config, robot: { ...config.robot, operator_camera } })
                    }}
                    className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-white">Operator view camera (USB)</span>
                    <p className="text-[11px] text-gray-500">USB camera for operator view only; not a RealSense, not used for teleop or recording</p>
                  </div>
                </label>
                {config.robot.operator_camera != null ? (
                  <div className="mt-3 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                    <Field label="Device index">
                      <input
                        type="number"
                        min={0}
                        value={config.robot.operator_camera.device_index ?? 0}
                        onChange={(e) =>
                          onConfigChange({
                            ...config,
                            robot: {
                              ...config.robot,
                              operator_camera: { ...config.robot.operator_camera!, device_index: Number(e.target.value) },
                            },
                          })
                        }
                        className="input-field"
                      />
                    </Field>
                    <Field label="Width">
                      <input
                        type="number"
                        min={1}
                        value={config.robot.operator_camera.width ?? 640}
                        onChange={(e) =>
                          onConfigChange({
                            ...config,
                            robot: {
                              ...config.robot,
                              operator_camera: { ...config.robot.operator_camera!, width: Number(e.target.value) },
                            },
                          })
                        }
                        className="input-field"
                      />
                    </Field>
                    <Field label="Height">
                      <input
                        type="number"
                        min={1}
                        value={config.robot.operator_camera.height ?? 480}
                        onChange={(e) =>
                          onConfigChange({
                            ...config,
                            robot: {
                              ...config.robot,
                              operator_camera: { ...config.robot.operator_camera!, height: Number(e.target.value) },
                            },
                          })
                        }
                        className="input-field"
                      />
                    </Field>
                    <Field label="FPS">
                      <input
                        type="number"
                        min={1}
                        value={config.robot.operator_camera.fps ?? 30}
                        onChange={(e) =>
                          onConfigChange({
                            ...config,
                            robot: {
                              ...config.robot,
                              operator_camera: { ...config.robot.operator_camera!, fps: Number(e.target.value) },
                            },
                          })
                        }
                        className="input-field"
                      />
                    </Field>
                    </div>
                    <div className="rounded border border-gray-600 bg-gray-800/50 p-2">
                      <p className="mb-2 text-xs text-gray-500">Identify USB camera index</p>
                      <button
                        type="button"
                        disabled={usbDevicesLoading}
                        onClick={() => {
                          setUsbDevicesError(null)
                          setUsbDevices(null)
                          setUsbDevicesLoading(true)
                          getUsbVideoDevices()
                            .then((r) => { setUsbDevices(r.devices); setUsbDevicesError(r.error ?? null) })
                            .catch((e) => { setUsbDevicesError(e instanceof Error ? e.message : String(e)); setUsbDevices([]) })
                            .finally(() => setUsbDevicesLoading(false))
                        }}
                        className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600 disabled:opacity-50"
                      >
                        {usbDevicesLoading ? 'Detecting…' : 'Detect USB cameras'}
                      </button>
                      {usbDevicesError && <p className="mt-2 text-xs text-amber-400">{usbDevicesError}</p>}
                      {usbDevices && usbDevices.length === 0 && !usbDevicesError && <p className="mt-2 text-xs text-gray-500">No /dev/video* devices found (Linux).</p>}
                      {usbDevices && usbDevices.length > 0 && (
                        <ul className="mt-2 space-y-1 text-xs">
                          {usbDevices.map((d) => (
                            <li key={d.index} className="flex items-center justify-between gap-2 rounded bg-gray-900/80 px-2 py-1">
                              <span className="text-gray-400">Index {d.index}: {d.path}{d.name ? ` — ${d.name}` : ''}</span>
                              <button
                                type="button"
                                onClick={() =>
                                  onConfigChange({
                                    ...config,
                                    robot: {
                                      ...config.robot,
                                      operator_camera: { ...config.robot.operator_camera!, device_index: d.index },
                                    },
                                  })
                                }
                                className="shrink-0 rounded bg-blue-600/80 px-2 py-0.5 text-white hover:bg-blue-500"
                              >
                                Use
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                ) : null}
              </div>
            </Section>

            {/* Network Section — two networks doc + Studio host for other PCs */}
            <Section title="Network">
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/30 p-3">
                <p className="mb-2 text-xs font-medium text-gray-400">Two networks (do not mix)</p>
                <table className="w-full text-[11px] text-gray-500">
                  <tbody>
                    <tr>
                      <td className="py-0.5 font-mono text-amber-400/90">192.168.1.x</td>
                      <td className="py-0.5 pl-2">Ethernet — Netgate, robot arms. Use for Leader IP, Follower IP.</td>
                    </tr>
                    <tr>
                      <td className="py-0.5 font-mono text-emerald-400/90">192.168.2.x</td>
                      <td className="py-0.5 pl-2">WiFi — Internet, internal LAN. Open Studio from another PC; Leader Service Host (PC2) for distributed.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <Field label="Studio host for other PCs (this PC’s 192.168.2.x)">
                <input
                  type="text"
                  value={config.robot.studio_host_for_remote ?? ''}
                  onChange={(e) =>
                    onConfigChange({
                      ...config,
                      robot: {
                        ...config.robot,
                        studio_host_for_remote: e.target.value.trim() || undefined,
                      },
                    })
                  }
                  className="input-field"
                  placeholder="e.g. 192.168.2.140"
                />
                <p className="mt-1 text-[11px] text-gray-500">Used for “Open from another PC” link in the header. Leave empty to set later.</p>
              </Field>
            </Section>

            {/* Paths Section */}
            <Section title="Paths">
              <Field label="LeRobot Trossen path">
                <input type="text" value={config.lerobot_trossen_path} onChange={(e) => onConfigChange({ ...config, lerobot_trossen_path: e.target.value })} className="input-field" />
              </Field>
            </Section>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-700/50 px-6 py-4">
          {message && <p className={`mb-3 text-sm ${message.startsWith('Failed') ? 'text-red-400' : 'text-emerald-400'}`}>{message}</p>}
          <div className="flex gap-3">
            <button onClick={onClose} className="flex-1 rounded-lg border border-gray-600 bg-gray-800 py-2.5 text-sm font-medium text-gray-300 transition hover:bg-gray-700">
              Cancel
            </button>
            <button onClick={handleSave} disabled={saving} className="flex-1 rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs text-gray-500">{label}</label>
      {children}
    </div>
  )
}
