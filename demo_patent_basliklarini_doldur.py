"""Var olan patentli profillerin patent_title alanini geriye donuk doldurur.

Bu basliklar daha once sadece PDF icine gomulmustu (bkz. demo_patent_arttir.py,
demo_bora_aydin_zenginlestir.py); yeni "Patentler" bolumunde gosterebilmek
icin veritabanina da yaziliyor. Zengin set'teki 3 patent sahibinin (Deniz
Aydemir, Kaan Yildirim, Zeynep Kaya) gercek bir baslik metni hic uretilmemisti
(sadece has_verified_patent=true set edilmisti) - bu script onlar icin de
bio'larina uygun, makul bir baslik ekliyor.

DIKKAT: Bu script SUPABASE_SERVICE_KEY kullanir. Yalnizca gelistirme/demo
projeleri uzerinde calistirin.
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_eksik = [
    isim
    for isim, deger in (("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY))
    if not deger
]
if _eksik:
    sys.exit(f"HATA: eksik ortam degiskeni: {', '.join(_eksik)}")

_SABLON_ISARETLERI = ("replace_me", "your-service-key", "buraya", "changeme")
if any(isaret in SUPABASE_SERVICE_KEY.lower() for isaret in _SABLON_ISARETLERI):
    sys.exit("HATA: SUPABASE_SERVICE_KEY hala sablon degerinde. .env dosyasini doldurun.")

_GIZLI_DEGERLER = tuple(deger for deger in (SUPABASE_SERVICE_KEY,) if deger and len(deger) >= 8)


def maskele(metin: object) -> str:
    sonuc = str(metin)
    for sir in _GIZLI_DEGERLER:
        sonuc = sonuc.replace(sir, "***GIZLI***")
    return sonuc


def onay_al() -> None:
    if os.getenv("DEMO_SEED_ONAY", "").strip().lower() in ("1", "true", "evet", "yes"):
        return
    print("Bu islem asagidaki Supabase projesine ADMIN yetkisiyle yazacak:")
    print(f"  {SUPABASE_URL}")
    try:
        cevap = input("Devam etmek icin 'EVET' yazin: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nIptal edildi (onay alinamadi).")
    if cevap != "EVET":
        sys.exit("Iptal edildi.")


onay_al()
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PATENT_BASLIKLARI = {
    "Selin Yıldız": "Görüntü Tabanlı Erken Teşhis Modeli için Veri Ön İşleme Yöntemi",
    "Onur Kurt": "Düşük Güç Tüketimli IoT Sensör Ağlarında Veri Toplama Yöntemi",
    "Deniz Koç": "Gerçek Zamanlı İşlem Anomalisi Tespiti için Hibrit Skor Yöntemi",
    "Mehmet Demir": "Çok Kiracılı Sistemlerde Otomatik Veritabanı Ölçekleme Yöntemi",
    "Bora Aydın": "Gürültülü Ortamlarda Ses Sinyali Filtreleme Yöntemi",
    "Deniz Aydemir": "Ölçeklenebilir API Mimarilerinde Otomatik Hız Sınırlama Yöntemi",
    "Kaan Yıldırım": "Düşük Çözünürlüklü Görüntülerden Nesne Tespiti için Ön İşleme Yöntemi",
    "Zeynep Kaya": "Dağıtık Sistemlerde Otomatik Hata Kurtarma Yöntemi",
}

print(f"{len(PATENT_BASLIKLARI)} profilin patent basligi dolduruluyor.\n")

for full_name, baslik in PATENT_BASLIKLARI.items():
    try:
        r = (
            supabase.table("profiles")
            .select("id, has_verified_patent")
            .eq("full_name", full_name)
            .limit(1)
            .execute()
        )
        if not r.data:
            print(f"  x '{full_name}' bulunamadı, atlanıyor")
            continue
        if not r.data[0]["has_verified_patent"]:
            print(f"  x '{full_name}' patentli görünmüyor (has_verified_patent=false), atlanıyor")
            continue

        supabase.table("profiles").update({"patent_title": baslik}).eq("id", r.data[0]["id"]).execute()
        print(f"  + {full_name}: {baslik}")
    except Exception as e:
        print(f"  x Hata ({full_name}): {maskele(e)}")

print("\nTamamlandı!")
