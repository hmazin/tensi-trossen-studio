import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfigForm } from './ConfigForm'

vi.mock('../api/client', () => ({
  saveConfig: vi.fn().mockResolvedValue({ status: 'saved', config: {} }),
}))

const baseConfig = {
  robot: {
    leader_ip: '192.168.1.2',
    follower_ip: '192.168.1.5',
    remote_leader: false,
    remote_leader_host: '10.0.0.99',
    remote_leader_port: 5555,
    use_top_camera_only: true,
    cameras: {
      wrist: { type: 'intelrealsense', serial_number_or_name: 'WRIST', width: 640, height: 480, fps: 30 },
      top: { type: 'intelrealsense', serial_number_or_name: 'TOP', width: 640, height: 480, fps: 30 },
    },
  },
  dataset: { repo_id: '', num_episodes: 0, episode_time_s: 0, reset_time_s: 0, single_task: '', push_to_hub: false },
  train: { dataset_repo_id: '', policy_type: '', output_dir: '', job_name: '', policy_repo_id: '' },
  replay: { repo_id: '', episode: 0 },
  lerobot_trossen_path: '/home/user/lerobot',
} as any

describe('ConfigForm', () => {
  it('has translate-x-full when closed (off-screen)', () => {
    render(<ConfigForm config={baseConfig} onConfigChange={() => {}} open={false} onClose={() => {}} />)
    const heading = screen.getByText('Settings')
    const panel = heading.closest('[class*="translate-x"]')
    expect(panel?.className).toContain('translate-x-full')
  })

  it('renders Settings heading when open', () => {
    render(<ConfigForm config={baseConfig} onConfigChange={() => {}} open={true} onClose={() => {}} />)
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('shows follower IP field', () => {
    render(<ConfigForm config={baseConfig} onConfigChange={() => {}} open={true} onClose={() => {}} />)
    const input = screen.getByDisplayValue('192.168.1.5')
    expect(input).toBeInTheDocument()
  })

  it('shows remote leader fields when checkbox is checked', () => {
    const remoteCfg = { ...baseConfig, robot: { ...baseConfig.robot, remote_leader: true } }
    render(<ConfigForm config={remoteCfg} onConfigChange={() => {}} open={true} onClose={() => {}} />)
    expect(screen.getByDisplayValue('10.0.0.99')).toBeInTheDocument()
    expect(screen.getByDisplayValue('5555')).toBeInTheDocument()
  })

  it('shows leader IP when not remote', () => {
    render(<ConfigForm config={baseConfig} onConfigChange={() => {}} open={true} onClose={() => {}} />)
    expect(screen.getByDisplayValue('192.168.1.2')).toBeInTheDocument()
  })

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn()
    render(<ConfigForm config={baseConfig} onConfigChange={() => {}} open={true} onClose={onClose} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('has Save Settings button', () => {
    render(<ConfigForm config={baseConfig} onConfigChange={() => {}} open={true} onClose={() => {}} />)
    expect(screen.getByText('Save Settings')).toBeInTheDocument()
  })
})
