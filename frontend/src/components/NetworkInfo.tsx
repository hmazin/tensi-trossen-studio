import { useState, useRef, useEffect } from 'react'
import type { AppConfig } from '../api/client'

const NETWORK_DOC = `Two networks (do not mix)

• 192.168.1.x (Ethernet) — Netgate, robot arms
  Use for: Leader IP, Follower IP in Settings.
  Robots and hardware only.

• 192.168.2.x (WiFi) — Internet, internal LAN
  Use for: Opening Studio from another PC (e.g. PC2).
  Leader Service Host (PC2) for distributed teleop must be PC2’s 192.168.2.x.`

interface NetworkInfoProps {
  config: AppConfig | null
  open: boolean
  onClose: () => void
  anchorRef: React.RefObject<HTMLElement | null>
  onOpenSettings?: () => void
}

export function NetworkInfo({ config, open, onClose, anchorRef, onOpenSettings }: NetworkInfoProps) {
  const [copied, setCopied] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  const host = config?.robot?.studio_host_for_remote ?? null
  const shareUrl = host ? `http://${host}:5173` : null

  const copyUrl = () => {
    if (!shareUrl) return
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        open &&
        panelRef.current && !panelRef.current.contains(e.target as Node) &&
        anchorRef.current && !anchorRef.current.contains(e.target as Node)
      ) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open, onClose, anchorRef])

  if (!open) return null

  return (
    <div
      ref={panelRef}
      className="absolute right-0 top-full z-50 mt-2 w-[340px] rounded-lg border border-gray-600 bg-gray-900 shadow-xl"
    >
      <div className="border-b border-gray-700/50 px-4 py-2">
        <h3 className="text-sm font-semibold text-white">Network</h3>
      </div>
      <div className="space-y-4 p-4 text-sm">
        <pre className="whitespace-pre-wrap rounded bg-gray-800/80 p-3 font-sans text-xs text-gray-300">
          {NETWORK_DOC}
        </pre>
        <div>
          <p className="mb-1.5 text-xs text-gray-500">Open from another PC (use this PC’s 192.168.2.x)</p>
          {shareUrl ? (
            <div className="flex items-center gap-2">
              <code className="flex-1 truncate rounded bg-gray-800 px-2 py-1.5 text-xs text-emerald-300">
                {shareUrl}
              </code>
              <button
                type="button"
                onClick={copyUrl}
                className="shrink-0 rounded bg-gray-700 px-2 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          ) : (
            <p className="rounded bg-gray-800/50 px-2 py-1.5 text-xs text-gray-500">
              Set in Settings → Network (Studio host for other PCs)
            </p>
          )}
          {onOpenSettings && (
            <button
              type="button"
              onClick={() => { onClose(); onOpenSettings() }}
              className="mt-2 text-xs text-blue-400 hover:underline"
            >
              Open Settings →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
