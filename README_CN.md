# 智能体语音对话系统（macOS）

模块化、全链路流式、全双工的智能体语音对话系统（macOS + Python）

[English Version](README.md)

## 系统架构

```
前端 (Web Audio API) ↔ 网关层 (FastAPI + WebSocket) ↔ 听觉层 (VAD + ASR + 声纹) ↔ 认知层 (LLM) ↔ 发声层 (TTS)
```

## 技术栈

- **网关层**: FastAPI + WebSocket（全双工通信）
- **听觉层**: Silero VAD + pyannote.audio + Whisper (pywhispercpp)
- **认知层**: Apple MLX (mlx-lm)
- **发声层**: MLX-Audio + Kokoro TTS（**真正流式输出**）
- **前端**: Web Audio API + AudioWorklet

## 特性

- ✅ **真正流式 TTS**: MLX-Audio + Kokoro 支持逐块生成音频，无需等待完整文本
- ✅ **全链路流式**: 从 ASR → LLM → TTS 全程流式处理
- ✅ **全双工通信**: WebSocket 并行收发，支持打断和实时交互
- ✅ **Apple Silicon 优化**: MLX 框架充分利用 M1/M2/M3/M4 芯片性能
- ✅ **中文支持**: Kokoro 模型原生支持中文语音合成

## 安装

### 系统要求

- macOS (Apple Silicon) - 必需（用于 Apple MLX）
- Python 3.11+
- Homebrew (用于系统依赖)

### 安装依赖

```bash
# 创建虚拟环境
conda create -n voice-agent python=3.11
conda activate voice-agent

# 安装系统依赖 (macOS)
brew install portaudio espeak

# 安装 Python 依赖
pip install -r requirements.txt
```

### 或使用安装脚本

```bash
chmod +x install.sh
./install.sh
```

## 配置

编辑 `config.yaml` 调整系统参数：

```yaml
# 网关层配置
gateway:
  host: "0.0.0.0"
  port: 8000

# 听觉层配置
auditory:
  sample_rate: 16000
  vad_threshold: 0.5
  similarity_threshold: 0.7

# 认知层配置
cognition:
  llm_model: "mistralai/Mistral-7B-Instruct-v0.3"
  max_tokens: 512
  temperature: 0.7

# 发声层配置 (MLX-Audio + Kokoro)
tts:
  model: "mlx-community/Kokoro-82M-bf16"
  voice: "zf_xiaobei"  # 中文女声 (可选: zm_yunxi 男声)
  lang_code: "z"  # z = 中文
  speed: 1.0  # 语速
  sample_rate: 24000  # Kokoro 输出 24kHz
  buffer_size: 20  # 字符数（遇到标点或缓冲区满时触发 TTS）
```

## 运行

### 启动系统

1. **启动后端服务器**:

```bash
cd /workspace/voice-agent
source venv/bin/activate
python main.py
```

2. **打开前端页面**:

在浏览器中打开:

```
http://localhost:8000
```

或直接打开文件:

```bash
open frontend/index.html
```

### 使用语音智能体

1. 点击"开始对话"按钮
2. 允许浏览器访问麦克风
3. 对麦克风说话
4. 系统会自动识别语音、生成回复并播放 TTS 音频
5. 点击"停止对话"结束

## 项目结构

```
voice-agent/
├── config.yaml                 # 配置文件
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明 (中文)
├── README_EN.md                # 项目说明 (英文)
├── gateway/                    # 网关层
│   ├── server.py              # FastAPI + WebSocket 服务器
│   └── connection_manager.py  # WebSocket 连接管理
├── auditory/                   # 听觉层
│   ├── vad.py                # Silero VAD
│   ├── speaker_recognition.py # pyannote.audio 声纹识别
│   ├── asr.py                # Whisper ASR
│   └── audio_processor.py    # 音频采集和处理
├── cognition/                  # 认知层
│   └── llm.py                # MLX LLM 推理
├── tts/                        # 发声层 (流式输出)
│   └── mlx_tts.py            # MLX-Audio + Kokoro TTS
├── core/                       # 核心模块
│   ├── orchestrator.py        # 异步编排器
│   └── queues.py              # asyncio.Queue 定义
├── frontend/                   # 前端
│   ├── index.html             # 网页界面
│   ├── voice_interface.js     # AudioWorklet + WebSocket 客户端
│   └── audio_worklet.js      # AudioWorklet 处理器
└── utils/                      # 工具函数
    ├── config_loader.py        # 配置加载器
    └── audio_utils.py         # 音频处理工具
```

## 核心特性

### 1. 真正流式 TTS

使用 MLX-Audio + Kokoro 实现真正的流式输出：

```python
# TTS 引擎本身是迭代器，逐块生成音频
async for audio_chunk in tts_engine.synthesize_stream(text):
    # 立即发送音频块（无需等待完整合成）
    await websocket.send_bytes(audio_chunk)
```

### 2. 全链路流式处理

整个管道支持流式：
- 音频采集 → 流式传输到后端
- ASR 识别 → 流式传输文本到 LLM
- LLM 生成 → 流式传输 token 到 TTS
- TTS 合成 → 流式传输音频到前端

这最小化了延迟，提供了流畅的用户体验。

### 3. 全双工通信

WebSocket 连接支持同时双向音频流：
- 前端可以在接收 TTS 音频时发送音频
- 后端可以在发送 TTS 音频时处理音频

### 4. 声纹识别

系统支持声纹注册和识别：
- 注册说话人的声纹
- 只识别和处理已注册说话人的语音
- 防止未授权用户触发语音智能体

## 测试

### 测试所有模块

```bash
python test_modules.py
```

### 测试单独模块

```bash
# 测试配置加载器
python utils/config_loader.py

# 测试 VAD 模型
python auditory/vad.py

# 测试 ASR 模型
python auditory/asr.py

# 测试声纹识别模型
python auditory/speaker_recognition.py

# 测试 TTS 模型 (MLX-Audio + Kokoro)
python tts/mlx_tts.py
```

## 故障排除

### 1. mlx-lm 安装失败

**错误**: `pip install mlx-lm` 失败

**解决方案**: 确保你在 macOS (Apple Silicon) 上，并安装了 Xcode 命令行工具。

```bash
xcode-select --install
```

### 2. pyannote.audio 模型下载失败

**错误**: 从 HuggingFace Hub 下载模型失败

**解决方案**: 设置 HuggingFace Hub 镜像或使用代理。

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. 音频设备未找到

**错误**: `sounddevice.PortAudioError: No Default Output Device Available`

**解决方案**: 检查音频设备连接，或在代码中指定设备 ID。

```python
import sounddevice as sd
print(sd.query_devices())  # 查看可用设备
```

### 4. MLX-Audio 模型下载失败

**错误**: 从 HuggingFace Hub 下载 Kokoro 模型失败

**解决方案**: 设置 HuggingFace Hub 镜像。

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 工作原理

### 音频处理管道

1. **音频采集**:
   - 前端使用 `MediaRecorder` (或 `AudioWorklet`) 采集麦克风音频
   - 音频格式: PCM 16-bit, 16kHz, mono

2. **VAD 检测**:
   - Silero VAD 检测语音活动
   - 过滤静音和噪声

3. **声纹识别**:
   - pyannote.audio 提取说话人嵌入
   - 与已注册说话人比较
   - 只在识别到已注册说话人时继续

4. **语音识别**:
   - Whisper (pywhispercpp) 将语音转为文本
   - 支持中文和英文

5. **LLM 推理**:
   - mlx-lm 在 Apple Silicon 上运行 LLM
   - 流式生成 (token by token)

6. **TTS 合成**:
   - MLX-Audio + Kokoro TTS 将文本转为语音
   - **真正流式合成** (逐块生成音频)

7. **音频播放**:
   - 前端通过 WebSocket 接收 TTS 音频
   - 使用 Web Audio API 播放音频

### 异步编排器

`Orchestrator` 类管理整个管道：

```python
# 初始化模块
await orchestrator.initialize_modules()

# 启动异步循环
await asyncio.gather(
    orchestrator.auditory_loop(),   # VAD + ASR
    orchestrator.cognition_loop(),   # LLM
    orchestrator.tts_loop()          # TTS (流式)
)
```

### 模块通信

模块通过 `asyncio.Queue` 通信：

```
audio_queue  →  text_queue  →  llm_queue  →  tts_queue
   (bytes)        (str)          (str)          (bytes)
```

## 性能优化

### 延迟优化

- **流式处理**: LLM 生成 token 的同时 TTS 合成音频
- **缓冲区管理**: TTS 缓冲区大小可调（默认: 20 字符）
- **模型量化**: 使用量化模型加速推理

### 内存优化

- **音频压缩**: PCM 16-bit 格式
- **队列大小限制**: 防止内存溢出
- **模型卸载**: 不使用时卸载模型

## 中文声音选项

Kokoro 模型支持多种中文声音：

| 声音 ID | 类型 | 说明 |
|---------|------|------|
| `zf_xiaobei` | 女声 | 默认声音 |
| `zm_yunxi` | 男声 | - |
| `zf_...` | 女声 | 共 55 种女声 |
| `zm_...` | 男声 | 共 45 种男声 |

配置方法：

```yaml
tts:
  voice: "zm_yunxi"  # 改为男声
```

## 许可证

MIT

## GitHub 仓库

https://github.com/renxiubang/voice-agent

## 致谢

- [Silero VAD](https://github.com/snakers4/silero-vad) - 语音活动检测
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - 声纹识别
- [Whisper](https://github.com/openai/whisper) - 语音识别
- [mlx-lm](https://github.com/ml-explore/mlx-examples) - Apple Silicon 上的 LLM 推理
- [MLX-Audio](https://github.com/Blaizzy/mlx-audio) - MLX 音频处理（TTS）
- [Kokoro TTS](https://github.com/ardorleo/kokoro-tts-zh) - 轻量级中文 TTS
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - 音频处理
