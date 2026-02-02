#!/bin/bash
# Project GOZEN - Qwen環境構築スクリプト
#
# 使用方法:
#   ./scripts/setup_qwen.sh [--check-only]
#
# オプション:
#   --check-only  確認のみ（ダウンロードしない）

set -e

# === 設定 ===
REQUIRED_MODELS=(
    "qwen2.5:32b-instruct-q4_K_M"   # 参謀用
    "qwen2.5:14b-instruct-q4_K_M"   # 提督/士官用
    "qwen2.5:7b-instruct-q8_0"      # 書記用（高品質）
    "qwen2.5:7b-instruct-q4_K_M"    # 海兵/歩兵用（並列）
)

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# === 関数 ===

check_ollama_installed() {
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}[ERROR] Ollama がインストールされていません${NC}"
        echo ""
        echo "インストール方法:"
        echo "  curl -fsSL https://ollama.com/install.sh | sh"
        echo ""
        return 1
    fi
    echo -e "${GREEN}[OK] Ollama インストール済み${NC}"
    return 0
}

check_ollama_running() {
    if ! ollama list &> /dev/null; then
        echo -e "${YELLOW}[WARN] Ollama サービスが起動していません${NC}"
        echo "起動中..."
        ollama serve &> /dev/null &
        sleep 3
    fi
    echo -e "${GREEN}[OK] Ollama サービス起動中${NC}"
    return 0
}

check_model_exists() {
    local model=$1
    if ollama list 2>/dev/null | grep -q "${model%%:*}"; then
        # モデルファミリが存在する場合、正確なタグも確認
        if ollama list 2>/dev/null | grep -q "$model"; then
            return 0
        fi
    fi
    return 1
}

download_model() {
    local model=$1
    echo -e "${YELLOW}[DOWNLOAD] ${model} をダウンロード中...${NC}"
    if ollama pull "$model"; then
        echo -e "${GREEN}[OK] ${model} ダウンロード完了${NC}"
    else
        echo -e "${RED}[ERROR] ${model} ダウンロード失敗${NC}"
        return 1
    fi
}

check_disk_space() {
    # 必要な容量（概算）
    # 32B-Q4: ~20GB, 14B-Q4: ~9GB, 7B-Q8: ~8GB, 7B-Q4: ~4GB
    # 合計: ~41GB + バッファ = 50GB推奨
    local required_gb=50
    local available_gb
    available_gb=$(df -BG ~ | tail -1 | awk '{print $4}' | tr -d 'G')

    if [ "$available_gb" -lt "$required_gb" ]; then
        echo -e "${YELLOW}[WARN] ディスク空き容量が少ない可能性があります${NC}"
        echo "  必要: ${required_gb}GB以上推奨"
        echo "  現在: ${available_gb}GB"
    else
        echo -e "${GREEN}[OK] ディスク空き容量: ${available_gb}GB${NC}"
    fi
}

check_memory() {
    local total_mem
    total_mem=$(free -g | awk '/^Mem:/{print $2}')
    local required_mem=32  # 32B-Q4を動かすのに最低32GB推奨

    if [ "$total_mem" -lt "$required_mem" ]; then
        echo -e "${YELLOW}[WARN] メモリが不足している可能性があります${NC}"
        echo "  推奨: ${required_mem}GB以上"
        echo "  現在: ${total_mem}GB"
        echo "  ※ 32Bモデルは逐次ロードで運用してください"
    else
        echo -e "${GREEN}[OK] メモリ: ${total_mem}GB${NC}"
    fi
}

print_summary() {
    echo ""
    echo "========================================"
    echo "  Project GOZEN - Qwen環境サマリ"
    echo "========================================"
    echo ""

    local all_ok=true
    for model in "${REQUIRED_MODELS[@]}"; do
        if check_model_exists "$model"; then
            echo -e "  ${GREEN}✓${NC} $model"
        else
            echo -e "  ${RED}✗${NC} $model"
            all_ok=false
        fi
    done

    echo ""
    if [ "$all_ok" = true ]; then
        echo -e "${GREEN}全モデル準備完了！CONFIDENTIALモードが使用可能です。${NC}"
    else
        echo -e "${YELLOW}一部モデルが未準備です。${NC}"
    fi
    echo ""
}

# === メイン処理 ===

main() {
    local check_only=false

    if [ "$1" = "--check-only" ]; then
        check_only=true
    fi

    echo "========================================"
    echo "  Project GOZEN - Qwen環境構築"
    echo "========================================"
    echo ""

    # 前提条件チェック
    echo "[1/5] Ollama インストール確認..."
    check_ollama_installed || exit 1

    echo ""
    echo "[2/5] Ollama サービス確認..."
    check_ollama_running || exit 1

    echo ""
    echo "[3/5] システムリソース確認..."
    check_disk_space
    check_memory

    echo ""
    echo "[4/5] モデル確認..."

    missing_models=()
    for model in "${REQUIRED_MODELS[@]}"; do
        if check_model_exists "$model"; then
            echo -e "  ${GREEN}[OK]${NC} $model"
        else
            echo -e "  ${RED}[MISSING]${NC} $model"
            missing_models+=("$model")
        fi
    done

    echo ""
    echo "[5/5] モデルダウンロード..."

    if [ ${#missing_models[@]} -eq 0 ]; then
        echo -e "${GREEN}全モデル準備済み。ダウンロード不要です。${NC}"
    elif [ "$check_only" = true ]; then
        echo -e "${YELLOW}--check-only モード: ダウンロードをスキップ${NC}"
        echo "未準備モデル:"
        for model in "${missing_models[@]}"; do
            echo "  - $model"
        done
    else
        echo "未準備モデルをダウンロードします..."
        echo ""
        for model in "${missing_models[@]}"; do
            download_model "$model" || exit 1
            echo ""
        done
    fi

    # サマリ表示
    print_summary
}

main "$@"
