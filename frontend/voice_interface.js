/**
 * 语音接口 - WebSocket 客户端 + AudioWorklet
 */

class VoiceInterface {
    /**
     * 初始化语音接口
     * @param {string} websocketUrl - WebSocket 服务器 URL
     */
    constructor(websocketUrl = "ws://localhost:8000/ws") {
        this.websocketUrl = websocketUrl;
        this.websocket = null;
        this.audioContext = null;
        this.audioWorkletNode = null;
        this.mediaRecorder = null;
        this.isRecording = false;
        this.isPlaying = false;
        
        // 音频播放队列
        this.audioQueue = [];
        this.isProcessingAudioQueue = false;
        
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
        
        // 加载 AudioWorklet 处理器
        await this.audioContext.audioWorklet.addModule("audio_worklet.js");
        
        console.log("音频上下文初始化完成");
    }

    /**
     * 关闭音频上下文
     */
    async closeAudioContext() {
        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
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
     * 播放音频
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
            22050  // 采样率 (与 TTS 输出一致)
        );
        
        audioBuffer.getChannelData(0).set(float32Array);
        
        // 创建 BufferSource
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);
        
        // 等待播放完成
        return new Promise((resolve) => {
            source.onended = () => {
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
            // 获取麦克风权限
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,  // 回声消除
                    noiseSuppression: true    // 噪声抑制
                }
            });
            
            // 创建 MediaRecorder
            this.mediaRecorder = new MediaRecorder(stream);
            
            // 处理音频数据
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.sendAudioData(event.data);
                }
            };
            
            // 开始录音
            this.mediaRecorder.start(100);  // 每 100ms 发送一次数据
            this.isRecording = true;
            
            console.log("录音已开始");
            this.updateAudioStatus("正在录音...");
            
        } catch (error) {
            console.error("开始录音失败:", error);
            throw error;
        }
    }

    /**
     * 停止录音
     */
    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // 关闭麦克风流
            this.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
            
            console.log("录音已停止");
            this.updateAudioStatus("录音已停止");
        }
    }

    /**
     * 发送音频数据到 WebSocket
     * @param {Blob} audioBlob - 音频数据 (Blob)
     */
    sendAudioData(audioBlob) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            audioBlob.arrayBuffer().then((buffer) => {
                this.websocket.send(buffer);
            });
        }
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
}

// 初始化语音接口
document.addEventListener("DOMContentLoaded", () => {
    const voiceInterface = new VoiceInterface();
    console.log("语音接口已初始化");
});
