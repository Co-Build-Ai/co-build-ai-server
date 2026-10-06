"""Ikinci parti profil fotografi yukleme - klasordeki yeni eklenen
fotograflari, cinsiyetle uyumlu sekilde secilmis, henuz avatar_url'i olmayan
demo profillere yukler. demo_profil_fotolari_yukle.py'nin devami.

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
FOTO_KLASORU = r"C:\Users\DELL\Downloads\profile pics"

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

# full_name -> kaynak dosya adi (cinsiyete gore elle eslendi)
ESLESTIRME = {
    # Erkek gorunumlu fotograflar
    "Ahmet Yılmaz": "Neo Reggae Roots artist of Paper Crown Records, Ra Jah_.jpg",
    "Emir Şahin": "Professor Alexandre - Física.jpg",
    "Cem Yalçın": "jpg(13)",
    "Onur Demirtaş": "jpg(14)",
    "Kerem Polat": "Are you job hunting_ Looking to level up_ Your professional head shot matters_ Make your LinkedIn profile give the best version of you possible and show prospective employers they are getting a pro.jpg",
    "Tolga Erdem": "Ready for a change of scenery_ 🏔️ If you’re eyeing a new role this quarter, your LinkedIn photo is your first interview_ Make it count. A modern, high-quality headshot shows recruiters you’re serious about your career and att.jpg",
    # Kadin gorunumlu fotograflar
    "Zeynep Arslan": "Asia Simone Burns.jpg",
    "Cansu Erdoğan": "Professional Portrait Photo on Lummi(2).jpg",
    "Selin Doğan": "jpg(11)",
    "Gizem Aksoy": "jpg(12)",
    "Merve Doğan": "New Headshots 👩🏿_💻💾 Which one should I use for my LinkedIn Profile Pic_ The 1st one or 2nd_.jpg",
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

        path = f"{user_id}/avatar.jpg"
        supabase.storage.from_(AVATAR_BUCKET).upload(
            path, veri, {"content-type": "image/jpeg", "upsert": "true"}
        )
        public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)
        avatar_url = f"{public_url}?t={int(time.time())}"

        supabase.table("profiles").update({"avatar_url": avatar_url}).eq("id", user_id).execute()
        print(f"  + {full_name}: avatar yüklendi")
    except Exception as e:
        print(f"  x Hata ({full_name}): {maskele(e)}")

print("\nTamamlandı!")
