import { useEffect, useRef } from 'react'
import type { ProcessStatus } from '../api/client'

interface ProcessLogProps {
  status: ProcessStatus
}

export function ProcessLog({ status }: ProcessLogProps) {
  const preRef = useRef<HTMLPreElement>(null)

  useEffect(() => {
    if (preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight
    }
  }, [status.logs])

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Process Log</h2>
        <span
          className={`rounded px-2 py-1 text-sm font-medium ${
            status.running
              ? 'bg-amber-900/50 text-amber-300'
              : 'bg-gray-700 text-gray-400'
          }`}
        >
          {status.running ? `Running: ${status.mode}` : 'Idle'}
        </span>
      </div>
      <pre
        ref={preRef}
        className="max-h-64 overflow-y-auto rounded bg-gray-900 p-3 font-mono text-sm text-gray-300"
      >
        {status.logs.length > 0
          ? status.logs.join('\n')
          : 'No output yet. Start a process to see logs.'}
      </pre>
      {status.error && (
        <p className="mt-2 text-sm text-red-400">Error: {status.error}</p>
      )}
    </div>
  )
}
