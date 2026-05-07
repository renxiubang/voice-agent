/**
 * AudioWorklet 处理器 - 实时音频采集
 */

class AudioCaptureProcessor extends AudioWorkletProcessor {
    /**
     * 构造函数
     * @param {AudioWorkletNodeOptions} options - 选项
     */
    constructor(options) {
        super(options);
        
        // 采样率
        this.sampleRate = options.processorOptions.sampleRate || 16000;
        
        // 音频缓冲区
        this.bufferSize = options.processorOptions.bufferSize || 4096;
        this.audioBuffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
        
        // 是否正在录音
        this.isRecording = false;
    }

    /**
     * 音频处理函数
     * @param {Float32Array[][]} inputs - 输入音频数据
     * @param {Float32Array[][]} outputs - 输出音频数据
     * @param {Object} parameters - 参数
     * @returns {boolean} 是否保持处理器活跃
     */
    process(inputs, outputs, parameters) {
        // 如果没有输入，返回 true (保持处理器活跃)
        if (inputs.length === 0 || inputs[0].length === 0) {
            return true;
        }
        
        // 获取输入音频 (第一个输入的第一个声道)
        const input = inputs[0][0];
        
        if (!input || input.length === 0) {
            return true;
        }
        
        // 将音频数据添加到缓冲区
        for (let i = 0; i < input.length; i++) {
            this.audioBuffer[this.bufferIndex] = input[i];
            this.bufferIndex++;
            
            // 如果缓冲区已满，发送数据到主线程
            if (this.bufferIndex >= this.bufferSize) {
                this.sendAudioData();
            }
        }
        
        return true;
    }

    /**
     * 发送音频数据到主线程
     */
    sendAudioData() {
        // 将 Float32 转换为 Int16 (PCM 16-bit)
        const int16Buffer = new Int16Array(this.bufferSize);
        
        for (let i = 0; i < this.bufferSize; i++) {
            // 限制在 -1.0 ~ 1.0
            const sample = Math.max(-1.0, Math.min(1.0, this.audioBuffer[i]));
            
            // 转换为 Int16
            int16Buffer[i] = sample < 0 ? sample * 32768 : sample * 32767;
        }
        
        // 发送数据到主线程
        this.port.postMessage({
            type: "audioData",
            data: int16Buffer.buffer
        }, [int16Buffer.buffer]);  // Transferable objects
        
        // 重置缓冲区
        this.bufferIndex = 0;
    }

    /**
     * 开始录音
     */
    startRecording() {
        this.isRecording = true;
        this.bufferIndex = 0;
        console.log("AudioWorklet: 开始录音");
    }

    /**
     * 停止录音
     */
    stopRecording() {
        this.isRecording = false;
        console.log("AudioWorklet: 停止录音");
    }
}

// 注册 AudioWorklet 处理器
registerProcessor("audio-capture-processor", AudioCaptureProcessor);
