/**
 * 语音接口 - WebSocket 客户端 + AudioWorklet + VAD
 */

class VoiceInterface {
    /**
     * 初始化语音接口
     * @param {string} websocketUrl - WebSocket 服务器 URL
     */
    constructor(websocketUrl = "ws://localhost:8800/ws") {
        this.websocketUrl = websocketUrl;
        this.websocket = null;
        this.audioContext = null;
        this.audioWorkletNode = null;
        this.microphoneSource = null;
        this.mediaStream = null;
        this.isRecording = false;
        this.isPlaying = false;
        
        // 回声消除：播放目标
        this.playbackDestination = null;
        
        // 音频播放队列
        this.audioQueue = [];
        this.isProcessingAudioQueue = false;
        
        // VAD 状态
        this.vadReady = false;
        this.isSpeaking = false;
        
        // 音频可视化
        this.analyser = null;
        this.canvasCtx = null;
        this.isVisualizing = false;
        
        // 绑定 UI 元素
        this.statusEl = document.getElementById("status");
        this.conversationEl = document.getElementById("conversation");
        this.audioStatusEl = document.getElementById("audio-status");
        this.btnStart = document.getElementById("btn-start");
        this.btnStop = document.getElementById("btn-stop");
        
        // 绑定按钮事件
        this.btnStart.addEventListener("click", () => this.start());
        this.btnStop.addEventListener("click", () => this.stop());
        
        // 更新状态
        this.updateStatus("ready");
    }

    /**
     * 开始语音对话
     */
    async start() {
        try {
            // 初始化音频上下文
            await this.initAudioContext();
            
            // 连接 WebSocket
            await this.connectWebSocket();
            
            // 开始录音
            await this.startRecording();
            
            // 更新 UI
            this.btnStart.disabled = true;
            this.btnStop.disabled = false;
            this.updateStatus("connected");
            
        } catch (error) {
            console.error("启动失败:", error);
            this.updateAudioStatus("启动失败: " + error.message);
        }
    }

    /**
     * 停止语音对话
     */
    async stop() {
        try {
            // 停止录音
            await this.stopRecording();
            
            // 关闭 WebSocket
            await this.disconnectWebSocket();
            
            // 关闭音频上下文
            await this.closeAudioContext();
            
            // 更新 UI
            this.btnStart.disabled = false;
            this.btnStop.disabled = true;
            this.updateStatus("disconnected");
            
        } catch (error) {
            console.error("停止失败:", error);
        }
    }

    /**
     * 初始化音频上下文
     */
    async initAudioContext() {
        // 创建音频上下文
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000,
            channelCount: 1
        });
        
        // 等待 AudioContext 恢复 (需要用户手势)
        if (this.audioContext.state === "suspended") {
            await this.audioContext.resume();
        }
        
        // 创建播放目标 (用于回声消除参考)
        this.playbackDestination = this.audioContext.createMediaStreamDestination();
        
        // 创建音频分析器 (用于音频可视化)
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 2048;
        this.analyser.smoothingTimeConstant = 0.8;
        
        // 获取 Canvas 上下文
        const canvas = document.getElementById("audioCanvas");
        this.canvasCtx = canvas.getContext("2d");
        
        // 加载 AudioWorklet 处理器
        await this.audioContext.audioWorklet.addModule("audio_worklet.js");
        
        console.log("音频上下文初始化完成 (含音频可视化)");
    }

    /**
     * 关闭音频上下文
     */
    async closeAudioContext() {
        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
            this.playbackDestination = null;
            console.log("音频上下文已关闭");
        }
    }

    /**
     * 连接 WebSocket
     */
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            this.websocket = new WebSocket(this.websocketUrl);
            
            this.websocket.onopen = () => {
                console.log("WebSocket 连接成功");
                resolve();
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event);
            };
            
            this.websocket.onerror = (error) => {
                console.error("WebSocket 错误:", error);
                reject(error);
            };
            
            this.websocket.onclose = () => {
                console.log("WebSocket 连接关闭");
                this.updateStatus("disconnected");
            };
        });
    }

    /**
     * 断开 WebSocket 连接
     */
    async disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
            console.log("WebSocket 连接已断开");
        }
    }

    /**
     * 处理 WebSocket 消息
     * @param {MessageEvent} event - WebSocket 消息事件
     */
    handleWebSocketMessage(event) {
        if (event.data instanceof Blob) {
            // 接收音频数据 (Binary frame)
            event.data.arrayBuffer().then((buffer) => {
                this.queueAudio(buffer);
            });
        } else if (typeof event.data === "string") {
            // 接收文本消息
            console.log("收到文本消息:", event.data);
        }
    }

    /**
     * 将音频数据加入播放队列
     * @param {ArrayBuffer} buffer - 音频数据 (PCM 16-bit)
     */
    queueAudio(buffer) {
        this.audioQueue.push(buffer);
        
        if (!this.isProcessingAudioQueue) {
            this.processAudioQueue();
        }
    }

    /**
     * 处理音频播放队列
     */
    async processAudioQueue() {
        if (this.audioQueue.length === 0) {
            this.isProcessingAudioQueue = false;
            this.updateAudioStatus("播放完成");
            return;
        }
        
        this.isProcessingAudioQueue = true;
        this.updateAudioStatus("正在播放...");
        
        const buffer = this.audioQueue.shift();
        
        try {
            // 播放音频
            await this.playAudio(buffer);
        } catch (error) {
            console.error("播放音频失败:", error);
        }
        
        // 处理下一个音频
        this.processAudioQueue();
    }

    /**
     * 播放音频 (改进回声消除 + 音频可视化)
     * @param {ArrayBuffer} buffer - 音频数据 (PCM 16-bit)
     */
    async playAudio(buffer) {
        // 将 PCM 16-bit 转换为 Float32
        const int16Array = new Int16Array(buffer);
        const float32Array = new Float32Array(int16Array.length);
        
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }
        
        // 创建 AudioBuffer
        const audioBuffer = this.audioContext.createBuffer(
            1,  // 单声道
            float32Array.length,
            24000  // 采样率 (与 Kokoro TTS 输出一致)
        );
        
        audioBuffer.getChannelData(0).set(float32Array);
        
        // 创建 BufferSource
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        
        // 连接到音频分析器 (用于可视化)
        if (this.analyser) {
            source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
        }
        
        // 改进回声消除：连接到播放目标 (提供回声参考)
        if (this.playbackDestination) {
            source.connect(this.playbackDestination);
        }
        
        // 同时连接到扬声器 (实际播放)
        source.connect(this.audioContext.destination);
        
        // 等待播放完成
        return new Promise((resolve) => {
            source.onended = () => {
                // 断开连接
                if (this.analyser) {
                    source.disconnect(this.analyser);
                    this.analyser.disconnect(this.audioContext.destination);
                }
                if (this.playbackDestination) {
                    source.disconnect(this.playbackDestination);
                }
                source.disconnect(this.audioContext.destination);
                resolve();
            };
            
            source.start();
        });
    }

    /**
     * 开始录音
     */
    async startRecording() {
        try {
            // 获取麦克风权限 (启用回声消除)
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,  // 启用浏览器回声消除
                    noiseSuppression: true,   // 噪声抑制
                    autoGainControl: true     // 自动增益
                }
            });
            
            // 保存流引用，用于停止时关闭
            this.mediaStream = stream;
            
            // 创建音频源节点
            this.microphoneSource = this.audioContext.createMediaStreamSource(stream);
            
            // 创建 AudioWorklet 节点，捕获原始 PCM 音频 + VAD
            this.audioWorkletNode = new AudioWorkletNode(
                this.audioContext,
                "audio-capture-processor",  // 对应 audio_worklet.js 中注册的名称
                {
                    processorOptions: {
                        sampleRate: 16000,
                        bufferSize: 4096
                    }
                }
            );
            
            // 监听 AudioWorklet 发送的消息
            this.audioWorkletNode.port.onmessage = (event) => {
                this.handleAudioWorkletMessage(event.data);
            };
            
            // 连接音频节点
            this.microphoneSource.connect(this.audioWorkletNode);
            // 注意：不连接到 destination，避免回声
            
            // 通知 AudioWorklet 开始录音
            this.audioWorkletNode.port.postMessage({
                type: 'startRecording'
            });
            
            this.isRecording = true;
            
            console.log("录音已开始 (AudioWorklet + VAD)");
            this.updateAudioStatus("正在录音...");
            
        } catch (error) {
            console.error("开始录音失败:", error);
            throw error;
        }
    }

    /**
     * 处理 AudioWorklet 消息
     * @param {Object} message - 消息对象
     */
    handleAudioWorkletMessage(message) {
        switch (message.type) {
            case 'vadReady':
                this.vadReady = true;
                console.log('VAD 已就绪');
                break;
                
            case 'speechStart':
                this.isSpeaking = true;
                console.log('检测到语音开始');
                this.updateAudioStatus("检测到语音...");
                
                // 打断机制：检测到用户语音时，停止音频播放
                if (this.isProcessingAudioQueue || this.audioQueue.length > 0) {
                    console.log("🚨 检测到用户语音，触发打断！");
                    this.stopAudioPlayback();
                }
                break;
                
            case 'speechEnd':
                this.isSpeaking = false;
                console.log('检测到语音结束');
                this.updateAudioStatus("语音结束，处理中...");
                break;
                
            case 'audioData':
                // 接收到完整的说话段音频数据
                this.sendAudioData(message.data);
                break;
        }
    }

    /**
     * 停止录音
     */
    async stopRecording() {
        if (this.isRecording) {
            // 通知 AudioWorklet 停止录音
            if (this.audioWorkletNode) {
                this.audioWorkletNode.port.postMessage({
                    type: 'stopRecording'
                });
            }
            
            // 断开音频节点连接
            if (this.microphoneSource) {
                this.microphoneSource.disconnect();
                this.microphoneSource = null;
            }
            
            if (this.audioWorkletNode) {
                this.audioWorkletNode.disconnect();
                this.audioWorkletNode = null;
            }
            
            // 关闭麦克风流
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach((track) => track.stop());
                this.mediaStream = null;
            }
            
            this.isRecording = false;
            this.vadReady = false;
            this.isSpeaking = false;
            
            console.log("录音已停止");
            this.updateAudioStatus("录音已停止");
        }
    }

    /**
     * 发送音频数据到 WebSocket
     * @param {ArrayBuffer} audioBuffer - 音频数据 (Int16Array buffer)
     */
    sendAudioData(audioBuffer) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(audioBuffer);
            console.log(`发送音频数据: ${audioBuffer.byteLength} 字节`);
        }
    }

    /**
     * 停止音频播放（用于打断机制）
     */
    stopAudioPlayback() {
        console.log("🚨 打断：停止音频播放");
        
        // 清空音频队列
        this.audioQueue = [];
        
        // 停止当前播放（如果存在）
        if (this.audioContext && this.audioContext.state === "running") {
            // 暂停音频上下文
            this.audioContext.suspend().then(() => {
                console.log("音频播放已暂停");
                // 恢复音频上下文（准备下一次播放）
                setTimeout(() => {
                    this.audioContext.resume();
                }, 100);
            });
        }
        
        this.updateAudioStatus("已打断，停止播放");
    }

    /**
     * 更新连接状态
     * @param {string} status - 状态 ("connected", "disconnected", "ready")
     */
    updateStatus(status) {
        if (status === "connected") {
            this.statusEl.className = "status connected";
            this.statusEl.textContent = "已连接";
        } else if (status === "disconnected") {
            this.statusEl.className = "status disconnected";
            this.statusEl.textContent = "未连接";
        } else {
            this.statusEl.className = "status";
            this.statusEl.textContent = "准备就绪";
        }
    }

    /**
     * 更新音频状态
     * @param {string} status - 状态描述
     */
    updateAudioStatus(status) {
        this.audioStatusEl.textContent = status;
        
        if (status.includes("播放")) {
            this.audioStatusEl.className = "audio-status playing";
        } else if (status.includes("语音")) {
            this.audioStatusEl.className = "audio-status speaking";
        } else {
            this.audioStatusEl.className = "audio-status";
        }
    }

    /**
     * 添加对话消息到界面
     * @param {string} speaker - 说话人 ("user" or "agent")
     * @param {string} text - 消息文本
     */
    addMessage(speaker, text) {
        const messageEl = document.createElement("div");
        messageEl.className = `message ${speaker}`;
        
        messageEl.innerHTML = `
            <div class="speaker">${speaker === "user" ? "你" : "智能体"}</div>
            <div class="text">${text}</div>
        `;
        
        this.conversationEl.appendChild(messageEl);
        
        // 滚动到底部
        this.conversationEl.scrollTop = this.conversationEl.scrollHeight;
    }

    /**
     * 绘制音频可视化
     */
    drawAudioVisualization() {
        if (!this.analyser || !this.canvasCtx) {
            return;
        }

        // 获取 Canvas 元素
        const canvas = document.getElementById("audioCanvas");
        const ctx = this.canvasCtx;

        // 设置 Canvas 尺寸
        const width = canvas.width = canvas.offsetWidth;
        const height = canvas.height = canvas.offsetHeight;

        // 获取音频数据
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteFrequencyData(dataArray);

        // 清空 Canvas
        ctx.fillStyle = "#f8f9fa";
        ctx.fillRect(0, 0, width, height);

        // 绘制波形
        const barWidth = (width / bufferLength) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            barHeight = (dataArray[i] / 255) * height;

            // 设置颜色（渐变）
            const gradient = ctx.createLinearGradient(0, height - barHeight, 0, height);
            gradient.addColorStop(0, "#667eea");
            gradient.addColorStop(1, "#764ba2");
            ctx.fillStyle = gradient;

            // 绘制条形图
            ctx.fillRect(x, height - barHeight, barWidth, barHeight);

            x += barWidth + 1;
        }

        // 继续绘制
        requestAnimationFrame(() => this.drawAudioVisualization());
    }
}

// 初始化语音接口
document.addEventListener("DOMContentLoaded", () => {
    const voiceInterface = new VoiceInterface();
    console.log("语音接口已初始化 (支持 VAD + AEC + 音频可视化)");
    
    // 启动音频可视化
    voiceInterface.isVisualizing = true;
    voiceInterface.drawAudioVisualization();
});
