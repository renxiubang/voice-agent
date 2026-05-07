# 智能体语音对话系统（macOS）

[英文版本](README.md)

模块化、全链路流式、全双工的智能体语音对话系统（macOS + Python）

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

## 配置

编辑 `config.yaml` 调整系统参数。

## 项目结构

```
voice-agent/
├── config.yaml                 # 配置文件
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明
├── gateway/                    # 网关层
├── auditory/                   # 听觉层
├── cognition/                  # 认知层
├── tts/                        # 发声层
├── core/                       # 核心模块
├── frontend/                   # 前端
└── utils/                      # 工具函数
```

## 许可证

MIT
