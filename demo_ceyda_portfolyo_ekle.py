"""Ceyda Alemdar profiline birkac gercekci proje ve sertifika daha ekler.

Onceki script'lerdeki PDF'ler reportlab'in varsayilan Helvetica fontuyla
uretiliyordu; bu font Turkce'ye ozgu bazi harfleri (g-breve, s-cedilla,
noktasiz i) icermiyor ve PDF'te bozuk/eksik gorunebiliyordu. Bu script
Windows'un Arial fontunu (Turkce karakterleri tam destekler) reportlab'e
gomerek bu sorunu kokunden cozuyor - harfleri kisitlamiyor, dogru fontu
kullaniyor.

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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from supabase import create_client

load_dotenv()

PORTFOLYO_BUCKET = "portfolyo-dosyalari"
DEVELOPER_ID = "dea88211-a103-4787-a4b9-0bb95f5a544e"  # Ceyda Alemdar
AD_SOYAD = "Ceyda Alemdar"

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

# --- TURKCE DESTEKLI FONT KAYDI (Windows Arial) ---
_FONT_DIZINI = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("Arial", f"{_FONT_DIZINI}/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", f"{_FONT_DIZINI}/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", f"{_FONT_DIZINI}/ariali.ttf"))


def sahte_sertifika_pdf_uret(ad_soyad: str, baslik: str, issuer: str, item_date: str) -> bytes:
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    genislik, yukseklik = A4

    c.setFont("Arial-Bold", 22)
    c.drawCentredString(genislik / 2, yukseklik - 6 * cm, "KATILIM / BAŞARI SERTİFİKASI")

    c.setFont("Arial", 13)
    c.drawCentredString(genislik / 2, yukseklik - 8 * cm, "Bu belge aşağıdaki kişiye verilmiştir:")

    c.setFont("Arial-Bold", 18)
    c.drawCentredString(genislik / 2, yukseklik - 9.5 * cm, ad_soyad)

    c.setFont("Arial", 13)
    c.drawCentredString(genislik / 2, yukseklik - 11.5 * cm, baslik)

    c.setFont("Arial-Italic", 11)
    c.drawCentredString(genislik / 2, yukseklik - 13 * cm, f"{issuer} - {item_date}")

    c.showPage()
    c.save()
    return tampon.getvalue()


def dosya_yukle_ve_url_al(bucket_id: str, path: str, veri: bytes) -> str | None:
    try:
        supabase.storage.from_(bucket_id).upload(
            path, veri, {"content-type": "application/pdf", "upsert": "true"}
        )
        return supabase.storage.from_(bucket_id).get_public_url(path)
    except Exception as e:
        print(f"  x Dosya yuklenemedi ({path}): {maskele(e)}")
        return None


YENI_PROJELER = [
    {
        "title": "Müşteri Kaybı (Churn) Tahmin Sistemi",
        "description": "E-ticaret şirketleri için müşteri kaybı riskini geçmiş davranış verilerinden önceden tahmin eden, scikit-learn ile geliştirilmiş bir makine öğrenmesi modeli.",
    },
    {
        "title": "Türkçe Metinlerde Duygu Analizi API'si",
        "description": "Ürün yorumlarını pozitif, negatif ve nötr olarak sınıflandıran, FastAPI üzerinden servis edilen bir doğal dil işleme modeli.",
    },
]

YENI_SERTIFIKALAR = [
    {
        "title": "IBM Data Science Professional Certificate",
        "issuer": "IBM (Coursera)",
        "item_date": "2023-10-05",
    },
    {
        "title": "Deep Learning Specialization",
        "issuer": "DeepLearning.AI (Coursera)",
        "item_date": "2024-01-18",
    },
]

print(f"'{AD_SOYAD}' profiline {len(YENI_PROJELER)} proje + {len(YENI_SERTIFIKALAR)} sertifika ekleniyor.\n")

for proje in YENI_PROJELER:
    try:
        supabase.table("portfolio_items").delete().eq("developer_id", DEVELOPER_ID).eq("title", proje["title"]).execute()
        supabase.table("portfolio_items").insert({
            "developer_id": DEVELOPER_ID,
            "title": proje["title"],
            "description": proje["description"],
            "item_type": "project",
            "issuer": None,
            "item_date": None,
            "file_url": None,
        }).execute()
        print(f"  + Proje eklendi: {proje['title']}")
    except Exception as e:
        print(f"  x Hata (proje: {proje['title']}): {maskele(e)}")

for i, sert in enumerate(YENI_SERTIFIKALAR, start=2):
    try:
        supabase.table("portfolio_items").delete().eq("developer_id", DEVELOPER_ID).eq("title", sert["title"]).execute()

        sert_pdf = sahte_sertifika_pdf_uret(AD_SOYAD, sert["title"], sert["issuer"], sert["item_date"])
        sert_url = dosya_yukle_ve_url_al(PORTFOLYO_BUCKET, f"{DEVELOPER_ID}/sertifika{i}.pdf", sert_pdf)

        supabase.table("portfolio_items").insert({
            "developer_id": DEVELOPER_ID,
            "title": sert["title"],
            "description": None,
            "item_type": "certificate",
            "issuer": sert["issuer"],
            "item_date": sert["item_date"],
            "file_url": sert_url,
        }).execute()
        print(f"  + Sertifika eklendi: {sert['title']}")
    except Exception as e:
        print(f"  x Hata (sertifika: {sert['title']}): {maskele(e)}")

# Mevcut ilk sertifikayi da duzgun fontla yeniden uret (eski Helvetica
# ciktisinda Turkce karakterler bozuk gorunuyordu).
try:
    eski_sert = (
        supabase.table("portfolio_items")
        .select("title, issuer, item_date")
        .eq("developer_id", DEVELOPER_ID)
        .eq("item_type", "certificate")
        .eq("title", "Makine Öğrenmesi Temelleri")
        .limit(1)
        .execute()
        .data
    )
    if eski_sert:
        s = eski_sert[0]
        sert_pdf = sahte_sertifika_pdf_uret(AD_SOYAD, s["title"], s["issuer"], s["item_date"])
        dosya_yukle_ve_url_al(PORTFOLYO_BUCKET, f"{DEVELOPER_ID}/sertifika.pdf", sert_pdf)
        print("  + Mevcut sertifika (Makine Öğrenmesi Temelleri) düzgün fontla yeniden üretildi")
except Exception as e:
    print(f"  x Hata (eski sertifika yenileme): {maskele(e)}")

print("\nTamamlandı!")
