/**
 * WebRTC VAD 简化实现
 * 注意：这是一个简化版本，实际生产环境应使用完整的 WebRTC VAD Wasm 模块
 * 完整实现请参考：https://github.com/webrtc/samples/tree/gh-pages/src/content/getusermedia/record
 */

class VAD {
    /**
     * 构造函数
     */
    constructor() {
        this.mode = 3; // 激进模式 (0-3)
        this.initialized = false;
        this.sampleRate = 16000;
        
        // VAD 状态
        this.isSpeech = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
        
        // 能量阈值（简化实现）
        this.energyThreshold = 0.01;
    }

    /**
     * 初始化 VAD
     */
    async init() {
        // 简化版本，直接标记为已初始化
        this.initialized = true;
        console.log('VAD 初始化完成 (简化版本)');
        return Promise.resolve();
    }

    /**
     * 设置激进模式
     * @param {number} mode - 模式 (0-3)，数字越大越激进
     */
    setMode(mode) {
        this.mode = mode;
        
        // 根据模式调整阈值
        switch(mode) {
            case 0:
                this.energyThreshold = 0.02;
                break;
            case 1:
                this.energyThreshold = 0.015;
                break;
            case 2:
                this.energyThreshold = 0.01;
                break;
            case 3:
                this.energyThreshold = 0.005;
                break;
            default:
                this.energyThreshold = 0.01;
        }
        
        console.log(`VAD 模式设置为: ${mode}, 阈值: ${this.energyThreshold}`);
    }

    /**
     * 计算音频能量
     * @param {Int16Array} pcmData - PCM 音频数据
     * @returns {number} 能量值
     */
    calculateEnergy(pcmData) {
        let sum = 0;
        for (let i = 0; i < pcmData.length; i++) {
            const sample = pcmData[i] / 32768.0; // 归一化到 [-1, 1]
            sum += sample * sample;
        }
        return Math.sqrt(sum / pcmData.length);
    }

    /**
     * 处理音频帧，检测是否包含语音
     * @param {Int16Array} pcmData - PCM 音频数据 (Int16Array)
     * @param {number} sampleRate - 采样率
     * @returns {number} 1 表示语音，0 表示静音
     */
    process(pcmData, sampleRate) {
        if (!this.initialized) {
            console.warn('VAD 未初始化，请先调用 init()');
            return 0;
        }

        // 计算音频能量
        const energy = this.calculateEnergy(pcmData);
        
        // 简单的能量阈值检测（简化实现）
        if (energy > this.energyThreshold) {
            this.speechFrames++;
            this.silenceFrames = 0;
            this.isSpeech = true;
            return 1; // 检测到语音
        } else {
            this.silenceFrames++;
            this.speechFrames = 0;
            
            // 需要连续多帧静音才判定为静音（避免误判）
            if (this.silenceFrames > 5) {
                this.isSpeech = false;
            }
            
            return 0; // 静音
        }
    }

    /**
     * 重置 VAD 状态
     */
    reset() {
        this.isSpeech = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
    }
}

// 导出 VAD 类
export default VAD;
