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
    # SÜRÜMLER BİLEREK SABİT (2026-10-13'te denenip çalışan kombinasyon):
    # - vllm 0.10.2, torch 2.8.0+cu128 getirir; Pod sürücüsü CUDA 12.8'e kadar
    #   destekliyorsa çalışır. Sabitlenmeyen `pip install vllm` cu13 torch çeker
    #   ve "driver too old" hatası verir.
    # - transformers 5.x, vLLM 0.10.2'nin tokenizer'ını kırar
    #   (all_special_tokens_extended hatası) -> 4.56.2'ye sabit.
    # - --no-cache-dir: container diski dar; pip önbelleği yer kaplar.
    pip install --no-cache-dir "vllm==0.10.2" "transformers==4.56.2"
fi

echo "4/4 - vLLM sunucusu başlatılıyor (model indirilecekse burada zaman alır)..."
echo "NOT: 'Application startup complete' satırını gördüğünüzde hazırdır."
# 24GB VRAM'de 32B-AWQ sınırda: --enforce-eager (CUDA graph belleğini atlar) ve
# --max-num-seqs 8 olmadan "CUDA out of memory" alınıyor. Model ~18GB iner;
# container disk en az 50GB olmalı (30GB'ta indirme "not enough disk space" ile kesildi).
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ --quantization awq --max-model-len 4096 --gpu-memory-utilization 0.93 --enforce-eager --max-num-seqs 8
