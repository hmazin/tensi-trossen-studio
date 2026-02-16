import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProcessLog } from './ProcessLog'

const idle = { mode: 'idle', running: false, pid: null, logs: [] as string[], error: null }

describe('ProcessLog', () => {
  it('shows placeholder when no logs', () => {
    render(<ProcessLog status={idle} />)
    expect(screen.getByText(/No output yet/i)).toBeInTheDocument()
  })

  it('renders log lines', () => {
    const status = { ...idle, logs: ['Hello world', 'Second line'] }
    render(<ProcessLog status={status} />)
    expect(screen.getByText(/Hello world/)).toBeInTheDocument()
    expect(screen.getByText(/Second line/)).toBeInTheDocument()
  })

  it('shows line count', () => {
    const status = { ...idle, logs: ['a', 'b', 'c'] }
    render(<ProcessLog status={status} />)
    expect(screen.getByText('3 lines')).toBeInTheDocument()
  })

  it('shows error footer when error is set', () => {
    const status = { ...idle, error: 'Process crashed' }
    render(<ProcessLog status={status} />)
    expect(screen.getByText(/Process crashed/)).toBeInTheDocument()
  })
})
