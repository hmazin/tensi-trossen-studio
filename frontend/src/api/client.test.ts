import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getConfig,
  saveConfig,
  startTeleoperate,
  stopTeleoperate,
  startRecord,
  stopRecord,
  startTrain,
  stopTrain,
  startReplay,
  stopReplay,
  stopProcess,
  getProcessStatus,
  detectCameras,
  getCameraStatus,
  shutdownCameras,
  getLeaderServiceStatus,
  startLeaderService,
  stopLeaderService,
  getLeaderServiceLogs,
} from './client'

const mockFetch = vi.fn()
global.fetch = mockFetch

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  } as Response)
}

beforeEach(() => {
  mockFetch.mockReset()
})

describe('getConfig', () => {
  it('calls GET /api/config', async () => {
    const cfg = { robot: { leader_ip: '1.2.3.4' } }
    mockFetch.mockReturnValueOnce(jsonResponse(cfg))

    const result = await getConfig()
    expect(result).toEqual(cfg)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/config'),
      expect.objectContaining({ headers: expect.any(Object) }),
    )
  })
})

describe('saveConfig', () => {
  it('calls POST /api/config with JSON body', async () => {
    const cfg = { robot: { leader_ip: '1.1.1.1' } } as any
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'saved', config: cfg }))

    const result = await saveConfig(cfg)
    expect(result.status).toBe('saved')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/config'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(cfg) }),
    )
  })
})

describe('startTeleoperate', () => {
  it('calls POST with display_data param', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'started', mode: 'teleoperate' }))

    const result = await startTeleoperate(true, true)
    expect(result.status).toBe('started')
    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('display_data=true')
    expect(url).toContain('use_top_camera_only=true')
  })
})

describe('stopTeleoperate', () => {
  it('calls POST /teleoperate/stop', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'stopped' }))
    const result = await stopTeleoperate()
    expect(result.status).toBe('stopped')
  })
})

describe('startRecord', () => {
  it('includes all optional params', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'started', mode: 'record' }))

    await startRecord({
      repo_id: 'user/data',
      num_episodes: 5,
      episode_time_s: 30,
      single_task: 'Pick cube',
      push_to_hub: true,
      use_top_camera_only: true,
    })

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('repo_id=user%2Fdata')
    expect(url).toContain('num_episodes=5')
    expect(url).toContain('single_task=Pick+cube')
    expect(url).toContain('push_to_hub=true')
  })
})

describe('stopRecord', () => {
  it('calls POST /record/stop', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'stopped' }))
    const result = await stopRecord()
    expect(result.status).toBe('stopped')
  })
})

describe('startTrain', () => {
  it('calls POST with train params', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'started', mode: 'train' }))
    await startTrain({ dataset_repo_id: 'user/data', policy_type: 'act' })
    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('dataset_repo_id=user%2Fdata')
    expect(url).toContain('policy_type=act')
  })
})

describe('stopTrain', () => {
  it('calls POST /train/stop', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'stopped' }))
    const result = await stopTrain()
    expect(result.status).toBe('stopped')
  })
})

describe('startReplay', () => {
  it('calls POST with replay params', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'started', mode: 'replay' }))
    await startReplay({ repo_id: 'user/data', episode: 5 })
    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('repo_id=user%2Fdata')
    expect(url).toContain('episode=5')
  })
})

describe('stopReplay', () => {
  it('calls POST /replay/stop', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'stopped' }))
    const result = await stopReplay()
    expect(result.status).toBe('stopped')
  })
})

describe('stopProcess', () => {
  it('calls POST /process/stop', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'stopped' }))
    const result = await stopProcess()
    expect(result.status).toBe('stopped')
  })
})

describe('getProcessStatus', () => {
  it('returns process status', async () => {
    const data = { mode: 'idle', running: false, pid: null, logs: [], error: null }
    mockFetch.mockReturnValueOnce(jsonResponse(data))
    const result = await getProcessStatus()
    expect(result.mode).toBe('idle')
    expect(result.running).toBe(false)
  })
})

describe('camera APIs', () => {
  it('detectCameras calls /cameras/detect', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ detected: [], configured: {} }))
    const result = await detectCameras()
    expect(result.detected).toEqual([])
  })

  it('getCameraStatus calls /cameras/status', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ cameras: {} }))
    const result = await getCameraStatus()
    expect(result.cameras).toEqual({})
  })

  it('shutdownCameras calls POST /cameras/shutdown', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'shutdown', cameras_released: [] }))
    const result = await shutdownCameras()
    expect(result.status).toBe('shutdown')
  })
})

describe('leader service APIs', () => {
  it('getLeaderServiceStatus returns status', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'running', host: '10.0.0.1', port: 5555 }))
    const result = await getLeaderServiceStatus()
    expect(result.status).toBe('running')
  })

  it('startLeaderService calls POST', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'started', pid: '12345' }))
    const result = await startLeaderService()
    expect(result.status).toBe('started')
  })

  it('stopLeaderService calls POST', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ status: 'stopped' }))
    const result = await stopLeaderService()
    expect(result.status).toBe('stopped')
  })

  it('getLeaderServiceLogs returns logs', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ logs: ['line1', 'line2'] }))
    const result = await getLeaderServiceLogs(10)
    expect(result.logs).toEqual(['line1', 'line2'])
  })
})

describe('error handling', () => {
  it('throws on non-200 with detail', async () => {
    mockFetch.mockReturnValueOnce(
      Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Something broke' }),
      } as Response),
    )
    await expect(getConfig()).rejects.toThrow('Something broke')
  })

  it('throws with HTTP status when no detail', async () => {
    mockFetch.mockReturnValueOnce(
      Promise.resolve({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.reject(new Error('no json')),
      } as Response),
    )
    await expect(getConfig()).rejects.toThrow('Not Found')
  })
})
