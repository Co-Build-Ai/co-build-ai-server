"""Bora Aydın profiline 2 sinyal işleme patenti ve 4 AI/sinyal işleme +
pazarlama projesi ekler.

Profiles.patent_url tek bir patent alanı olduğu için birincil patent oraya
yazılır (has_verified_patent rozetini/çarpanını tetikler); ikinci patent,
portfolio_items üzerinde "certificate" tipinde (issuer: Türk Patent ve
Marka Kurumu) bir belge olarak temsil edilir - şema değişikliği gerektirmez.

Türkçe karakterler için Arial fontu kullanılır (bkz. demo_pdf_fontlarini_duzelt.py
- Helvetica bu karakterleri desteklemiyordu).

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
PATENT_BUCKET = "patent-belgeleri"
DEVELOPER_ID = "f934028e-8115-4dfb-a701-4feca1c55bca"  # Bora Aydın
AD_SOYAD = "Bora Aydın"

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

_FONT_DIZINI = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("Arial", f"{_FONT_DIZINI}/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", f"{_FONT_DIZINI}/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", f"{_FONT_DIZINI}/ariali.ttf"))


def sahte_patent_pdf_uret(ad_soyad: str, baslik: str) -> bytes:
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    genislik, yukseklik = A4

    c.setFont("Arial-Bold", 20)
    c.drawCentredString(genislik / 2, yukseklik - 5 * cm, "PATENT BELGESİ")

    c.setFont("Arial", 11)
    c.drawCentredString(genislik / 2, yukseklik - 6.5 * cm, "(Demo/örnek belge — gerçek bir tescil değildir)")

    c.setFont("Arial", 13)
    c.drawCentredString(genislik / 2, yukseklik - 8.5 * cm, "Buluş Sahibi:")
    c.setFont("Arial-Bold", 16)
    c.drawCentredString(genislik / 2, yukseklik - 9.5 * cm, ad_soyad)

    c.setFont("Arial", 13)
    c.drawCentredString(genislik / 2, yukseklik - 11.5 * cm, "Buluş Başlığı:")
    c.setFont("Arial-Bold", 13)
    c.drawCentredString(genislik / 2, yukseklik - 12.5 * cm, baslik)

    c.showPage()
    c.save()
    return tampon.getvalue()


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


# --- 1) BİRİNCİL PATENT (profiles.patent_url + has_verified_patent) ---
BIRINCIL_PATENT_BASLIK = "Gürültülü Ortamlarda Ses Sinyali Filtreleme Yöntemi"

patent_pdf = sahte_patent_pdf_uret(AD_SOYAD, BIRINCIL_PATENT_BASLIK)
patent_url = dosya_yukle_ve_url_al(PATENT_BUCKET, f"{DEVELOPER_ID}/patent.pdf", patent_pdf)
supabase.table("profiles").update({
    "has_verified_patent": True,
    "patent_url": patent_url,
}).eq("id", DEVELOPER_ID).execute()
print(f"+ Birincil patent eklendi: {BIRINCIL_PATENT_BASLIK}")

# --- 2) İKİNCİL PATENT (portfolio_items, certificate tipinde temsil edilir) ---
IKINCIL_PATENT = {
    "title": "Gerçek Zamanlı Titreşim Sinyali Anomali Tespiti İçin Donanım Bağımsız Yöntem (Patent)",
    "issuer": "Türk Patent ve Marka Kurumu",
    "item_date": "2023-11-14",
}
supabase.table("portfolio_items").delete().eq("developer_id", DEVELOPER_ID).eq("title", IKINCIL_PATENT["title"]).execute()
sert_pdf = sahte_patent_pdf_uret(AD_SOYAD, IKINCIL_PATENT["title"].replace(" (Patent)", ""))
sert_url = dosya_yukle_ve_url_al(PORTFOLYO_BUCKET, f"{DEVELOPER_ID}/patent2.pdf", sert_pdf)
supabase.table("portfolio_items").insert({
    "developer_id": DEVELOPER_ID,
    "title": IKINCIL_PATENT["title"],
    "description": None,
    "item_type": "certificate",
    "issuer": IKINCIL_PATENT["issuer"],
    "item_date": IKINCIL_PATENT["item_date"],
    "file_url": sert_url,
}).execute()
print(f"+ İkincil patent eklendi: {IKINCIL_PATENT['title']}")

# --- 3) PROJELER (AI + sinyal işleme + pazarlama) ---
PROJELER = [
    {
        "title": "Ses Sinyalinden Duygu Tanıma Uygulaması",
        "description": "Kullanıcının konuşma sesinden anlık duygu durumunu (mutlu, öfkeli, nötr vb.) tahmin eden, sinyal işleme ve derin öğrenme tabanlı bir mobil uygulama.",
    },
    {
        "title": "EKG Sinyali Anomali Tespit Sistemi",
        "description": "Giyilebilir cihazlardan alınan EKG sinyallerinde anormal ritim paternlerini gerçek zamanlı tespit edip uyarı üreten bir sistem.",
    },
    {
        "title": "Reklam Kampanyası Performans Tahmin Aracı",
        "description": "Geçmiş reklam verilerini (gösterim, tıklama, dönüşüm) analiz ederek yeni kampanyaların beklenen performansını tahmin eden bir makine öğrenmesi aracı.",
    },
    {
        "title": "Müşteri Segmentasyonu ve Hedefli Pazarlama Paneli",
        "description": "Müşteri davranış verilerini kümeleme algoritmalarıyla segmentlere ayırıp her segment için hedefli kampanya önerileri sunan bir pazarlama paneli.",
    },
]

for proje in PROJELER:
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
    print(f"+ Proje eklendi: {proje['title']}")

print("\nTamamlandı!")
