import { useEffect, useRef, useState } from 'react'
import type { ProcessStatus } from '../api/client'

interface ProcessLogProps {
  status: ProcessStatus
}

export function ProcessLog({ status }: ProcessLogProps) {
  const preRef = useRef<HTMLPreElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (preRef.current && autoScroll) {
      preRef.current.scrollTop = preRef.current.scrollHeight
    }
  }, [status.logs, autoScroll])

  const handleScroll = () => {
    if (!preRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = preRef.current
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 40)
  }

  return (
    <div className="flex flex-col rounded-xl border border-gray-700/50 bg-gray-800/30">
      <div className="flex items-center justify-between border-b border-gray-700/40 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
          </svg>
          <span className="text-sm font-medium text-gray-300">Process Log</span>
          <span className="font-mono text-xs text-gray-600">{status.logs.length} lines</span>
        </div>
        {!autoScroll && (
          <button
            onClick={() => {
              setAutoScroll(true)
              if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight
            }}
            className="rounded border border-gray-600 bg-gray-700 px-2 py-0.5 text-[10px] text-gray-400 hover:text-white"
          >
            Scroll to bottom
          </button>
        )}
      </div>
      <pre
        ref={preRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto bg-gray-950/50 p-3 font-mono text-xs leading-5 text-gray-400"
        style={{ maxHeight: '320px', minHeight: '120px' }}
      >
        {status.logs.length > 0
          ? status.logs.join('\n')
          : <span className="text-gray-600 italic">No output yet. Start a process to see logs.</span>}
      </pre>
      {status.error && (
        <div className="border-t border-red-900/30 bg-red-950/20 px-4 py-2">
          <p className="text-xs text-red-400">Error: {status.error}</p>
        </div>
      )}
    </div>
  )
}
