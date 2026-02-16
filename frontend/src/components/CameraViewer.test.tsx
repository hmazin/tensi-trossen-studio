import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CameraViewer } from './CameraViewer'

vi.mock('../api/client', () => ({
  detectCameras: vi.fn().mockResolvedValue({ detected: [] }),
  getCameraStatus: vi.fn().mockResolvedValue({ cameras: {} }),
  getCameraStreamUrl: vi.fn((key: string) => `/api/cameras/stream/${key}`),
}))

const idle = { mode: 'idle', running: false, pid: null, logs: [] as string[], error: null }

describe('CameraViewer', () => {
  it('shows add cameras message when no cameras configured', () => {
    const config = { robot: { cameras: {} } } as any
    render(<CameraViewer config={config} status={idle} />)
    expect(screen.getByText(/Add cameras in Settings/i)).toBeInTheDocument()
  })

  it('renders camera labels when cameras configured', () => {
    const config = {
      robot: {
        cameras: {
          wrist: { type: 'intelrealsense', serial_number_or_name: 'ABC', width: 640, height: 480, fps: 30 },
          top: { type: 'intelrealsense', serial_number_or_name: 'DEF', width: 640, height: 480, fps: 30 },
        },
      },
    } as any
    render(<CameraViewer config={config} status={idle} />)
    expect(screen.getByText('wrist')).toBeInTheDocument()
    expect(screen.getByText('top')).toBeInTheDocument()
  })

  it('shows Camera Feed heading when cameras exist', () => {
    const config = {
      robot: {
        cameras: {
          top: { type: 'intelrealsense', serial_number_or_name: 'X', width: 640, height: 480, fps: 30 },
        },
      },
    } as any
    render(<CameraViewer config={config} status={idle} />)
    expect(screen.getByText('Camera Feed')).toBeInTheDocument()
  })
})
