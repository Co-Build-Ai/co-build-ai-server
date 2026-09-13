"""
patent_veri_yukle.py
============================================================================
Co-Build AI — Patent Veri Seti Yükleyici (Tek Seferlik Script)
============================================================================
HUPD (Harvard USPTO Patent Dataset) veri setinden G06F (bilgi işlem) veya
G06N (yapay zeka) sınıflandırma kodlu patentleri filtreler, mevcut RAG
mimarimizle aynı embedding modeliyle (all-MiniLM-L6-v2) vektörleştirir ve
ChromaDB'nin `patent_ornekleri` koleksiyonuna kaydeder.

veri_yukle.py ile aynı desen: Excel yerine Hugging Face `datasets`
kütüphanesiyle HUPD/hupd veri setini kullanıyoruz.

ÖNEMLİ — datasets sürümü
-------------------------
HUPD/hupd, Hugging Face Hub'da eski tip bir "loading script" (hupd.py)
üzerinden yükleniyor. `datasets>=3.0` bu tip veri setlerini ARTIK
DESTEKLEMİYOR ("Dataset scripts are no longer supported" hatası verir).
Bu yüzden requirements.txt'te `datasets==2.19.0` sabitlendi — daha yeni bir
sürüme yükseltmeyin, HUPD yüklemesi kırılır.

ÖNEMLİ — "tam" veri seti (`--tam`) 57,5 GB'lık TEK bir arşiv
--------------------------------------------------------------
HUPD'nin "all" config'i, `load_dataset` çağrısında hangi tarih aralığı
verilirse verilsin, HER ZAMAN "all-years.tar" (57,5 GB, 2004-2018 tüm
yıllar) dosyasının TAMAMINI indirir — kısmi/streaming indirme bu format
için desteklenmiyor (TAR arşivi). Bu, çoğu ortamda pratik değildir.

Bunun yerine `--yil YIL` seçeneği, Hugging Face deposundaki tek bir yılın
küçük dosyasını (örn. `data/2016.tar.gz`, ~5 GB) DOĞRUDAN indirir ve
`datasets` kütüphanesini/metadata dosyasını hiç kullanmadan, o yılın
içindeki patent JSON dosyalarını (her biri kendi başlık/özet/sınıflandırma
kodunu taşıyor) doğrudan okur. 3000-5000 hedefine ulaşmak için genelde
TEK BİR yıl yeterlidir (bkz. sample'daki oran: Ocak 2016 tek başına 2118
eşleşme verdi — tam bir yıl ~12 katı, yani ~20.000+ eşleşme beklenir).

Kullanım
--------
1) Küçük bir örnekle test (varsayılan, ~22.000 kayıt, sadece Ocak 2016):
    python patent_veri_yukle.py

2) Tek bir yılın verisiyle (ÖNERİLEN — 3000-5000 hedefi için yeterli, ~5GB):
    python patent_veri_yukle.py --yil 2016

3) TÜM veri seti (57,5 GB, saatlerce sürebilir, ~100+ GB disk ister):
    python patent_veri_yukle.py --tam
"""

from __future__ import annotations

import argparse
import glob
import json as json_lib
import os
import sys
import tarfile

import chromadb
import httpx
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

HF_CACHE_KLASORU = "hf_cache"  # indirilen/açılan büyük dosyalar burada tutulur (.gitignore'da)

# G06F: Elektrikli sayısal veri işleme (bilgi işlem)
# G06N: Belirli hesaplama modellerine dayalı bilgi işlem düzenlemeleri (YZ/ML)
HEDEF_SINIF_ONEKLERI = ("G06F", "G06N")
HEDEF_MIN_KAYIT = 3000
HEDEF_MAKS_KAYIT = 5000
BATCH_SIZE = 100


def siniflandirma_kodunu_al(kayit: dict) -> str:
    """
    HUPD kayıtlarında sınıflandırma kodu iki alanda olabilir: `cpc_label`
    (Cooperative Patent Classification) veya `ipc_label` (International
    Patent Classification). Görüntüleme/metadata amacıyla CPC'yi tercih
    ediyoruz (daha güncel/standart), boşsa IPC'ye düşüyoruz. Filtreleme
    için ise `kayit_hedef_kitlede_mi` ikisini de BAĞIMSIZ kontrol eder.
    """
    return (kayit.get("cpc_label") or kayit.get("ipc_label") or "").strip()


def kayit_hedef_kitlede_mi(kayit: dict) -> bool:
    """
    G06F/G06N ile başlayan bir sınıflandırma kodu (CPC VEYA IPC'den herhangi
    biri eşleşirse yeterli — bazı kayıtlarda sadece biri dolu/eşleşen
    olabiliyor) VE dolu bir abstract şartı.
    """
    cpc = (kayit.get("cpc_label") or "").strip()
    ipc = (kayit.get("ipc_label") or "").strip()
    abstract = (kayit.get("abstract") or "").strip()
    kod_eslesiyor = cpc.startswith(HEDEF_SINIF_ONEKLERI) or ipc.startswith(HEDEF_SINIF_ONEKLERI)
    return kod_eslesiyor and len(abstract) > 0


def veri_setini_yukle(tam_veri_seti: bool):
    config_adi = "all" if tam_veri_seti else "sample"
    print(f"HUPD veri seti indiriliyor/yükleniyor (config='{config_adi}')...")
    print("(İlk çalıştırmada indirme gerekebilir, biraz sürebilir.)")

    try:
        # uniform_split=True: HUPD'nin kendi eğitim/doğrulama tarih aralığı
        # belirtme zorunluluğunu atlayıp varsayılan dengeli bölünmeyi kullanır.
        veri_seti = load_dataset(
            "HUPD/hupd",
            name=config_adi,
            trust_remote_code=True,
            split="train",
            uniform_split=True,
        )
    except Exception as e:
        print(f"HATA: Veri seti yüklenemedi: {e}")
        print(
            "İpucu: 'pip install datasets==2.19.0' kurulu mu? "
            "(datasets>=3.0 HUPD'nin eski tip loading script'ini desteklemiyor.)"
        )
        sys.exit(1)

    return veri_seti


def filtrele(veri_seti) -> list[dict]:
    print(f"Veri seti yüklendi. Toplam kayıt: {len(veri_seti)}")
    print("Filtreleme kriterleri uygulanıyor (G06F/G06N sınıflandırma kodu + dolu abstract)...")

    filtrelenmis: list[dict] = []
    for i, kayit in enumerate(veri_seti):
        if kayit_hedef_kitlede_mi(kayit):
            filtrelenmis.append(kayit)
        if (i + 1) % 5000 == 0:
            print(f"  ...{i + 1} kayıt tarandı, şu ana kadar {len(filtrelenmis)} eşleşme bulundu.")
        if len(filtrelenmis) >= HEDEF_MAKS_KAYIT:
            print(f"  Hedef maksimum ({HEDEF_MAKS_KAYIT}) kayda ulaşıldı, tarama durduruldu.")
            break

    print(f"\nFiltreleme tamamlandı: {len(filtrelenmis)} kayıt bulundu (hedef: {HEDEF_MIN_KAYIT}-{HEDEF_MAKS_KAYIT}).")
    if len(filtrelenmis) < HEDEF_MIN_KAYIT:
        print(
            f"UYARI: Hedeflenen minimum {HEDEF_MIN_KAYIT} kayda ulaşılamadı "
            f"({len(filtrelenmis)} bulundu). 'sample' config'de bu normal olabilir "
            "— tam veri setinde (--tam) çok daha fazla eşleşme beklenir."
        )
    return filtrelenmis


# ============================================================================
# YIL BAZLI MOD (--yil): datasets kütüphanesini/57,5 GB'lık tam arşivi
# kullanmadan, tek bir yılın küçük dosyasını doğrudan indirip işler.
# ============================================================================

def yil_verisini_indir(yil: str) -> str:
    """
    `data/{yil}.tar.gz` dosyasını (tam `all-years.tar` yerine SADECE o yıl,
    ~5 GB) doğrudan Hugging Face'ten indirir. Zaten indirilmişse atlar.
    """
    os.makedirs(HF_CACHE_KLASORU, exist_ok=True)
    tar_yolu = os.path.join(HF_CACHE_KLASORU, f"{yil}.tar.gz")
    if os.path.exists(tar_yolu):
        print(f"{tar_yolu} zaten mevcut, indirme atlanıyor.")
        return tar_yolu

    url = f"https://huggingface.co/datasets/HUPD/hupd/resolve/main/data/{yil}.tar.gz"
    print(f"İndiriliyor: {url}")
    gecici_yol = tar_yolu + ".tmp"
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=None) as r:
            r.raise_for_status()
            toplam = int(r.headers.get("content-length", 0))
            indirilen = 0
            son_bildirim = 0
            with open(gecici_yol, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=1024 * 1024 * 8):
                    f.write(chunk)
                    indirilen += len(chunk)
                    if indirilen - son_bildirim > 1024 * 1024 * 200:
                        son_bildirim = indirilen
                        print(f"  {indirilen / 1024**3:.2f} GB / {toplam / 1024**3:.2f} GB indirildi...")
    except Exception:
        if os.path.exists(gecici_yol):
            os.remove(gecici_yol)  # yarım kalan indirmeyi silip bir sonraki çalıştırmada baştan başlat
        raise

    os.rename(gecici_yol, tar_yolu)
    print("İndirme tamamlandı.")
    return tar_yolu


def yil_verisini_cikart(tar_yolu: str, yil: str) -> str:
    """tar.gz'yi açar (zaten açılmışsa atlar), açılan klasörün yolunu döner."""
    hedef_klasor = os.path.join(HF_CACHE_KLASORU, f"{yil}_extracted")
    if os.path.isdir(hedef_klasor) and any(os.scandir(hedef_klasor)):
        print(f"{hedef_klasor} zaten açılmış, tekrar açılmıyor.")
        return hedef_klasor

    print(f"{tar_yolu} açılıyor (bir miktar sürebilir)...")
    os.makedirs(hedef_klasor, exist_ok=True)
    with tarfile.open(tar_yolu, "r:gz") as tar:
        tar.extractall(hedef_klasor)
    print("Açma tamamlandı.")
    return hedef_klasor


def yil_json_dosyalarindan_filtrele(extracted_klasor: str) -> list[dict]:
    """
    Açılan klasördeki tüm patent JSON dosyalarını (her biri kendi başlığını,
    özetini ve sınıflandırma kodunu taşır — bkz. modül docstring'i) tarar,
    G06F/G06N filtresini uygular.
    """
    json_yollari = glob.glob(os.path.join(extracted_klasor, "**", "*.json"), recursive=True)
    print(f"Toplam {len(json_yollari)} JSON dosyası bulundu, taranıyor...")

    filtrelenmis: list[dict] = []
    for i, yol in enumerate(json_yollari):
        try:
            with open(yol, "r", encoding="utf-8") as f:
                ham = json_lib.load(f)
        except Exception as e:
            print(f"  UYARI: {yol} okunamadı, atlanıyor ({e}).")
            continue

        kayit = {
            "patent_number": os.path.splitext(os.path.basename(yol))[0],
            "title": ham.get("title") or "",
            "abstract": ham.get("abstract") or "",
            # Ham JSON'daki alan adları datasets kütüphanesinin ürettiği
            # "cpc_label"/"ipc_label" değil, HUPD'nin kendi ham alan adları:
            "cpc_label": ham.get("main_cpc_label") or "",
            "ipc_label": ham.get("main_ipcr_label") or "",
            "filing_date": ham.get("filing_date") or "",
        }
        if kayit_hedef_kitlede_mi(kayit):
            filtrelenmis.append(kayit)

        if (i + 1) % 5000 == 0:
            print(f"  ...{i + 1}/{len(json_yollari)} dosya tarandı, şu ana kadar {len(filtrelenmis)} eşleşme.")
        if len(filtrelenmis) >= HEDEF_MAKS_KAYIT:
            print(f"  Hedef maksimum ({HEDEF_MAKS_KAYIT}) kayda ulaşıldı, tarama durduruldu.")
            break

    print(f"\nFiltreleme tamamlandı: {len(filtrelenmis)} kayıt bulundu (hedef: {HEDEF_MIN_KAYIT}-{HEDEF_MAKS_KAYIT}).")
    return filtrelenmis


def vektorle_ve_kaydet(filtrelenmis: list[dict]) -> None:
    if not filtrelenmis:
        print("Kaydedilecek kayıt yok, işlem durduruluyor.")
        sys.exit(1)

    print("\nEmbedding modeli yükleniyor (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("ChromaDB koleksiyonu hazırlanıyor: patent_ornekleri (cosine benzerlik uzayı)")
    client = chromadb.PersistentClient(path="./chroma_data")
    # main.py'deki patent_cakismasi_kontrol_et fonksiyonu cosine benzerliği
    # ("1 - mesafe") beklediği için koleksiyon AYNI ayarla oluşturulmalı.
    collection = client.get_or_create_collection(
        name="patent_ornekleri",
        metadata={"hnsw:space": "cosine"},
    )

    print("Embedding'ler oluşturuluyor ve ChromaDB'ye kaydediliyor...")
    for i in range(0, len(filtrelenmis), BATCH_SIZE):
        batch = filtrelenmis[i : i + BATCH_SIZE]

        metinler = [
            f"{(k.get('title') or '').strip()}. {(k.get('abstract') or '').strip()}"
            for k in batch
        ]
        embeddingler = model.encode(metinler).tolist()

        ids = [f"patent_{k.get('patent_number') or (i + j)}" for j, k in enumerate(batch)]
        metadatalar = [
            {
                "patent_number": str(k.get("patent_number") or ""),
                "title": (k.get("title") or "")[:300],
                "classification_code": siniflandirma_kodunu_al(k),
                "filing_date": str(k.get("filing_date") or ""),
            }
            for k in batch
        ]

        # upsert (add değil): sample modu Ocak 2016'yı içeriyor, --yil 2016
        # çalıştırıldığında aynı patentler tekrar gelebilir — upsert bu
        # çakışmada hata vermek yerine kaydı günceller (idempotent).
        collection.upsert(
            ids=ids,
            embeddings=embeddingler,
            documents=metinler,
            metadatas=metadatalar,
        )

        print(f"  {min(i + BATCH_SIZE, len(filtrelenmis))} / {len(filtrelenmis)} kayıt işlendi...")

    print("\nTamamlandı! Veri chroma_data/ klasörüne kaydedildi.")
    print(f"Toplam kayıt sayısı (patent_ornekleri): {collection.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HUPD patent veri setini ChromaDB'ye yükler.")
    parser.add_argument(
        "--tam",
        action="store_true",
        help="Küçük örnek ('sample') yerine TÜM veri setini ('all', 57,5 GB) kullan.",
    )
    parser.add_argument(
        "--yil",
        type=str,
        default=None,
        help="Belirli bir yılın verisiyle çalış (örn. 2016) — sadece o yılın küçük "
        "dosyasını (~5 GB) indirir, 57,5 GB'lık tam arşivi indirmez. 3000-5000 "
        "hedefine ulaşmak için genelde tek bir yıl yeterlidir.",
    )
    args = parser.parse_args()

    if args.tam:
        onay = input(
            "DİKKAT: Tam HUPD veri setini (57,5 GB, tek parça arşiv) indirip "
            "işleyeceksiniz — bu uzun sürebilir ve ~100+ GB disk alanı gerektirir. "
            "Devam etmek istediğinize emin misiniz? (evet/hayır): "
        )
        if onay.strip().lower() not in ("evet", "e", "yes", "y"):
            print("İptal edildi.")
            sys.exit(0)

        ds = veri_setini_yukle(tam_veri_seti=True)
        kayitlar = filtrele(ds)
        vektorle_ve_kaydet(kayitlar)

    elif args.yil:
        tar_yolu = yil_verisini_indir(args.yil)
        extracted_klasor = yil_verisini_cikart(tar_yolu, args.yil)
        kayitlar = yil_json_dosyalarindan_filtrele(extracted_klasor)
        vektorle_ve_kaydet(kayitlar)

    else:
        ds = veri_setini_yukle(tam_veri_seti=False)
        kayitlar = filtrele(ds)
        vektorle_ve_kaydet(kayitlar)
