"""Ucuncu parti profil fotografi yukleme - klasordeki yeni eklenen
fotograflari, cinsiyetle uyumlu sekilde secilmis, henuz avatar_url'i olmayan
demo profillere yukler. demo_profil_fotolari_yukle.py / _2.py'nin devami.

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


def dosya_bul(on_ek: str) -> str | None:
    """Dosya adini basiyla eslestirir (emoji/ozel karakter iceren uzun
    adlarin encoding sorununa takilmadan, os.scandir uzerinden byte-safe)."""
    for entry in os.scandir(FOTO_KLASORU):
        if entry.name.startswith(on_ek):
            return entry.path
    return None


# full_name -> dosya adi baslangici (cinsiyete gore elle eslendi)
ESLESTIRME = {
    # Erkek gorunumlu fotograflar
    "Ali Vural": "AI-Enhanced Professional Portraits",
    "Burak Şahin": "David Shull",
    "Can Öztürk": "LinkedIn Profile Picture Ai genrated",
    "Deniz Koç": "New office headshots",
    "Mehmet Demir": "Q&A with Lawyer",
    "Mert Sönmez": "Some recent headshots! Send me a message if you or your club wants to host a headshot event!(1)",
    "Tuna Eren": "Your ERAS headshot",
    # Kadin gorunumlu fotograflar
    "Aslı Tekin": "18 years old girl in hijab",
    "Ayşe Çelik": "Business Headshots",
    "Ayşe Yılmaz": "Chicago Business Headshot",
    "Elif Toprak": "Headshot.jpg",
    "Fatma Öz": "Professional Corporate Headshots",
    "Gizem Aktaş": "Rrita Hashani",
    "Nazlı Er": "Some recent headshots! Send me a message if you or your club wants to host a headshot event!.jpg",
    "Yasemin Ak": "Thank you to @tulanechiomega",
}

print(f"{len(ESLESTIRME)} profile avatar yuklenecek.\n")

for full_name, on_ek in ESLESTIRME.items():
    try:
        r = supabase.table("profiles").select("id").eq("full_name", full_name).limit(1).execute()
        if not r.data:
            print(f"  x '{full_name}' bulunamadı, atlanıyor")
            continue
        user_id = r.data[0]["id"]

        dosya_yolu = dosya_bul(on_ek)
        if not dosya_yolu:
            print(f"  x '{full_name}' için dosya bulunamadı ({on_ek}), atlanıyor")
            continue

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
