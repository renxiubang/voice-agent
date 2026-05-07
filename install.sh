#!/bin/bash
# 智能体语音对话系统 - 安装脚本

set -e  # 遇到错误立即退出

echo "===== 智能体语音对话系统 - 安装脚本 ====="
echo ""

# 检查 Python 版本
echo "1. 检查 Python 版本..."
python3 --version || (echo "错误: 未找到 Python 3" && exit 1)
echo "✓ Python 检查通过"
echo ""

# 创建虚拟环境
echo "2. 创建虚拟环境..."
if [! -d "venv" ]; then
    python3 -m venv venv
fi
echo "✓ 虚拟环境已创建"
echo ""

# 激活虚拟环境
echo "3. 激活虚拟环境..."
source venv/bin/activate
echo "✓ 虚拟环境已激活"
echo ""

# 安装系统依赖 (macOS)
echo "4. 检查系统依赖 (macOS)..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS 系统，正在安装系统依赖..."
    
    # 检查 Homebrew
    if! command -v brew &&; then
        echo "错误: 未找到 Homebrew，请先安装 Homebrew"
        echo "安装命令: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # 安装 portaudio (用于 sounddevice)
    brew install portaudio
    
    # 安装 espeak (用于 Piper TTS)
    brew install espeak
    
    echo "✓ 系统依赖已安装"
else
    echo "警告: 非 macOS 系统，跳过系统依赖安装"
fi
echo ""

# 安装 Python 依赖
echo "5. 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Python 依赖已安装"
echo ""

# 下载 Whisper 模型 (pywhispercpp 会自动下载)
echo "6. 预下载 Whisper 模型..."
python3 -c "
import asyncio
from auditory.asr import ASRModel
from utils.config_loader import load_config

async def download_model():
    config = load_config()
    asr_model = ASRModel(config['auditory'])
    await asr_model.load_model()
    print('Whisper 模型已下载')

asyncio.run(download_model())
" || echo "警告: Whisper 模型下载失败，将在首次运行时自动下载"
echo ""

# 完成
echo "===== 安装完成 ====="
echo ""
echo "运行方式:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "然后打开浏览器访问: http://localhost:8000"
echo ""
