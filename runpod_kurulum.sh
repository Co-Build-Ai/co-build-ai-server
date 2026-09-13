#!/bin/bash
# ============================================================================
# Co-Build AI — RunPod vLLM Sıfırdan Kurulum Scripti
# ============================================================================
# Pod'un /workspace'i BOŞSA (yeni pod, eski Network Volume bağlanamadıysa,
# veya hiç volume yoksa) bu scripti pod'un Web Terminal'inde çalıştırın.
#
# Kullanım: Pod terminaline bu dosyanın İÇERİĞİNİ yapıştırın (ya da dosyayı
# pod'a yükleyip `bash runpod_kurulum.sh` çalıştırın).
# ============================================================================

set -e  # herhangi bir komut hata verirse dur

echo "1/4 - /workspace kontrol ediliyor..."
mkdir -p /workspace
cd /workspace

if [ -d "vllm_env" ]; then
    echo "vllm_env zaten var, kurulum atlanıyor, sadece aktive ediliyor."
else
    echo "2/4 - Sanal ortam oluşturuluyor..."
    python -m venv vllm_env
fi

source vllm_env/bin/activate

if python -c "import vllm" 2>/dev/null; then
    echo "vLLM zaten kurulu, indirme atlanıyor."
else
    echo "3/4 - vLLM kuruluyor (birkaç dakika sürebilir)..."
    pip install vllm
fi

echo "4/4 - vLLM sunucusu başlatılıyor (model indirilecekse burada zaman alır)..."
echo "NOT: 'Uvicorn running on http://0.0.0.0:8000' satırını gördüğünüzde hazırdır."
vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ --quantization awq --max-model-len 4096 --gpu-memory-utilization 0.85
