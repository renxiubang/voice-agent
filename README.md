# 智能体语音对话系统 (Voice Agent Dialogue System)

模块化、全链路流式、全双工的智能体语音对话系统（macOS + Python）

[English Version](README_EN.md)

## 系统架构

```
前端 (Web Audio API) ↔ 网关层 (FastAPI + WebSocket) ↔ 听觉层 (VAD + ASR + 声纹) ↔ 认知层 (LLM) ↔ 发声层 (TTS)
```

## 技术栈

- **网关层**: FastAPI + WebSocket
- **听觉层**: Silero VAD + pyannote.audio + Whisper (pywhispercpp)
- **认知层**: Apple MLX (mlx-lm)
- **发声层**: Piper TTS
- **前端**: Web Audio API + AudioWorklet

## 安装

```bash
# 创建虚拟环境
conda create -n voice-agent python=3.11
conda activate voice-agent

# 安装系统依赖 (macOS)
brew install portaudio espeak

# 安装 Python 依赖
pip install -r requirements.txt
```

## 运行

```bash
# 启动后端服务器
cd /workspace/voice-agent
python -m gateway.server

# 打开前端页面
open frontend/index.html
```

或者使用安装脚本：

```bash
chmod +x install.sh
./install.sh
```

## 配置

编辑 `config.yaml` 调整系统参数。

## 项目结构

```
voice-agent/
├── config.yaml                 # 配置文件
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明 (中文)
├── README_EN.md                # 项目说明 (英文)
├── RUN.md                     # 运行说明
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

## 许可证

MIT

## GitHub 仓库

https://github.com/renxiubang/voice-agent
