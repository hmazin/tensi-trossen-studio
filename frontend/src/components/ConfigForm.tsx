import { useState } from 'react'
import type { AppConfig } from '../api/client'
import { saveConfig } from '../api/client'

interface ConfigFormProps {
  config: AppConfig | null
  onConfigChange: (config: AppConfig) => void
}

export function ConfigForm({ config, onConfigChange }: ConfigFormProps) {
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

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

  if (!config) {
    return <div className="p-4 text-gray-500">Loading config...</div>
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4">
      <h2 className="mb-4 text-lg font-semibold text-white">Configuration</h2>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-gray-400">Leader IP</label>
            <input
              type="text"
              value={config.robot.leader_ip}
              onChange={(e) =>
                onConfigChange({
                  ...config,
                  robot: { ...config.robot, leader_ip: e.target.value },
                })
              }
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="192.168.1.2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-gray-400">Follower IP</label>
            <input
              type="text"
              value={config.robot.follower_ip}
              onChange={(e) =>
                onConfigChange({
                  ...config,
                  robot: { ...config.robot, follower_ip: e.target.value },
                })
              }
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="192.168.1.5"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="use-top-only"
            checked={config.robot.use_top_camera_only !== false}
            onChange={(e) =>
              onConfigChange({
                ...config,
                robot: { ...config.robot, use_top_camera_only: e.target.checked },
              })
            }
            className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="use-top-only" className="text-sm text-gray-400">
            Use top camera only (if wrist camera fails)
          </label>
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-400">Wrist camera serial</label>
          <input
            type="text"
            value={config.robot.cameras?.wrist?.serial_number_or_name ?? ''}
            onChange={(e) => {
              const cameras = { ...config.robot.cameras }
              cameras.wrist = { ...(cameras.wrist ?? { type: 'intelrealsense', width: 640, height: 480, fps: 30 }), serial_number_or_name: e.target.value }
              onConfigChange({ ...config, robot: { ...config.robot, cameras } })
            }}
            className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="218622275782"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-400">Top camera serial</label>
          <input
            type="text"
            value={config.robot.cameras?.top?.serial_number_or_name ?? ''}
            onChange={(e) => {
              const cameras = { ...config.robot.cameras }
              cameras.top = { ...(cameras.top ?? { type: 'intelrealsense', width: 640, height: 480, fps: 30 }), serial_number_or_name: e.target.value }
              onConfigChange({ ...config, robot: { ...config.robot, cameras } })
            }}
            className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="218622278263"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-400">LeRobot Trossen path</label>
          <input
            type="text"
            value={config.lerobot_trossen_path}
            onChange={(e) => onConfigChange({ ...config, lerobot_trossen_path: e.target.value })}
            className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="/home/user/lerobot_trossen"
          />
        </div>
        {message && <p className="text-sm text-amber-400">{message}</p>}
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Config'}
        </button>
      </div>
    </div>
  )
}
