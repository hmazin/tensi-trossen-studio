import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBar } from './StatusBar'

vi.mock('../api/client', () => ({
  getLeaderServiceStatus: vi.fn().mockResolvedValue({ status: 'running' }),
}))

const idle = { mode: 'idle', running: false, pid: null, logs: [] as string[], error: null }

const localConfig = {
  robot: {
    leader_ip: '192.168.1.2',
    follower_ip: '192.168.1.5',
    cameras: {},
  },
  dataset: { repo_id: '', num_episodes: 0, episode_time_s: 0, reset_time_s: 0, single_task: '', push_to_hub: false },
  train: { dataset_repo_id: '', policy_type: '', output_dir: '', job_name: '', policy_repo_id: '' },
  replay: { repo_id: '', episode: 0 },
  lerobot_trossen_path: '',
} as any

const remoteConfig = {
  ...localConfig,
  robot: {
    ...localConfig.robot,
    remote_leader: true,
    remote_leader_host: '10.0.0.99',
    remote_leader_port: 5555,
  },
}

describe('StatusBar', () => {
  it('renders the app title', () => {
    render(<StatusBar config={localConfig} status={idle} onSettingsClick={() => {}} />)
    expect(screen.getByText('TENSI Trossen Studio')).toBeInTheDocument()
  })

  it('shows Idle when not running', () => {
    render(<StatusBar config={localConfig} status={idle} onSettingsClick={() => {}} />)
    expect(screen.getByText('Idle')).toBeInTheDocument()
  })

  it('shows Teleoperating when running', () => {
    const running = { mode: 'teleoperate', running: true, pid: 123, logs: [], error: null }
    render(<StatusBar config={localConfig} status={running} onSettingsClick={() => {}} />)
    expect(screen.getByText('Teleoperating')).toBeInTheDocument()
  })

  it('shows follower IP in local mode', () => {
    render(<StatusBar config={localConfig} status={idle} onSettingsClick={() => {}} />)
    expect(screen.getByText('192.168.1.5')).toBeInTheDocument()
  })

  it('shows Leader Svc in remote mode', () => {
    render(<StatusBar config={remoteConfig} status={idle} onSettingsClick={() => {}} />)
    expect(screen.getByText('Leader Svc')).toBeInTheDocument()
  })

  it('calls onSettingsClick when gear icon is clicked', () => {
    const onClick = vi.fn()
    render(<StatusBar config={localConfig} status={idle} onSettingsClick={onClick} />)
    screen.getByTitle('Settings').click()
    expect(onClick).toHaveBeenCalledOnce()
  })
})
