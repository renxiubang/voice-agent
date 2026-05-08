---
name: macOS智能体语音对话系统改进计划（含避坑指南）
overview: 改进现有语音对话系统，实现 macOS Voice Processing I/O AEC、pyannote.audio 声纹识别、双讲检测与打断机制，保持 MLX-Audio + Kokoro TTS，打造全双工流式语音对话体验。
design:
  architecture:
    framework: html
    component: shadcn
  styleKeywords:
    - 现代科技感
    - 深色主题
    - 蓝色渐变
    - 音频可视化
    - 实时反馈
    - 微动画
  fontSystem:
    fontFamily: PingFang SC, Helvetica Neue, Arial, sans-serif
    heading:
      size: 24px
      weight: 600
    subheading:
      size: 18px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#1890FF"
      - "#40A9FF"
      - "#69C0FF"
    background:
      - "#141414"
      - "#1F1F1F"
      - "#2C2C2C"
    text:
      - "#FFFFFF"
      - "#D9D9D9"
      - "#8C8C8C"
    functional:
      - "#52C41A"
      - "#FF4D4F"
      - "#FAAD14"
todos:
  - id: implement-macos-aec
    content: 实现 macOS Voice Processing I/O AEC，修改 auditory/audio_processor.py，添加设备查找与配置逻辑
    status: pending
  - id: optimize-audio-callback
    content: 优化音频回调，使用线程安全队列与异步队列，避免 GIL 问题，修改 auditory/audio_processor.py
    status: pending
    dependencies:
      - implement-macos-aec
  - id: upgrade-speaker-recognition
    content: 升级声纹识别到 pyannote.audio，修改 auditory/speaker_recognition.py，实现专业声纹提取与比对
    status: pending
    dependencies:
      - optimize-audio-callback
  - id: implement-double-talk-detection
    content: 实现双讲检测逻辑，修改 core/orchestrator.py，添加 TTS 播放状态检测
    status: pending
    dependencies:
      - upgrade-speaker-recognition
  - id: implement-barge-in
    content: 实现打断机制（Barge-in），修改 core/orchestrator.py、tts/mlx_tts.py、frontend/voice_interface.js
    status: pending
    dependencies:
      - implement-double-talk-detection
  - id: adjust-auditory-flow
    content: 调整听觉层处理流程，确保 AEC → 声纹比对 → ASR 顺序，修改 core/orchestrator.py
    status: pending
    dependencies:
      - implement-barge-in
  - id: improve-frontend-ui
    content: 改进前端界面，添加对话显示与音频可视化，修改 frontend/index.html 和 frontend/voice_interface.js
    status: pending
    dependencies:
      - adjust-auditory-flow
  - id: update-config-and-dependencies
    content: 更新配置文件与依赖，修改 config.yaml 和 requirements.txt，添加 pyannote.audio 配置
    status: pending
    dependencies:
      - improve-frontend-ui
  - id: test-and-debug
    content: 测试与调试系统，确保各模块正常工作，进行性能优化，验证 macOS AEC、双讲检测、打断机制等功能
    status: pending
    dependencies:
      - update-config-and-dependencies
---

## 产品概述

在 macOS 环境下搭建一套智能体语音对话系统，采用模块化级联架构与全链路流式处理，实现全双工流式语音对话。系统仅识别特定注册人员（Target Speaker），并通过 macOS 系统级回声消除（AEC）避免 TTS 播放时的回声干扰。

## 核心功能

- **前端**：使用 JS/Web Audio API 实现音频采集与播放，通过 WebSocket 与后端通信，实时显示对话内容与系统状态，支持打断机制。
- **网关层（FastAPI + WebSocket）**：负责与前端建立长连接，双向传输音频流与文本消息，支持打断信号传输。
- **听觉层（VAD + ASR + 声纹识别）**：使用 Silero VAD 检测语音活动，使用 pyannote.audio 进行目标说话人声纹识别，仅当声纹匹配成功时启动 pywhispercpp（Whisper C++）进行语音识别。
- **认知层（LLM）**：接收文本，通过 MLX 流式接口调用大模型生成回复。
- **发声层（TTS）**：将大模型流式文本实时拼接，送入 MLX-Audio + Kokoro TTS 引擎生成音频流并立即推回前端。
- **macOS 系统级 AEC**：通过 macOS Voice Processing I/O 消除回声，避免 TTS 播放声音被麦克风录入。
- **双讲检测**：当 TTS 正在播放时，暂时暂停声纹比对与 Whisper 转录，避免误识别。
- **打断机制（Barge-in）**：当用户开始说话时，立即停止当前的 TTS 播放，清空播放队列，实现自然的交互体验。
- **音频处理流程**：音频流先经过 macOS Voice Processing I/O 消除回声，再进行声纹比对，最后交给 Whisper 转录。

## 技术栈选择

- **后端主体**：Python 3.9+，使用 asyncio 异步机制串联各模块。
- **网关层**：FastAPI + WebSocket（uvicorn 作为 ASGI 服务器）。
- **听觉层**：
- VAD：Silero VAD（torch.hub.load('snakers4/silero-vad')）
- ASR：pywhispercpp（Whisper C++ 实现，支持 GGML/GGUF 模型）
- 声纹识别：pyannote.audio（提取说话人嵌入向量，计算余弦相似度）
- 音频采集：sounddevice（配置 macOS Voice Processing I/O 设备）
- **认知层**：MLX-LM（本地模式）或 OpenAI 兼容 API（流式接口）
- **发声层**：MLX-Audio + Kokoro TTS（支持流式文本转音频，保持现有实现）
- **前端**：HTML5、CSS3、JavaScript（ES6+）、Web Audio API、AudioWorklet
- **配置与依赖管理**：PyYAML（配置文件）、pip（Python 包管理）

## 实现方法

### 1. 模块化级联架构与全链路流式处理

- 将系统分为四个独立模块（网关层、听觉层、认知层、发声层），通过 asyncio 队列（audio_queue、text_queue、llm_queue、tts_queue）串联。
- 每个模块作为独立的异步任务运行，通过队列进行数据传递，实现解耦与流式处理。
- 听觉层内部流程：audio_queue → macOS AEC（系统级） → 声纹识别 → （若匹配成功）VAD → ASR → text_queue。
- 认知层流程：text_queue → LLM 流式生成 → llm_queue（逐 token 传递）。
- 发声层流程：llm_queue → 文本拼接与分句 → MLX-Audio + Kokoro TTS 流式合成 → tts_queue → 网关层 → 前端播放。

### 2. macOS Voice Processing I/O 回声消除（AEC）

- 使用 sounddevice.query_devices() 查找 macOS 系统中支持 Voice Processing I/O 的音频设备（通常名称为 "Voice Processing" 或包含 "Voice Processing" 字样）。
- 如果找不到，指导用户创建聚合设备（Aggregate Device）：

1. 打开 "音频 MIDI 设置"
2. 左下角 +号 → 创建聚合设备
3. 勾选你的麦克风和输出设备，并确保勾选 "启用回声消除"
4. 在代码中使用 sd.query_devices() 找到这个聚合设备的索引

- 配置 sounddevice.default.device 为该设备，确保音频采集时自动进行系统级 AEC。
- 在 auditory/audio_processor.py 中实现 enable_echo_cancellation() 方法，完成设备查找与配置。
- 注意：macOS AEC 会引入约 20-50ms 延迟，需在系统中进行延迟补偿（可通过调整音频缓冲区大小或添加延迟校准逻辑）。

### 3. Python GIL 与实时音频优化

- **问题**：sounddevice 的回调运行在独立的 C 线程中，不能直接调用 await。
- **解决方案**：
- 回调内不做重活（如网络请求、重计算）
- 如果声纹比对（pyannote）太慢导致音频卡顿，需要将音频放入 asyncio.Queue，由另一个协程处理
- 回调只负责投递数据（put to queue）
- 使用 loop.call_soon_threadsafe() 或 asyncio.run_coroutine_threadsafe() 从回调中投递数据到异步队列
- **修改 auditory/audio_processor.py**：
- 修改 audio_callback()，只负责投递数据到线程安全队列
- 创建独立的协程处理音频数据（声纹比对、VAD、ASR）
- 避免 GIL 问题和回调阻塞

### 4. 目标说话人声纹识别（Target-Speaker ASR）

- 使用 pyannote.audio 的 SpeakerVerificationModel 提取声纹嵌入向量（embedding）。
- 实现声纹注册功能：允许用户通过录制音频样本注册目标说话人，将提取的嵌入向量保存到本地数据库（如 JSON 文件或 SQLite）。
- 实现声纹比对功能：对实时音频提取嵌入向量，与注册声纹计算余弦相似度，仅当相似度超过阈值（如 0.7）时，才将音频交给 Whisper 进行转录。
- 升级现有的 auditory/speaker_recognition.py，从简化版基础特征升级到 pyannote.audio 专业模型。
- **注意性能**：pyannote 可能较慢，需要异步处理，避免阻塞音频回调。

### 5. 双讲检测与处理

- 在编排器（core/orchestrator.py）中维护 TTS 播放状态（如 is_tts_playing 标志位）。
- 当 TTS 开始播放时，设置 is_tts_playing = True，听觉层在检测到该标志位后，暂时暂停声纹比对与 Whisper 转录。
- 当 TTS 播放完成时，设置 is_tts_playing = False，恢复听觉层处理。
- 可通过 asyncio.Event 或共享状态变量实现标志位的跨模块传递。

### 6. 打断机制（Barge-in）

- **需求**：当用户开始说话时，应立即停止当前的 TTS 播放。
- **实现方案**：
- 在 core/orchestrator.py 中添加 barge_in_event = asyncio.Event()
- 在 auditory_layer 中检测到用户语音时，向 vocal_layer 发送一个"停止"信号
- 清空 audio_out_queue（TTS 播放队列）
- 在前端立即停止当前音频播放
- **修改点**：
- core/orchestrator.py：添加 barge_in_event = asyncio.Event()
- auditory/：检测到用户语音开始时，设置 barge_in_event
- tts/：监听 barge_in_event，停止当前 TTS 合成和播放
- frontend/：接收打断信号，停止音频播放
- gateway/server.py：可能需要添加打断信号传输

### 7. MLX-Audio + Kokoro TTS 集成（保持现有实现）

- 现有 tts/mlx_tts.py 已实现 MLX-Audio + Kokoro TTS 的流式输出（synthesize_stream() 方法）。
- 需要确保与编排器的集成正确，优化流式输出性能。
- 添加打断机制支持（监听 barge_in_event）。
- 确保音频格式与前端播放匹配（PCM 16-bit，正确采样率）。

### 8. 音频处理流程调整

- 修改 core/orchestrator.py 中的 auditory_loop() 方法，确保音频处理顺序为：

1. 从 audio_queue 取出音频数据。
2. （可选）进行额外的音频预处理（如降噪，但 macOS AEC 已处理回声）。
3. 进行声纹识别，若不匹配则跳过后续步骤。
4. 进行 VAD 检测，若检测到语音则进行 ASR。
5. 将 ASR 结果（文本）放入 text_queue。

- 在听觉层中添加双讲检测逻辑，根据 TTS 播放状态决定是否进行声纹识别与 ASR。
- 在听觉层中添加打断检测逻辑，当用户开始说话时触发打断机制。

## 架构设计

### 系统架构图

```mermaid
graph TD
    A[前端（浏览器）] -->|WebSocket 音频流/文本/打断信号| B[网关层（FastAPI + WebSocket）]
    B -->|音频流| C[听觉层（VAD + ASR + 声纹识别）]
    C -->|文本| D[认知层（LLM）]
    D -->|流式文本 Token| E[发声层（MLX-Audio + Kokoro TTS）]
    E -->|音频流/打断信号| B
    B -->|音频流| A
    
    subgraph macOS 系统
        F[Voice Processing I/O（AEC）]
    end
    C -->|音频采集| F
    
    G[用户输入（麦克风）] -->|音频| F
    E -->|音频输出| H[扬声器]
    H -->|回声| G
```

### 模块交互流程

1. 前端通过 WebSocket 发送音频流到网关层。
2. 网关层将音频流放入 audio_queue。
3. 听觉层从 audio_queue 取出音频，进行以下处理：

- 若 TTS 正在播放（双讲检测），则暂停处理。
- 否则，进行声纹识别，若匹配成功则进行 VAD 检测。
- 若 VAD 检测到语音，则触发打断机制（如果 TTS 正在播放）。
- 若 VAD 检测到语音且未打断，则进行 ASR 转录，将文本放入 text_queue。

4. 认知层从 text_queue 取出文本，调用 LLM 生成流式回复，将 token 依次放入 llm_queue。
5. 发声层从 llm_queue 取出 token，拼接为文本后送入 TTS 引擎，生成音频流并放入 tts_queue。
6. 网关层从 tts_queue 取出音频流，通过 WebSocket 发送到前端。
7. 前端播放音频，并通过 Web Audio API 进行音频可视化。
8. 当用户开始说话时，听觉层检测到语音，触发打断机制，停止当前 TTS 播放。

## 目录结构

```
voice-agent/
├── config.yaml                          # [MODIFY] 配置文件，添加 pyannote.audio、双讲检测、打断机制配置
├── requirements.txt                     # [MODIFY] Python 依赖，添加 pyannote.audio
├── main.py                              # [MODIFY] 主入口，启动编排器
├── auditory/
│   ├── __init__.py                     # [KEEP] 模块初始化
│   ├── audio_processor.py              # [MODIFY] 实现 macOS Voice Processing I/O AEC，优化音频回调
│   ├── vad.py                          # [KEEP] Silero VAD 模型（无需修改）
│   ├── speaker_recognition.py          # [MODIFY] 升级到 pyannote.audio
│   └── asr.py                          # [KEEP] pywhispercpp ASR（无需修改）
├── cognition/
│   ├── __init__.py                     # [KEEP] 模块初始化
│   └── llm.py                          # [KEEP] LLM 模型（无需修改）
├── core/
│   ├── __init__.py                     # [KEEP] 模块初始化
│   ├── orchestrator.py                 # [MODIFY] 实现双讲检测逻辑、打断机制
│   └── queues.py                       # [KEEP] asyncio 队列定义（无需修改）
├── gateway/
│   ├── __init__.py                     # [KEEP] 模块初始化
│   ├── server.py                       # [MODIFY] 添加打断信号传输支持
│   └── connection_manager.py           # [KEEP] WebSocket 连接管理（无需修改）
├── tts/
│   ├── __init__.py                     # [KEEP] 模块初始化
│   └── mlx_tts.py                     # [MODIFY] 优化 MLX-Audio + Kokoro TTS 集成，添加打断支持
├── frontend/
│   ├── index.html                      # [MODIFY] 改进界面设计，添加对话显示与音频可视化
│   ├── voice_interface.js              # [MODIFY] 改进前端逻辑，添加打断机制支持
│   └── audio_worklet.js                # [KEEP] AudioWorklet 处理器（无需修改）
└── utils/
    ├── __init__.py                     # [KEEP] 工具模块初始化
    └── config_loader.py                # [KEEP] 配置文件加载（无需修改）
```

## 关键代码结构

### 1. 音频处理器 AEC 配置与回调优化（auditory/audio_processor.py）

```python
class AudioProcessor:
    """音频采集与预处理，支持 macOS Voice Processing I/O AEC"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = "int16"
        self.blocksize = 1024
        self.stream = None
        self.callback = None
        
        # 音频缓冲区（线程安全）
        self.audio_buffer = queue.Queue()  # 使用标准库 queue.Queue，线程安全
        
        # 异步队列（用于协程处理）
        self.async_queue = None  # 将在 init() 中初始化
        
        # 事件循环引用
        self.loop = None
    
    async def init(self, config: dict):
        """初始化音频处理器"""
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        self.dtype = config.get("dtype", "int16")
        
        # 保存事件循环引用
        self.loop = asyncio.get_event_loop()
        
        # 创建异步队列
        self.async_queue = asyncio.Queue()
        
        # 打印可用的音频设备
        logger.info("可用的音频设备:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            logger.info(f"  {i}: {device['name']} (输入: {device['max_input_channels']}, 输出: {device['max_output_channels']})")
        
        logger.info("音频处理器初始化完成")
    
    def audio_callback(self, indata, frames, time, status):
        """音频流回调函数（运行在 C 线程）"""
        if status:
            logger.warning(f"音频流状态: {status}")
        
        # ✅ 正确：放入线程安全的队列，由另一个协程处理
        self.audio_buffer.put(indata.copy())
        
        # 使用 asyncio.run_coroutine_threadsafe() 将数据投递到异步队列
        asyncio.run_coroutine_threadsafe(
            self.async_queue.put(indata.copy()),
            self.loop
        )
    
    async def start_stream(self):
        """启动音频流"""
        logger.info("正在启动音频流...")
        
        try:
            # 创建输入流
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=self.audio_callback
            )
            
            # 启动流
            self.stream.start()
            logger.info("音频流已启动")
            
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            raise
    
    async def enable_echo_cancellation(self) -> bool:
        """配置 macOS Voice Processing I/O 设备，启用系统级 AEC"""
        devices = sd.query_devices()
        
        # 查找包含 "Voice Processing" 的设备
        for i, device in enumerate(devices):
            if "Voice Processing" in device['name'] and device['max_input_channels'] > 0:
                sd.default.device = i
                logger.info(f"已启用 macOS Voice Processing I/O AEC: {device['name']}")
                return True
        
        # 如果找不到，提示用户创建聚合设备
        logger.warning("未找到 Voice Processing 设备！")
        logger.warning("请按以下步骤创建聚合设备：")
        logger.warning("1. 打开 '音频 MIDI 设置'")
        logger.warning("2. 左下角 +号 -> 创建聚合设备")
        logger.warning("3. 勾选你的麦克风和输出设备，并确保勾选 '启用回声消除'")
        logger.warning("4. 重新运行程序")
        
        return False
    
    async def get_audio_data(self):
        """获取音频数据（从异步队列）"""
        return await self.async_queue.get()
```

### 2. 声纹识别接口（auditory/speaker_recognition.py）

```python
class SpeakerRecognitionModel:
    """使用 pyannote.audio 的目标说话人声纹识别模型"""
    
    def __init__(self, config: dict):
        self.config = config
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        self.model = None
        self.speaker_db: Dict[str, np.ndarray] = {}
        
    async def load_model(self):
        """加载 pyannote.audio 说话人验证模型"""
        from pyannote.audio import SpeakerVerificationModel
        self.model = SpeakerVerificationModel("speechbrain/spkrec-ecapa-voxceleb")
        logger.info("pyannote.audio 声纹识别模型加载成功")
        
    async def register_speaker(self, speaker_id: str, audio_samples: list):
        """注册目标说话人，提取并保存声纹嵌入向量"""
        embeddings = []
        for audio in audio_samples:
            embedding = self.model.compute_embedding(audio)
            embeddings.append(embedding)
        
        # 计算平均 embedding
        avg_embedding = np.mean(embeddings, axis=0)
        
        # 保存到数据库
        self.speaker_db[speaker_id] = avg_embedding
        self._save_db()
        
        logger.info(f"说话人 {speaker_id} 注册成功")
        
    async def recognize(self, audio: np.ndarray) -> str:
        """识别说话人，返回 speaker_id 或 'unknown'"""
        if len(self.speaker_db) == 0:
            return "target_speaker"
        
        # 提取音频的 embedding
        embedding = self.model.compute_embedding(audio)
        
        # 与数据库中的所有说话人比较
        max_similarity = -1
        recognized_speaker = "unknown"
        
        for speaker_id, db_embedding in self.speaker_db.items():
            # 计算余弦相似度
            similarity = self._cosine_similarity(embedding, db_embedding)
            
            if similarity > max_similarity:
                max_similarity = similarity
                recognized_speaker = speaker_id
        
        # 如果相似度超过阈值，返回识别结果
        if max_similarity >= self.similarity_threshold:
            return recognized_speaker
        else:
            return "unknown"
```

### 3. 双讲检测与打断机制（core/orchestrator.py）

```python
class Orchestrator:
    """异步编排器，管理各模块与双讲检测状态"""
    
    def __init__(self, config: dict):
        # 添加 TTS 播放状态标志位
        self.is_tts_playing = False  # TTS 播放状态标志位
        self.barge_in_event = asyncio.Event()  # 打断事件
        
        # 获取队列
        self.audio_queue = get_audio_queue()
        self.text_queue = get_text_queue()
        self.llm_queue = get_llm_queue()
        self.tts_queue = get_tts_queue()
        
    async def set_tts_playing(self, playing: bool):
        """设置 TTS 播放状态，供发声层调用"""
        self.is_tts_playing = playing
        
        # 如果开始播放，清空打断事件
        if playing:
            self.barge_in_event.clear()
        else:
            # 如果播放完成，设置打断事件（如果没有打断）
            if not self.barge_in_event.is_set():
                self.barge_in_event.set()
        
    async def trigger_barge_in(self):
        """触发打断机制"""
        logger.info("触发打断机制")
        
        # 设置打断事件
        self.barge_in_event.set()
        
        # 清空 TTS 队列
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.info("打断机制已触发，TTS 队列已清空")
        
    async def auditory_loop(self):
        """听觉层主循环，包含双讲检测逻辑与打断检测"""
        logger.info("听觉层循环启动")
        
        while self.running:
            try:
                # 从 audio_queue 取出音频
                audio_data = await self.audio_queue.get()
                
                # 转换为 numpy 数组
                import numpy as np
                audio_float32 = np.frombuffer(audio_data, dtype=np.int16).astype(
                    np.float32
                ) / 32768.0
                
                # VAD 检测
                is_speech = await self.vad_model.is_speech(audio_float32)
                
                if is_speech:
                    # 如果 TTS 正在播放，触发打断机制
                    if self.is_tts_playing:
                        await self.trigger_barge_in()
                        continue
                    
                    # 声纹识别
                    speaker_id = await self.speaker_model.recognize(audio_float32)
                    
                    # 如果是目标说话人，进行 ASR
                    if speaker_id == "target_speaker":
                        text = await self.asr_model.transcribe(audio_float32)
                        
                        # 放入 text_queue
                        await self.text_queue.put(text)
                        logger.info(f"识别文本: {text}")
                
            except Exception as e:
                logger.error(f"听觉层错误: {e}")
                await asyncio.sleep(0.1)
```

## 设计风格

采用现代科技感设计风格，以深色主题为主，搭配蓝色渐变与青色灯光效果，营造智能、流畅的语音对话体验。界面布局清晰，重点突出对话内容与系统状态，添加微动画与过渡效果提升用户体验。

## 页面布局设计

### 1. 顶部导航栏

- 显示系统标题（如"智能语音对话助手"）与连接状态指示灯（绿色表示已连接，红色表示未连接）。
- 包含设置按钮（用于配置声纹注册、音频设备等）。

### 2. 对话内容区域

- 使用气泡式对话框，区分用户消息（右侧，蓝色气泡）与智能体消息（左侧，灰色气泡）。
- 消息包含发送者头像、文本内容、时间戳。
- 支持自动滚动到底部，显示最新消息。

### 3. 音频波形可视化区域

- 在对话内容区域上方或下方，添加音频波形可视化组件。
- 使用 Web Audio API 的 AnalyserNode 获取音频频率数据，通过 Canvas 绘制实时波形。
- 区分输入音频（麦克风）与输出音频（TTS 播放）的波形，使用不同颜色表示。

### 4. 系统状态显示区域

- 显示当前系统状态，包括：
- VAD 状态（检测到语音/静音）。
- 声纹识别结果（目标说话人/未知）。
- TTS 播放状态（播放中/空闲）。
- 双讲检测状态（激活/未激活）。
- 打断机制状态（激活/未激活）。
- 使用图标与文字结合的方式，清晰展示状态信息。

### 5. 控制按钮区域

- 包含开始对话、停止对话、声纹注册等按钮。
- 按钮设计采用圆角、渐变背景与悬停效果，提升交互体验。

## 交互设计

- 点击"开始对话"按钮后，前端与网关层建立 WebSocket 连接，开始音频采集与处理。
- 实时显示对话内容与系统状态，用户可直观了解系统运行情况。
- 声纹注册功能：点击"声纹注册"按钮，引导用户录制音频样本，完成声纹注册后提示成功。
- 音频波形实时更新，增强视觉反馈，让用户了解音频输入输出情况。
- 打断机制：当用户开始说话时，系统立即停止当前 TTS 播放，并清空播放队列，实现自然的交互体验。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 探索代码库，了解现有实现细节，辅助定位需要修改的文件与函数。
- Expected outcome: 获取准确的代码结构信息，确保计划与现有代码兼容。