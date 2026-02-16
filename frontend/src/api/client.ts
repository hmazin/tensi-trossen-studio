const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const CAMERA_API_BASE = import.meta.env.VITE_CAMERA_API_BASE || API_BASE;

async function fetchApi(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function fetchCameraApi(path: string, options?: RequestInit) {
  const res = await fetch(`${CAMERA_API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function getCameraStreamUrl(cameraKey: string): string {
  return `${CAMERA_API_BASE}/cameras/stream/${cameraKey}`;
}

export interface AppConfig {
  robot: {
    leader_ip: string;
    follower_ip: string;
    use_top_camera_only?: boolean;
    remote_leader?: boolean;
    remote_leader_host?: string;
    remote_leader_port?: number;
    cameras: Record<string, { type: string; serial_number_or_name: string; width: number; height: number; fps: number }>;
  };
  dataset: {
    repo_id: string;
    num_episodes: number;
    episode_time_s: number;
    reset_time_s: number;
    single_task: string;
    push_to_hub: boolean;
  };
  train: {
    dataset_repo_id: string;
    policy_type: string;
    output_dir: string;
    job_name: string;
    policy_repo_id: string;
  };
  replay: {
    repo_id: string;
    episode: number;
  };
  lerobot_trossen_path: string;
}

export interface ProcessStatus {
  mode: string;
  running: boolean;
  pid: number | null;
  logs: string[];
  error: string | null;
}

export async function getConfig(): Promise<AppConfig> {
  return fetchApi('/config');
}

export async function saveConfig(config: AppConfig): Promise<{ status: string; config: AppConfig }> {
  return fetchApi('/config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export async function startTeleoperate(displayData = true, useTopCameraOnly?: boolean): Promise<{ status: string; mode: string }> {
  const params = new URLSearchParams();
  params.set('display_data', String(displayData));
  if (useTopCameraOnly === true) params.set('use_top_camera_only', 'true');
  return fetchApi(`/teleoperate/start?${params}`, { method: 'POST' });
}

export async function stopTeleoperate(): Promise<{ status: string }> {
  return fetchApi('/teleoperate/stop', { method: 'POST' });
}

export async function startRecord(params?: {
  repo_id?: string;
  num_episodes?: number;
  episode_time_s?: number;
  single_task?: string;
  push_to_hub?: boolean;
  use_top_camera_only?: boolean;
}): Promise<{ status: string; mode: string }> {
  const search = new URLSearchParams();
  if (params?.repo_id) search.set('repo_id', params.repo_id);
  if (params?.num_episodes != null) search.set('num_episodes', String(params.num_episodes));
  if (params?.episode_time_s != null) search.set('episode_time_s', String(params.episode_time_s));
  if (params?.single_task) search.set('single_task', params.single_task);
  if (params?.push_to_hub != null) search.set('push_to_hub', String(params.push_to_hub));
  if (params?.use_top_camera_only === true) search.set('use_top_camera_only', 'true');
  return fetchApi(`/record/start?${search}`, { method: 'POST' });
}

export async function stopRecord(): Promise<{ status: string }> {
  return fetchApi('/record/stop', { method: 'POST' });
}

export async function startTrain(params?: {
  dataset_repo_id?: string;
  policy_type?: string;
  output_dir?: string;
  job_name?: string;
}): Promise<{ status: string; mode: string }> {
  const search = new URLSearchParams();
  if (params?.dataset_repo_id) search.set('dataset_repo_id', params.dataset_repo_id);
  if (params?.policy_type) search.set('policy_type', params.policy_type);
  if (params?.output_dir) search.set('output_dir', params.output_dir);
  if (params?.job_name) search.set('job_name', params.job_name);
  return fetchApi(`/train/start?${search}`, { method: 'POST' });
}

export async function stopTrain(): Promise<{ status: string }> {
  return fetchApi('/train/stop', { method: 'POST' });
}

export async function startReplay(params?: { repo_id?: string; episode?: number }): Promise<{ status: string; mode: string }> {
  const search = new URLSearchParams();
  if (params?.repo_id) search.set('repo_id', params.repo_id);
  if (params?.episode != null) search.set('episode', String(params.episode));
  return fetchApi(`/replay/start?${search}`, { method: 'POST' });
}

export async function stopReplay(): Promise<{ status: string }> {
  return fetchApi('/replay/stop', { method: 'POST' });
}

export async function stopProcess(): Promise<{ status: string }> {
  return fetchApi('/process/stop', { method: 'POST' });
}

export async function getProcessStatus(): Promise<ProcessStatus> {
  return fetchApi('/process/status');
}

export interface CameraDetectResult {
  detected: { serial: string; name: string }[];
  configured?: Record<string, string>;
  error?: string;
  message?: string;
}

export interface CameraStatusResult {
  cameras: Record<
    string,
    {
      status: string;
      error_type?: string;
      message?: string;
      details?: { serial: string; error: string };
    }
  >;
}

export async function detectCameras(): Promise<CameraDetectResult> {
  return fetchCameraApi('/cameras/detect');
}

export async function getCameraStatus(): Promise<CameraStatusResult> {
  return fetchCameraApi('/cameras/status');
}

export async function shutdownCameras(): Promise<{ status: string; cameras_released: string[] }> {
  return fetchCameraApi('/cameras/shutdown', { method: 'POST' });
}

// Leader Service (remote PC2) management
export interface LeaderServiceStatus {
  status: 'running' | 'stopped' | 'unknown';
  host?: string;
  port?: number;
}

export async function getLeaderServiceStatus(): Promise<LeaderServiceStatus> {
  return fetchApi('/leader-service/status');
}

export async function startLeaderService(): Promise<{ status: string; message?: string; host?: string; port?: number; pid?: string }> {
  return fetchApi('/leader-service/start', { method: 'POST' });
}

export async function stopLeaderService(): Promise<{ status: string }> {
  return fetchApi('/leader-service/stop', { method: 'POST' });
}

export async function getLeaderServiceLogs(lines?: number): Promise<{ logs: string[]; error?: string }> {
  const params = lines ? `?lines=${lines}` : '';
  return fetchApi(`/leader-service/logs${params}`);
}
