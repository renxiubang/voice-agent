# 运行说明

## 1. 安装依赖

### 1.1 使用安装脚本 (macOS)

```bash
cd /workspace/voice-agent
chmod +x install.sh
./install.sh
```

### 1.2 手动安装

#### 创建虚拟环境

```bash
cd /workspace/voice-agent
python3 -m venv venv
source venv/bin/activate
```

#### 安装系统依赖 (macOS)

```bash
# 安装 Homebrew (如果未安装)
#/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 portaudio (用于 sounddevice)
brew install portaudio

# 安装 espeak (用于 Piper TTS)
brew install espeak
```

#### 安装 Python 依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. 配置

编辑 `config.yaml` 调整系统参数：

```yaml
# 网关层配置
gateway:
  host: "0.0.0.0"
  port: 8800  # WebSocket 端口

# 听觉层配置
auditory:
  sample_rate: 16000  # 音频采样率
  vad_threshold: 0.5   # VAD 阈值
  similarity_threshold: 0.7  # 声纹识别相似度阈值

# 认知层配置
cognition:
  llm_model: "mistralai/Mistral-7B-Instruct-v0.3"
  max_tokens: 512
  temperature: 0.7

# 发声层配置
tts:
  model: "zh_CN-huayan-medium"
  sample_rate: 22050
```

## 3. 运行

### 3.1 启动后端服务器

```bash
cd /workspace/voice-agent
source venv/bin/activate
python main.py
```

服务器将在 `http://localhost:8800` 启动。

### 3.2 打开前端页面

在浏览器中打开：

```
http://localhost:8800
```

或者使用文件方式打开：

```bash
open frontend/index.html
```

## 4. 使用

1. 点击"开始对话"按钮
2. 允许浏览器访问麦克风
3. 对麦克风说话
4. 系统会自动识别语音、生成回复、并播放 TTS 音频
5. 点击"停止对话"按钮结束

## 5. 测试各个模块

### 5.1 测试配置加载器

```bash
python -c "from utils.config_loader import load_config; config = load_config(); print(config)"
```

### 5.2 测试队列管理器

```bash
python utils/config_loader.py
```

### 5.3 测试 VAD 模型

```bash
python auditory/vad.py
```

### 5.4 测试 ASR 模型

```bash
python auditory/asr.py
```

### 5.5 测试声纹识别模型

```bash
python auditory/speaker_recognition.py
```

### 5.6 测试 TTS 模型

```bash
python tts/piper_tts.py
```

### 5.7 测试所有模块

```bash
python test_modules.py
```

## 6. 手动下载 Whisper 模型（国内用户）

如果在国内环境运行，从 Hugging Face 下载 Whisper 模型可能会超时。可以使用以下方法手动下载模型：

### 6.1 从 ModelScope 下载

1. **安装 ModelScope SDK**:
   ```bash
   pip install modelscope
   ```

2. **下载 Whisper 模型**:
   ```python
   from modelscope.hub.snapshot_download import snapshot_download
   
   # 下载 medium.en 模型（约 1.4GB）
   model_dir = snapshot_download(
       'zhongguoa/ggml-medium.en.bin',
       cache_dir='~/.cache',
       revision='master'
   )
   print(f'模型下载到: {model_dir}')
   ```

3. **复制模型到 pywhispercpp 目录**:
   ```bash
   # 创建目标目录
   mkdir -p ~/Library/Application\ Support/pywhispercpp/models
   
   # 复制模型文件
   cp ~/.cache/zhongguoa/ggml-medium.en.bin/*/ggml-medium.en.bin ~/Library/Application\ Support/pywhispercpp/models/
   ```

4. **验证模型文件**:
   ```bash
   ls -lh ~/Library/Application\ Support/pywhispercpp/models/ggml-medium.en.bin
   # 应该显示约 1.4GB 的文件
   ```

5. **配置 config.yaml**:
   ```yaml
   auditory:
     asr_model: "medium.en"  # pywhispercpp 会自动使用本地模型
   ```

### 6.2 支持的模型

pywhispercpp 官方支持的模型：
- `tiny.en`, `tiny`
- `base.en`, `base`
- `small.en`, `small`
- `medium.en`, `medium`
- `large-v1`, `large`

---

## 7. 常见问题

### 7.1 mlx-lm 安装失败

**错误**: `pip install mlx-lm` 失败

**解决方案**: 确保在 macOS (Apple Silicon) 上运行，并且已安装 Xcode Command Line Tools。

```bash
xcode-select --install
```

### 7.2 pyannote.audio 下载模型失败

**错误**: `HuggingFace Hub` 下载模型失败

**解决方案**: 设置 HuggingFace Hub 镜像或者使用代理。

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 7.3 Piper TTS 未安装

**错误**: `piper: command not found`

**解决方案**: 安装 Piper TTS。

```bash
pip install piper-tts
```

### 7.4 音频设备未找到

**错误**: `sounddevice.PortAudioError: No Default Output Device Available`

**解决方案**: 检查音频设备连接，或者在代码中指定设备 ID。

```python
import sounddevice as sd
print(sd.query_devices())  # 查看可用设备
```

## 7. 项目结构

```
voice-agent/
├── config.yaml                 # 配置文件
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明
├── RUN.md                     # 运行说明 (本文件)
├── install.sh                 # 安装脚本
├── main.py                    # 主入口
├── test_modules.py            # 模块测试脚本
│
├── gateway/                    # 网关层
│   ├── server.py              # FastAPI + WebSocket 服务器
│   └── connection_manager.py  # WebSocket 连接管理
│
├── auditory/                   # 听觉层
│   ├── vad.py                # Silero VAD
│   ├── speaker_recognition.py # pyannote.audio 声纹识别
│   ├── asr.py                # Whisper ASR
│   └── audio_processor.py    # 音频采集和预处理
│
├── cognition/                  # 认知层
│   └── llm.py                # mlx-lm LLM 推理
│
├── tts/                        # 发声层
│   └── piper_tts.py          # Piper TTS 引擎
│
├── core/                       # 核心模块
│   ├── orchestrator.py        # 异步编排器
│   └── queues.py              # asyncio.Queue 定义
│
├── frontend/                   # 前端
│   ├── index.html             # Web 页面
│   ├── voice_interface.js     # AudioWorklet + WebSocket 客户端
│   └── audio_worklet.js      # AudioWorklet 处理器
│
└── utils/                      # 工具函数
    ├── config_loader.py        # 配置加载
    └── audio_utils.py         # 音频处理工具
```

## 8. 许可证

MIT
