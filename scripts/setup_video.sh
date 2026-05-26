#!/bin/bash
# Setup script for Virtus video generation dependencies
#
# Installs:
# - Node.js 22+ check
# - FFmpeg check
# - HyperFrames CLI
# - Python dependencies

set -e

echo "=== Virtus 動画生成セットアップ ==="
echo ""

# Check Node.js version
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -ge 22 ]; then
        echo "Node.js $(node -v) - OK"
    else
        echo "Node.js $(node -v) は古いです。Node.js 22+ をインストールしてください"
        echo "   https://nodejs.org/"
        exit 1
    fi
else
    echo "Node.js が見つかりません。Node.js 22+ をインストールしてください"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check FFmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "FFmpeg - OK ($(ffmpeg -version | head -1 | awk '{print $3}'))"
else
    echo "FFmpeg が見つかりません。インストールしてください:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt install ffmpeg"
    exit 1
fi

# Install HyperFrames
echo ""
echo "HyperFrames をインストール中..."
npx skills add heygen-com/hyperframes || true
echo "HyperFrames インストール完了"

# Install Python dependencies
echo ""
echo "Python 依存関係をインストール中..."
pip install -e ".[video]"
echo "Python 依存関係インストール完了"

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "テスト実行:"
echo "  python -m pytest tests/"
echo ""
echo "デモ実行:"
echo "  export ANTHROPIC_API_KEY=sk-ant-..."
echo "  python examples/demo_video_generation.py"
echo ""
echo "CLI 使用:"
echo "  python scripts/virtus_video.py create --title 'タイトル' --duration 10"
