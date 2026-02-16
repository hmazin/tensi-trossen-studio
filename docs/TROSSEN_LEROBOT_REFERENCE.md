# Trossen LeRobot Plugin Reference

Consolidated reference from the [Trossen Robotics Trossen Arm Documentation](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/). Use this when developing TENSI Trossen Studio or integrating with LeRobot.

---

## 1. Setup (LeRobot Installation)

**Source:** [LeRobot Installation Guide](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/setup.html)

1. **Install uv** — [uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
2. **Clone LeRobot:**
   ```bash
   git clone https://github.com/TrossenRobotics/lerobot_trossen.git ~/lerobot_trossen
   ```
3. **Install packages and dependencies:**
   ```bash
   cd ~/lerobot_trossen
   uv sync
   ```
4. **Verify installation:**
   ```bash
   cd ~/lerobot_trossen
   uv pip list | grep lerobot
   ```
5. **Trossen AI Mobile (SLATE) only:** Remove `brltty`, add user to `dialout` group, then log out and back in.

---

## 2. Configuration

**Source:** [Trossen AI Configuration](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/configuration.html)

### Specs to Identify

- **IP address** — Leader/follower arm IPs
- **model_name** — Robot type (e.g. `widowxai_follower_robot`)
- **Camera serial numbers** — For RealSense or indices for OpenCV

Pass specs via `--robot.ip_address`, `--robot.type`, and `--robot.cameras`.

### Config File Locations

- **Follower arm:** `lerobot_trossen/packages/lerobot_robot_trossen/src/lerobot_robot_trossen/`
- **Leader arm:** `lerobot_trossen/packages/lerobot_teleoperation_trossen/src/lerobot_teleoperation_trossen/`

### IP Address

- Default Trossen AI arm IP: `192.168.1.2`
- Arms must be on the same network; use `configure_cleanup`, `set_ip_method`, or `set_manual_ip` demos.

### Camera Serial Numbers

**RealSense:**
```bash
--robot.cameras="{
  wrist: {type: intelrealsense, serial_number_or_name: \"0123456789\", width: 640, height: 480, fps: 30},
  top: {type: intelrealsense, serial_number_or_name: \"1123456789\", width: 640, height: 480, fps: 30}
}"
```

**OpenCV:**
```bash
--robot.cameras="{
  wrist: {type: opencv, index_or_path: 8, width: 640, height: 480, fps: 30},
  top: {type: opencv, index_or_path: 10, width: 640, height: 480, fps: 30}
}"
```

**Find cameras:**
```bash
uv run lerobot-find-cameras realsense   # or: opencv
```

Images are saved to `outputs/captured_images`. Match serial numbers to physical cameras via filenames like `realsense__0123456789.png`.

**Note:** Camera key names vary: `wrist`/`top` (config docs), `cam_left`/`cam_right`/`cam_low`/`cam_high` (some examples). Use a consistent convention.

**Troubleshooting:** If RealSense cameras freeze during recording (bandwidth), move cameras to different USB hubs or PCIe cards.

### WidowXAIFollowerConfig

- `ip_address`, `max_relative_target`, `min_time_to_move_multiplier`, `loop_rate`
- `cameras: dict[str, CameraConfig]`
- `joint_names`: joint_0..joint_5, left_carriage_joint
- `staged_positions`: rad for arm, m for gripper

---

## 3. Teleoperation

**Source:** [Teleoperation](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/teleoperation.html)

### Solo Arm

```bash
uv run lerobot-teleoperate \
  --robot.type=widowxai_follower_robot \
  --robot.ip_address=192.168.1.4 \
  --robot.id=follower \
  --robot.cameras="{cam_left: {type: intelrealsense, serial_number_or_name: \"0123456789\", width: 640, height: 480, fps: 30}, cam_right: {type: intelrealsense, serial_number_or_name: \"0123456789\", width: 640, height: 480, fps: 30}}" \
  --teleop.type=widowxai_leader_teleop \
  --teleop.ip_address=192.168.1.2 \
  --teleop.id=leader \
  --display_data=true
```

### Additional Args

```bash
uv run lerobot-teleoperate --help
```

- `--fps` (int): Frames per second to send
- `--teleop_time_s` (int): Duration in seconds
- `--robot.max_relative_target` (float): Safety limit for target vector (default 5.0); set to `null` to disable
- `--robot.loop_rate` (int): Control loop rate Hz (default 30)

---

## 4. Record Episodes

**Source:** [Record Episodes](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/record_episode.html)

### Hugging Face Login

```bash
huggingface-cli login --token ${HUGGINGFACE_TOKEN} --add-to-git-credential
HF_USER=$(huggingface-cli whoami | head -n 1)
```

### Solo Arm Recording

```bash
uv run lerobot-record \
  --robot.type=widowxai_follower_robot \
  --robot.ip_address=192.168.1.4 \
  --robot.id=follower \
  --robot.cameras="{cam_low: {type: intelrealsense, serial_number_or_name: \"0123456789\", width: 640, height: 480, fps: 30}, cam_high: {type: intelrealsense, serial_number_or_name: \"1123456789\", width: 640, height: 480, fps: 30}}" \
  --teleop.type=widowxai_leader_teleop \
  --teleop.ip_address=192.168.1.2 \
  --teleop.id=leader \
  --display_data=true \
  --dataset.repo_id=${HF_USER}/widowxai-cube-pickup \
  --dataset.episode_time_s=45 \
  --dataset.reset_time_s=15 \
  --dataset.num_episodes=2 \
  --dataset.push_to_hub=true \
  --dataset.single_task="Grab the cube"
```

**Joint units:** Joints 0–5: radians. Joint 6 (gripper): meters.

### Camera FPS Issues

- Increase `--dataset.num_image_writer_threads_per_camera` (e.g. 8)
- Or set `--display_data=false`
- RealSense causing issues → try OpenCV instead

### Recording Configuration

| Param | Type | Description |
|-------|------|-------------|
| `--dataset.repo_id` | str | e.g. `{hf_username}/{dataset_name}` |
| `--dataset.single_task` | str | Task description |
| `--dataset.root` | str/Path | Local storage path |
| `--dataset.fps` | int | FPS (default 30) |
| `--dataset.episode_time_s` | int/float | Episode duration (default 60) |
| `--dataset.reset_time_s` | int/float | Reset phase duration (default 60) |
| `--dataset.num_episodes` | int | Number of episodes (default 50) |
| `--dataset.video` | bool | Encode to video (default True) |
| `--dataset.push_to_hub` | bool | Upload to Hub (default True) |
| `--dataset.num_image_writer_threads_per_camera` | int | Threads per camera (default 4) |
| `--dataset.num_image_writer_processes` | int | Subprocesses for PNG writing (default 0) |

---

## 5. Visualize

**Source:** [Visualize](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/visualize.html)

### Remote (Hugging Face)

Use [Hugging Face visualize space](https://huggingface.co/spaces/lerobot/visualize_dataset) with repo ID: `<username>/<dataset-id>`.

### Local

**Hub dataset:**
```bash
uv run lerobot-dataset-viz --repo-id ${HF_USER}/<dataset-id> --episode-index 0
```

**Local dataset (no upload):**
```bash
uv run lerobot-dataset-viz \
  --repo-id ${HF_USER}/<dataset-id> \
  --root .cache/huggingface/lerobot/${HF_USER}/datasetname/videos \
  --mode local \
  --episode-index 0
```

---

## 6. Replay

**Source:** [Replaying an Episode](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/replay.html)

```bash
uv run lerobot-replay \
  --robot.type=widowxai_follower_robot \
  --robot.ip_address=192.168.1.4 \
  --robot.id=follower \
  --dataset.repo_id=${HF_USER}/<dataset-id> \
  --dataset.episode=0
```

### Replay Configuration

- `--dataset.repo_id` (str): Dataset ID
- `--dataset.episode` (int): Episode index
- `--dataset.root` (str/Path): Local path if not on Hub
- `--dataset.fps` (int): FPS limit (default 30)

---

## 7. Train and Evaluate

**Source:** [Training and Evaluating a Policy](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/train_and_evaluate.html)

### Training

```bash
uv run lerobot-train \
  --dataset.repo_id=${HF_USER}/trossen_ai_solo_test \
  --policy.type=act \
  --output_dir=outputs/train/act_trossen_ai_solo_test \
  --job_name=act_trossen_ai_solo_test \
  --policy.device=cuda \
  --wandb.enable=true \
  --policy.repo_id=${HF_USER}/my_policy
```

- Policy adapts to motors and cameras from the dataset
- Apple Silicon: use `--policy.device=mps`
- Checkpoints: `outputs/train/act_trossen_ai_xxxxx_test/checkpoints/`

### Resume Training

```bash
uv run lerobot-train \
  --config_path=outputs/train/trossen_ai_xxxxxxx_test/checkpoints/last/pretrained_model/train_config.json \
  --resume=true
```

### Evaluation

Use `lerobot-record` with `--policy.path`:

```bash
uv run lerobot-record \
  --robot.type=widowxai_follower_robot \
  --robot.cameras='{up: {type: opencv, index_or_path: 10, ...}, side: {...}}' \
  --robot.id=follower \
  --display_data=false \
  --dataset.repo_id=${HF_USER}/eval_trossen_ai_xxxxxxx_test \
  --dataset.single_task="Grab and handover the red cube" \
  --policy.path=${HF_USER}/my_policy
```

- Policy checkpoint: `outputs/train/act_xxxxx_test/checkpoints/last/pretrained_model` or Hub ID
- Eval dataset prefix: `eval_`
- Smoother motion: `--robot.min_time_to_move_multiplier=6.0` (default 3.0)
- Higher FPS: `--num_image_writer_processes=1`

---

## Quick Reference

| Item | Value |
|------|-------|
| Default arm IP | 192.168.1.2 |
| Camera find | `uv run lerobot-find-cameras realsense` |
| Joint 0–5 units | Radians |
| Joint 6 (gripper) | Meters |
| min_time_to_move | multiplier / fps (recommended 3.0) |

### Source URLs

- [Setup](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/setup.html)
- [Configuration](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/configuration.html)
- [Teleoperation](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/teleoperation.html)
- [Record Episodes](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/record_episode.html)
- [Visualize](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/visualize.html)
- [Replay](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/replay.html)
- [Train and Evaluate](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin/train_and_evaluate.html)
