import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ActionPanel } from './ActionPanel'

vi.mock('../api/client', () => ({
  startTeleoperate: vi.fn().mockResolvedValue({ status: 'started' }),
  startRecord: vi.fn().mockResolvedValue({ status: 'started' }),
  startTrain: vi.fn().mockResolvedValue({ status: 'started' }),
  startReplay: vi.fn().mockResolvedValue({ status: 'started' }),
  stopProcess: vi.fn().mockResolvedValue({ status: 'stopped' }),
  getLeaderServiceStatus: vi.fn().mockResolvedValue({ status: 'stopped' }),
  startLeaderService: vi.fn().mockResolvedValue({ status: 'started' }),
  stopLeaderService: vi.fn().mockResolvedValue({ status: 'stopped' }),
}))

const idle = { mode: 'idle', running: false, pid: null, logs: [] as string[], error: null }

const localConfig = {
  robot: { leader_ip: '1.1.1.1', follower_ip: '2.2.2.2', cameras: {} },
  dataset: { repo_id: 'x/y', num_episodes: 10, episode_time_s: 45, reset_time_s: 15, single_task: 'test', push_to_hub: false },
  train: { dataset_repo_id: 'x/y', policy_type: 'act', output_dir: 'out', job_name: 'j', policy_repo_id: 'p' },
  replay: { repo_id: 'x/y', episode: 0 },
  lerobot_trossen_path: '/tmp',
} as any

const remoteConfig = {
  ...localConfig,
  robot: { ...localConfig.robot, remote_leader: true, remote_leader_host: '10.0.0.99', remote_leader_port: 5555 },
}

describe('ActionPanel', () => {
  it('renders all 4 action cards when idle', () => {
    render(<ActionPanel config={localConfig} status={idle} onAction={() => {}} />)
    expect(screen.getByText('Teleoperate')).toBeInTheDocument()
    expect(screen.getByText('Record')).toBeInTheDocument()
    expect(screen.getByText('Train')).toBeInTheDocument()
    expect(screen.getByText('Replay')).toBeInTheDocument()
  })

  it('shows Stop button when running', () => {
    const running = { mode: 'teleoperate', running: true, pid: 123, logs: [], error: null }
    render(<ActionPanel config={localConfig} status={running} onAction={() => {}} />)
    expect(screen.getByText('Stop')).toBeInTheDocument()
  })

  it('shows Leader Service card in remote mode', () => {
    render(<ActionPanel config={remoteConfig} status={idle} onAction={() => {}} />)
    expect(screen.getByText('Leader Service')).toBeInTheDocument()
  })

  it('does not show Leader Service card in local mode', () => {
    render(<ActionPanel config={localConfig} status={idle} onAction={() => {}} />)
    expect(screen.queryByText('Leader Service')).not.toBeInTheDocument()
  })

  it('shows mode label when process is running', () => {
    const running = { mode: 'record', running: true, pid: 456, logs: [], error: null }
    render(<ActionPanel config={localConfig} status={running} onAction={() => {}} />)
    expect(screen.getByText('Recording')).toBeInTheDocument()
  })
})
