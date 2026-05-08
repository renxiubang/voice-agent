/**
 * AudioWorklet 处理器 - 实时音频采集 + VAD 检测
 */

// ========== VAD 类 (内联，避免 ES module import 问题) ==========
class VAD {
    constructor() {
        this.mode = 3;
        this.initialized = false;
        this.sampleRate = 16000;
        this.isSpeech = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
        this.energyThreshold = 0.005;
    }

    async init() {
        this.initialized = true;
        console.log('VAD 初始化完成');
        return Promise.resolve();
    }

    setMode(mode) {
        this.mode = mode;
        switch(mode) {
            case 0: this.energyThreshold = 0.02; break;
            case 1: this.energyThreshold = 0.015; break;
            case 2: this.energyThreshold = 0.01; break;
            case 3: this.energyThreshold = 0.005; break;
            default: this.energyThreshold = 0.01;
        }
    }

    calculateEnergy(pcmData) {
        let sum = 0;
        for (let i = 0; i < pcmData.length; i++) {
            const sample = pcmData[i] / 32768.0;
            sum += sample * sample;
        }
        return Math.sqrt(sum / pcmData.length);
    }

    process(pcmData, sampleRate) {
        if (!this.initialized) return 0;
        const energy = this.calculateEnergy(pcmData);
        if (energy > this.energyThreshold) {
            this.speechFrames++;
            this.silenceFrames = 0;
            this.isSpeech = true;
            return 1;
        } else {
            this.silenceFrames++;
            this.speechFrames = 0;
            if (this.silenceFrames > 5) {
                this.isSpeech = false;
            }
            return 0;
        }
    }

    reset() {
        this.isSpeech = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
    }
}
// ========== VAD 类结束 ==========

class AudioCaptureProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super(options);
        
        this.sampleRate = options.processorOptions.sampleRate || 16000;
        
        // VAD 相关
        this.vad = null;
        this.vadInitialized = false;
        this.vadFrameSize = 160; // 10ms @ 16kHz
        this.vadBuffer = new Int16Array(this.vadFrameSize);
        this.vadBufferIndex = 0;
        
        // 状态机
        this.STATE = { IDLE: 0, SPEAKING: 1, STOPPING: 2 };
        this.state = this.STATE.IDLE;
        
        // 拖尾处理
        this.hangoverFrames = 15; // 150ms
        this.silenceFrameCount = 0;
        
        // 音频缓冲区
        this.speechBuffer = [];
        this.isBuffering = false;
        
        // 是否正在录音
        this.isRecording = false;
        
        // 初始化 VAD
        this.initVAD();
        
        // 监听主线程消息
        this.port.onmessage = (event) => {
            if (event.data.type === 'startRecording') {
                this.startRecording();
            } else if (event.data.type === 'stopRecording') {
                this.stopRecording();
            }
        };
    }

    async initVAD() {
        try {
            this.vad = new VAD();
            await this.vad.init();
            this.vad.setMode(3);
            this.vadInitialized = true;
            console.log('AudioWorklet: VAD 初始化成功');
            
            this.port.postMessage({ type: 'vadReady' });
        } catch (error) {
            console.error('AudioWorklet: VAD 初始化失败', error);
        }
    }

    process(inputs, outputs, parameters) {
        if (inputs.length === 0 || inputs[0].length === 0) {
            return true;
        }
        
        const input = inputs[0][0];
        if (!input || input.length === 0) {
            return true;
        }
        
        if (this.isRecording && this.vadInitialized) {
            this.processAudioWithVAD(input);
        }
        
        return true;
    }

    processAudioWithVAD(input) {
        for (let i = 0; i < input.length; i++) {
            const sample = Math.max(-1.0, Math.min(1.0, input[i]));
            const int16Sample = sample < 0 ? sample * 32768 : sample * 32767;
            
            this.vadBuffer[this.vadBufferIndex] = int16Sample;
            this.vadBufferIndex++;
            
            if (this.vadBufferIndex >= this.vadFrameSize) {
                this.processVADFrame();
                this.vadBufferIndex = 0;
            }
        }
    }

    processVADFrame() {
        if (!this.vad) return;
        
        const isSpeech = this.vad.process(this.vadBuffer, this.sampleRate);
        
        switch (this.state) {
            case this.STATE.IDLE:
                if (isSpeech === 1) {
                    this.state = this.STATE.SPEAKING;
                    this.isBuffering = true;
                    this.speechBuffer = [];
                    this.speechBuffer.push(new Int16Array(this.vadBuffer));
                    console.log('VAD: 检测到语音开始');
                    this.port.postMessage({ type: 'speechStart' });
                }
                break;
                
            case this.STATE.SPEAKING:
                if (isSpeech === 1) {
                    this.speechBuffer.push(new Int16Array(this.vadBuffer));
                    this.silenceFrameCount = 0;
                } else {
                    this.silenceFrameCount++;
                    this.speechBuffer.push(new Int16Array(this.vadBuffer));
                    if (this.silenceFrameCount >= this.hangoverFrames) {
                        this.state = this.STATE.STOPPING;
                        this.finalizeSpeech();
                    }
                }
                break;
                
            case this.STATE.STOPPING:
                this.state = this.STATE.IDLE;
                break;
        }
    }

    finalizeSpeech() {
        if (this.speechBuffer.length === 0) {
            this.state = this.STATE.IDLE;
            return;
        }
        
        const totalLength = this.speechBuffer.length * this.vadFrameSize;
        const combinedAudio = new Int16Array(totalLength);
        
        for (let i = 0; i < this.speechBuffer.length; i++) {
            combinedAudio.set(this.speechBuffer[i], i * this.vadFrameSize);
        }
        
        this.port.postMessage({
            type: 'audioData',
            data: combinedAudio.buffer
        }, [combinedAudio.buffer]);
        
        console.log(`VAD: 说话结束，发送 ${combinedAudio.length} 个采样点`);
        
        this.state = this.STATE.IDLE;
        this.speechBuffer = [];
        this.silenceFrameCount = 0;
        this.port.postMessage({ type: 'speechEnd' });
    }

    startRecording() {
        this.isRecording = true;
        this.state = this.STATE.IDLE;
        this.speechBuffer = [];
        this.silenceFrameCount = 0;
        this.vadBufferIndex = 0;
        
        if (this.vad) this.vad.reset();
        console.log('AudioWorklet: 开始录音');
    }

    stopRecording() {
        this.isRecording = false;
        if (this.isBuffering && this.speechBuffer.length > 0) {
            this.finalizeSpeech();
        }
        console.log('AudioWorklet: 停止录音');
    }
}

// 注册 AudioWorklet 处理器
registerProcessor('audio-capture-processor', AudioCaptureProcessor);
