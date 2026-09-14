"""Test/placeholder hesap adlarini (deneme, dual, ikiz vb.) normal ad-soyad
formatina cevirir ve CV/sertifika PDF'lerini yeni isimle yeniden uretir
(PDF icerigine eski isim gomulu oldugu icin tutarlilik icin gerekli).

Hedef eslesme full_name'e gore. Yeni kullanici OLUSTURMAZ, sadece var olan
profilleri gunceller.

DIKKAT: Bu script SUPABASE_SERVICE_KEY kullanir. Yalnizca gelistirme/demo
projeleri uzerinde calistirin.
"""

import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from supabase import create_client

load_dotenv()

CV_BUCKET = "cvs"
PORTFOLYO_BUCKET = "portfolyo-dosyalari"

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


def _metni_sar(metin: str, satir_uzunlugu: int) -> list[str]:
    kelimeler = metin.split()
    satirlar: list[str] = []
    guncel = ""
    for kelime in kelimeler:
        if len(guncel) + len(kelime) + 1 > satir_uzunlugu:
            satirlar.append(guncel)
            guncel = kelime
        else:
            guncel = f"{guncel} {kelime}".strip()
    if guncel:
        satirlar.append(guncel)
    return satirlar


def sahte_cv_pdf_uret(ad_soyad: str, bio: str, skills: list[str]) -> bytes:
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    genislik, yukseklik = A4
    y = yukseklik - 3 * cm

    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, y, ad_soyad)
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Hakkinda")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    for satir in _metni_sar(bio or "", 90):
        c.drawString(2 * cm, y, satir)
        y -= 0.5 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Beceriler")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, ", ".join(skills or []))

    c.showPage()
    c.save()
    return tampon.getvalue()


def sahte_sertifika_pdf_uret(ad_soyad: str, baslik: str, issuer: str, item_date: str) -> bytes:
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    genislik, yukseklik = A4

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(genislik / 2, yukseklik - 6 * cm, "KATILIM / BASARI SERTIFIKASI")

    c.setFont("Helvetica", 13)
    c.drawCentredString(genislik / 2, yukseklik - 8 * cm, "Bu belge asagidaki kisiye verilmistir:")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(genislik / 2, yukseklik - 9.5 * cm, ad_soyad)

    c.setFont("Helvetica", 13)
    c.drawCentredString(genislik / 2, yukseklik - 11.5 * cm, baslik)

    c.setFont("Helvetica-Oblique", 11)
    c.drawCentredString(genislik / 2, yukseklik - 13 * cm, f"{issuer} - {item_date}")

    c.showPage()
    c.save()
    return tampon.getvalue()


def dosya_yukle(bucket_id: str, path: str, veri: bytes) -> None:
    supabase.storage.from_(bucket_id).upload(
        path, veri, {"content-type": "application/pdf", "upsert": "true"}
    )


# --- ESKI ISIM -> YENI ISIM ESLEMESI ---
YENI_ISIMLER = {
    "deneme deneme": "Efe Karaca",
    "deneme4yazilimci": "Yusuf Güler",
    "yıldız koz": "Bora Aydın",
    "Dual Test Kullanici": "Cansu Erdoğan",
    "dual hesap": "Tuna Eren",
    "ikiz": "Mert Sönmez",
    "ceren soyak": "Melis Soysal",
}

print(f"{len(YENI_ISIMLER)} hesabin adi degistirilecek.\n")

for eski_isim, yeni_isim in YENI_ISIMLER.items():
    try:
        r = supabase.table("profiles").select("id, bio, skills").eq("full_name", eski_isim).limit(1).execute()
        if not r.data:
            print(f"  x '{eski_isim}' bulunamadi, atlaniyor")
            continue

        profil = r.data[0]
        user_id = profil["id"]

        supabase.table("profiles").update({"full_name": yeni_isim}).eq("id", user_id).execute()

        # CV PDF'ini yeni isimle yeniden uret (ayni path, upsert)
        cv_pdf = sahte_cv_pdf_uret(yeni_isim, profil.get("bio") or "", profil.get("skills") or [])
        dosya_yukle(CV_BUCKET, f"{user_id}/cv.pdf", cv_pdf)

        # Sertifika(lar)i yeni isimle yeniden uret
        sertifikalar = (
            supabase.table("portfolio_items")
            .select("id, title, issuer, item_date, file_url")
            .eq("developer_id", user_id)
            .eq("item_type", "certificate")
            .execute()
            .data
        )
        for sert in sertifikalar:
            if not sert.get("file_url"):
                continue
            sert_pdf = sahte_sertifika_pdf_uret(
                yeni_isim, sert["title"], sert.get("issuer") or "", sert.get("item_date") or ""
            )
            dosya_yukle(PORTFOLYO_BUCKET, f"{user_id}/sertifika.pdf", sert_pdf)

        print(f"  + '{eski_isim}' -> '{yeni_isim}' (CV + sertifika yeniden uretildi)")
    except Exception as e:
        print(f"  x Hata ({eski_isim}): {maskele(e)}")

print("\nTamamlandi!")
