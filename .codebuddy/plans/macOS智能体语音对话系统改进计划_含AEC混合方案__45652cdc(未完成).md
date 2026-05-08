---
name: macOS智能体语音对话系统改进计划（含AEC混合方案）
overview: 改进现有语音对话系统，实现 macOS 系统级 AEC（后端用 pyobjc + Core Audio，前端用浏览器 AEC）、pyannote.audio 声纹识别、双讲检测与打断机制，保持 MLX-Audio + Kokoro TTS，打造全双工流式语音对话体验。
---

## 产品概述

在 macOS 环境下搭建一套智能体语音对话系统，采用模块化级联架构与全链路流式处理，实现全双工流式语音对话。系统仅识别特定注册人员（Target Speaker），并通过 macOS 系统级回声消除（AEC）避免 TTS 播放时的回声干扰。

## 核心功能

- **前端**：使用 JS/Web Audio API 实现音频采集与播放，通过 WebSocket 与后端通信，实时显示对话内容与系统状态，支持打断机制。
- **网关层（FastAPI + WebSocket）**：负责与前端建立长连接，双向传输音频流与文本消息，支持打断信号传输。
- **听觉层（VAD + ASR + 声纹识别）**：使用 Silero VAD 检测语音活动，使用 pyannote.audio 进行目标说话人声纹识别，仅当声纹匹配成功时启动 pywhispercpp（Whisper C++）进行语音识别。
- **认知层（LLM）**：接收文本，通过 MLX 流式接口调用大模型生成回复。
- **发声层（TTS）**：将大模型流式文本实时拼接，送入 MLX-Audio + Kokoro TTS 引擎生成音频流并立即推回前端。
- **macOS 系统级 AEC（混合方案）**：
- **前端采集（默认）**：使用浏览器 AEC（方案 C），实现简单可靠
- **后端采集（可选）**：使用 pyobjc 调用 Core Audio API（方案 B），提供系统级 AEC
- 用户可通过配置选择采集方式
- **双讲检测**：当 TTS 正在播放时，暂时暂停声纹比对与 Whisper 转录，避免误识别。
- **打断机制（Barge-in）**：当用户开始说话时，立即停止当前的 TTS 播放，清空播放队列，实现自然的交互体验。
- **音频处理流程**：音频流先经过 AEC（前端采集用浏览器 AEC，后端采集用 Core Audio AEC），再进行声纹比对，最后交给 Whisper 转录。

## 技术栈选择

- **后端主体**：Python 3.9+，使用 asyncio 异步机制串联各模块。
- **网关层**：FastAPI + WebSocket（uvicorn 作为 ASGI 服务器）。
- **听觉层**：
- VAD：Silero VAD（torch.hub.load('snakers4/silero-vad')）
- ASR：pywhispercpp（Whisper C++ 实现，支持 GGML/GGUF 模型）
- 声纹识别：pyannote.audio（提取说话人嵌入向量，计算余弦相似度）
- 音频采集（前端方式）：浏览器 AEC（通过 `getUserMedia({ echoCancellation: true })`）
- 音频采集（后端方式）：pyobjc + Core Audio API（系统级 AEC）
- **认知层**：MLX-LM（本地模式）或 OpenAI 兼容 API（流式接口）
- **发声层**：MLX-Audio + Kokoro TTS（支持流式文本转音频，保持现有实现）
- **前端**：HTML5、CSS3、JavaScript（ES6+）、Web Audio API、AudioWorklet
- **配置与依赖管理**：PyYAML（配置文件）、pip（Python 包管理）

## 实现方法

### 1. 模块化级联架构与全链路流式处理

- 将系统分为四个独立模块（网关层、听觉层、认知层、发声层），通过 asyncio 队列（audio_queue、text_queue、llm_queue、tts_queue）串联。
- 每个模块作为独立的异步任务运行，通过队列进行数据传递，实现解耦与流式处理。
- 听觉层内部流程：audio_queue → AEC（系统级或浏览器级） → 声纹识别 → （若匹配成功）VAD → ASR → text_queue。
- 认知层流程：text_queue → LLM 流式生成 → llm_queue（逐 token 传递）。
- 发声层流程：llm_queue → 文本拼接与分句 → MLX-Audio + Kokoro TTS 流式合成 → tts_queue → 网关层 → 前端播放。

### 2. macOS Voice Processing I/O 回声消除（AEC）混合方案

**方案 C：前端浏览器 AEC（默认方案）**

- 修改 `frontend/voice_interface.js`，在 `getUserMedia()` 中启用 `echoCancellation: true`
- 优点：实现简单，浏览器原生支持，兼容性好
- 缺点：只能消除从浏览器播放的声音的回声

**方案 B：pyobjc + Core Audio API（可选方案，为高级用户提供更强的系统级 AEC）**

- 创建 `auditory/core_audio_processor.py`，使用 pyobjc 调用 Core Audio API
- 实现 Voice Processing I/O 配置，启用系统级 AEC
- 提供降级方案（如果 pyobjc 实现失败，自动回退到前端采集）

**用户配置选择**：
在 `config.yaml` 中添加配置：

```
audio:
  input_mode: "frontend"  # 或 "backend"
  # frontend: 前端采集（浏览器 AEC）
  # backend: 后端采集（pyobjc + Core Audio AEC）
```

**实施策略**：

1. 默认使用前端采集（方案 C），因为实现简单可靠
2. 可选使用后端采集（方案 B），为高级用户提供系统级 AEC
3. 两种采集方式共用同一套听觉层处理逻辑

### 3. pyobjc + Core Audio API 实施细节（方案 B）

**安装 pyobjc**：

```
pip install pyobjc
```

**核心代码思路**（创建 `auditory/core_audio_processor.py`）：

```python
import AVFoundation as AV
from Foundation import NSObject

class CoreAudioProcessor:
    """使用 pyobjc 调用 Core Audio API，启用 Voice Processing I/O"""
    
    def __init__(self):
        self.audio_engine = None
        self.input_node = None
        self.audio_queue = None
        
    async def init_core_audio(self):
        """初始化 Core Audio，启用 Voice Processing I/O"""
        # 创建 AVAudioEngine
        self.audio_engine = AV.AVAudioEngine()
        
        # 获取输入节点
        self.input_node = self.audio_engine.inputNode()
        
        # 配置 Voice Processing I/O
        # 设置 AVAudioUnitVoiceProcessing
        # 需要编写 Objective-C 桥接代码或使用现有的 Python 封装
        
        # 启动音频引擎
        self.audio_engine.startAndReturnError_(None)
        
    def audio_callback(self, buffer):
        """音频回调函数"""
        # 处理音频数据
        # 放入 audio_queue
        pass
```

**注意**：pyobjc 文档较少，调试可能较困难。需要提供降级方案。

### 4. 前端浏览器 AEC 实施细节（方案 C）

**修改 frontend/voice_interface.js**：

```javascript
async startRecording() {
    try {
        // 启用浏览器 AEC
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,  // 启用浏览器回声消除
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        
        // 创建音频源节点
        this.microphoneSource = this.audioContext.createMediaStreamSource(stream);
        
        // ... 后续处理
    }
}
```

**优点**：

- 实现简单，不需要修改后端代码
- 浏览器原生支持，兼容性好

**缺点**：

- 只能消除从浏览器播放的声音的回声
- 如果后端直接播放音频（不通过浏览器），则无法消除

### 5. Python GIL 与实时音频优化

- **问题**：sounddevice 的回调运行在独立的 C 线程中，不能直接调用 await。
- **解决方案**：
- 回调内不做重活（如网络请求、重计算）
- 如果声纹比对（pyannote）太慢导致音频卡顿，需要将音频放入 asyncio.Queue，由另一个协程处理
- 回调只负责投递数据（put to queue）
- 使用 `loop.call_soon_threadsafe()` 或 `asyncio.run_coroutine_threadsafe()` 从回调中投递数据到异步队列
- **修改 auditory/audio_processor.py**：
- 修改 `audio_callback()`，只负责投递数据到线程安全队列
- 创建独立的协程处理音频数据（声纹比对、VAD、ASR）
- 避免 GIL 问题和回调阻塞
- **支持两种采集方式**：前端采集（WebSocket 接收音频）和后端采集（麦克风直接采集）

### 6. 目标说话人声纹识别（Target-Speaker ASR）

- 使用 pyannote.audio 的 SpeakerVerificationModel 提取声纹嵌入向量（embedding）。
- 实现声纹注册功能：允许用户通过录制音频样本注册目标说话人，将提取的嵌入向量保存到本地数据库（如 JSON 文件或 SQLite）。
- 实现声纹比对功能：对实时音频提取嵌入向量，与注册声纹计算余弦相似度，仅当相似度超过阈值（如 0.7）时，才将音频交给 Whisper 进行转录。
- 升级现有的 `auditory/speaker_recognition.py`，从简化版基础特征升级到 pyannote.audio 专业模型。
- **注意性能**：pyannote 可能较慢，需要异步处理，避免阻塞音频回调。

### 7. 双讲检测与处理

- 在编排器（core/orchestrator.py）中维护 TTS 播放状态（如 is_tts_playing 标志位）。
- 当 TTS 开始播放时，设置 is_tts_playing = True，听觉层在检测到该标志位后，暂时暂停声纹比对与 Whisper 转录。
- 当 TTS 播放完成时，设置 is_tts_playing = False，恢复听觉层处理。
- 可通过 asyncio.Event 或共享状态变量实现标志位的跨模块传递。

### 8. 打断机制（Barge-in）

- **需求**：当用户开始说话时，应立即停止当前的 TTS 播放。
- **实现方案**：
- 在 core/orchestrator.py 中添加 barge_in_event = asyncio.Event()
- 在 auditory_layer 中检测到用户语音时，向 vocal_layer