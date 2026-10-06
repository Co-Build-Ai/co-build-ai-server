"""Dorduncu parti profil fotografi yukleme - "foto" klasorundeki fotograflari
kalan (avatarsiz) erkek profillere yukler.

DIKKAT: Bu script SUPABASE_SERVICE_KEY kullanir. Yalnizca gelistirme/demo
projeleri uzerinde calistirin.
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

AVATAR_BUCKET = "avatars"
FOTO_KLASORU = r"C:\Users\DELL\Downloads\foto"

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

ESLESTIRME = {
    "Deniz Aydemir": "Dili Investiert on TikTok.jpg",  # patentli, once o
    "Barış Güneş": "hhhhh.png",
    "Burak Çelik": "aaaa.png",
    "Yusuf Güler": "jjjjjjjj.png",
}

print(f"{len(ESLESTIRME)} profile avatar yuklenecek.\n")

for full_name, dosya_adi in ESLESTIRME.items():
    try:
        r = supabase.table("profiles").select("id").eq("full_name", full_name).limit(1).execute()
        if not r.data:
            print(f"  x '{full_name}' bulunamadı, atlanıyor")
            continue
        user_id = r.data[0]["id"]

        dosya_yolu = os.path.join(FOTO_KLASORU, dosya_adi)
        with open(dosya_yolu, "rb") as f:
            veri = f.read()

        icerik_tipi = "image/png" if dosya_adi.lower().endswith(".png") else "image/jpeg"
        uzanti = "png" if dosya_adi.lower().endswith(".png") else "jpg"
        path = f"{user_id}/avatar.{uzanti}"
        supabase.storage.from_(AVATAR_BUCKET).upload(
            path, veri, {"content-type": icerik_tipi, "upsert": "true"}
        )
        public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)
        avatar_url = f"{public_url}?t={int(time.time())}"

        supabase.table("profiles").update({"avatar_url": avatar_url}).eq("id", user_id).execute()
        print(f"  + {full_name}: avatar yüklendi")
    except Exception as e:
        print(f"  x Hata ({full_name}): {maskele(e)}")

print("\nTamamlandı!")
