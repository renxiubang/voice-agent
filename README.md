# Voice Agent Chat System

A modular, full-link streaming, full-duplex voice agent dialogue system (macOS + Python)

[中文版本](README_CN.md)

## System Architecture

```
Frontend (Web Audio API) ↔ Gateway Layer (FastAPI + WebSocket) ↔ Auditory Layer (VAD + ASR + Speaker Recognition) ↔ Cognition Layer (LLM) ↔ TTS Layer
```

## Tech Stack

- **Gateway Layer**: FastAPI + WebSocket
- **Auditory Layer**: Silero VAD + pyannote.audio + Whisper (pywhispercpp)
- **Cognition Layer**: Apple MLX (mlx-lm)
- **TTS Layer**: Piper TTS
- **Frontend**: Web Audio API + AudioWorklet

## Installation

### Prerequisites

- macOS (Apple Silicon) - Required for Apple MLX
- Python 3.11+
- Homebrew (for system dependencies)

### Install Dependencies

```bash
# Create virtual environment
conda create -n voice-agent python=3.11
conda activate voice-agent

# Install system dependencies (macOS)
brew install portaudio espeak

# Install Python dependencies
pip install -r requirements.txt
```

### Or use the install script

```bash
chmod +x install.sh
./install.sh
```

## Configuration

Edit `config.yaml` to adjust system parameters:

```yaml
# Gateway layer config
gateway:
  host: "0.0.0.0"
  port: 8000

# Auditory layer config
auditory:
  sample_rate: 16000
  vad_threshold: 0.5
  similarity_threshold: 0.7

# Cognition layer config
cognition:
  llm_model: "mistralai/Mistral-7B-Instruct-v0.3"
  max_tokens: 512
  temperature: 0.7

# TTS layer config
tts:
  model: "zh_CN-huayan-medium"
  sample_rate: 22050
```

## Usage

### Start the System

1. **Start the backend server**:

```bash
cd /workspace/voice-agent
source venv/bin/activate
python main.py
```

2. **Open the frontend page**:

In your browser, open:

```
http://localhost:8000
```

Or open the file directly:

```bash
open frontend/index.html
```

### Use the Voice Agent

1. Click the "开始对话 (Start Dialogue)" button
2. Allow the browser to access your microphone
3. Speak to the microphone
4. The system will automatically recognize speech, generate a response, and play the TTS audio
5. Click "停止对话 (Stop Dialogue)" to end

## Project Structure

```
voice-agent/
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation (Chinese)
├── README_EN.md                # Project documentation (English)
├── RUN.md                     # Running instructions
├── install.sh                 # Installation script
├── main.py                    # Main entry point
├── test_modules.py            # Module testing script
│
├── gateway/                    # Gateway layer
│   ├── server.py              # FastAPI + WebSocket server
│   └── connection_manager.py  # WebSocket connection manager
│
├── auditory/                   # Auditory layer
│   ├── vad.py                # Silero VAD
│   ├── speaker_recognition.py # pyannote.audio speaker recognition
│   ├── asr.py                # Whisper ASR
│   └── audio_processor.py    # Audio capture and preprocessing
│
├── cognition/                  # Cognition layer
│   └── llm.py                # mlx-lm LLM inference
│
├── tts/                        # TTS layer
│   └── piper_tts.py          # Piper TTS engine
│
├── core/                       # Core modules
│   ├── orchestrator.py        # Async orchestrator
│   └── queues.py              # asyncio.Queue definitions
│
├── frontend/                   # Frontend
│   ├── index.html             # Web page
│   ├── voice_interface.js     # AudioWorklet + WebSocket client
│   └── audio_worklet.js      # AudioWorklet processor
│
└── utils/                      # Utility functions
    ├── config_loader.py        # Configuration loader
    └── audio_utils.py         # Audio processing utilities
```

## Key Features

### 1. Modular Cascade Architecture

The system is divided into four independent modules:
- **Gateway Layer**: Handles WebSocket connections
- **Auditory Layer**: VAD + Speaker Recognition + ASR
- **Cognition Layer**: LLM inference
- **TTS Layer**: Text-to-Speech synthesis

Each module runs as an independent async task, communicating via `asyncio.Queue`.

### 2. Full-Link Streaming

The entire pipeline supports streaming:
- Audio captured → streamed to backend
- ASR recognizes → streams text to LLM
- LLM generates → streams tokens to TTS
- TTS synthesizes → streams audio to frontend

This minimizes latency and provides a smooth user experience.

### 3. Full-Duplex Communication

The WebSocket connection supports simultaneous bidirectional audio streaming:
- Frontend can send audio while receiving TTS audio
- Backend can process audio while sending TTS audio

### 4. Speaker Recognition

The system supports speaker registration and recognition:
- Register a speaker's voiceprint
- Only recognize and process speech from registered speakers
- Prevents unauthorized users from triggering the voice agent

## Testing

### Test All Modules

```bash
python test_modules.py
```

### Test Individual Modules

```bash
# Test configuration loader
python utils/config_loader.py

# Test queue manager
python -c "from core.queues import get_audio_queue; import asyncio; asyncio.run(get_audio_queue().put('test'))"

# Test VAD model
python auditory/vad.py

# Test ASR model
python auditory/asr.py

# Test speaker recognition model
python auditory/speaker_recognition.py

# Test TTS model
python tts/piper_tts.py
```

## Troubleshooting

### 1. mlx-lm installation failed

**Error**: `pip install mlx-lm` failed

**Solution**: Ensure you are on macOS (Apple Silicon) and have Xcode Command Line Tools installed.

```bash
xcode-select --install
```

### 2. pyannote.audio model download failed

**Error**: Failed to download model from HuggingFace Hub

**Solution**: Set HuggingFace Hub mirror or use a proxy.

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. Piper TTS not installed

**Error**: `piper: command not found`

**Solution**: Install Piper TTS.

```bash
pip install piper-tts
```

### 4. Audio device not found

**Error**: `sounddevice.PortAudioError: No Default Output Device Available`

**Solution**: Check audio device connection, or specify device ID in code.

```python
import sounddevice as sd
print(sd.query_devices())  # View available devices
```

## How It Works

### Audio Processing Pipeline

1. **Audio Capture**: 
   - Frontend captures microphone audio using `MediaRecorder` (or `AudioWorklet`)
   - Audio format: PCM 16-bit, 16kHz, mono

2. **VAD Detection**:
   - Silero VAD detects speech activity
   - Filters out silence and noise

3. **Speaker Recognition**:
   - pyannote.audio extracts speaker embedding
   - Compares with registered speakers
   - Only proceeds if speaker is recognized

4. **Speech Recognition**:
   - Whisper (pywhispercpp) transcribes speech to text
   - Supports Chinese and English

5. **LLM Inference**:
   - mlx-lm runs LLM on Apple Silicon
   - Streaming generation (token by token)

6. **TTS Synthesis**:
   - Piper TTS converts text to speech
   - Streaming synthesis (sentence by sentence)

7. **Audio Playback**:
   - Frontend receives TTS audio via WebSocket
   - Plays audio using Web Audio API

### Async Orchestrator

The `Orchestrator` class manages the entire pipeline:

```python
# Initialize modules
await orchestrator.initialize_modules()

# Start async loops
await asyncio.gather(
    orchestrator.auditory_loop(),   # VAD + ASR
    orchestrator.cognition_loop(),   # LLM
    orchestrator.tts_loop()          # TTS
)
```

### Module Communication

Modules communicate via `asyncio.Queue`:

```
audio_queue  →  text_queue  →  llm_queue  →  tts_queue
   (bytes)        (str)          (str)          (bytes)
```

## Performance Optimization

### Latency Optimization

- **Streaming processing**: LLM generates tokens while TTS synthesizes audio
- **Buffer management**: TTS buffer size adjustable (default: 20 chars)
- **Model quantization**: Use quantized models for faster inference

### Memory Optimization

- **Audio compression**: PCM 16-bit format
- **Queue size limits**: Prevent memory overflow
- **Model unloading**: Unload models when not in use

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## GitHub Repository

https://github.com/renxiubang/voice-agent

## Acknowledgments

- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice Activity Detection
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - Speaker Recognition
- [Whisper](https://github.com/openai/whisper) - Speech Recognition
- [mlx-lm](https://github.com/ml-explore/mlx-examples) - LLM Inference on Apple Silicon
- [Piper TTS](https://github.com/rhasspy/piper) - Text-to-Speech
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Audio Processing
