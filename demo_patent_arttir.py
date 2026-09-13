"""Var olan bazı demo yazılımcı profillerine patent belgesi ekler.

Amaç: Patentli profil sayısını artırmak (demo/sunum için daha zengin görünüm).
Zaten var olan hesapları hedef alır, yeni kullanıcı OLUŞTURMAZ — sadece
`profiles.has_verified_patent` ve `profiles.patent_url` alanlarını doldurur.

DIKKAT: Bu script SUPABASE_SERVICE_KEY kullanir. Yalnizca gelistirme/demo
projeleri uzerinde calistirin.
"""

import io
import os
import sys

# Windows konsolu bazen cp1254 gibi bir kod sayfasi kullaniyor ve checkmark
# gibi Unicode karakterleri yazdiramiyor (UnicodeEncodeError). UTF-8'e zorluyoruz.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from supabase import create_client

load_dotenv()

PATENT_BUCKET = "patent-belgeleri"

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

# Patent verilecek hedef profiller — full_name'e göre eşleşiyor (demo_veri.json'daki
# ana 15 yazılımcı setinden, alanına uygun, çeşitlilik gözetilerek seçildi).
HEDEF_PATENTLER = [
    {
        "full_name": "Selin Yıldız",
        "baslik": "Görüntü Tabanlı Erken Teşhis Modeli için Veri Ön İşleme Yöntemi",
    },
    {
        "full_name": "Onur Kurt",
        "baslik": "Düşük Güç Tüketimli IoT Sensör Ağlarında Veri Toplama Yöntemi",
    },
    {
        "full_name": "Deniz Koç",
        "baslik": "Gerçek Zamanlı İşlem Anomalisi Tespiti için Hibrit Skor Yöntemi",
    },
    {
        "full_name": "Mehmet Demir",
        "baslik": "Çok Kiracılı Sistemlerde Otomatik Veritabanı Ölçekleme Yöntemi",
    },
]


def sahte_patent_pdf_uret(ad_soyad: str, baslik: str) -> bytes:
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    genislik, yukseklik = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(genislik / 2, yukseklik - 5 * cm, "PATENT BELGESİ")

    c.setFont("Helvetica", 11)
    c.drawCentredString(genislik / 2, yukseklik - 6.5 * cm, "(Demo/örnek belge — gerçek bir tescil değildir)")

    c.setFont("Helvetica", 13)
    c.drawCentredString(genislik / 2, yukseklik - 8.5 * cm, "Buluş Sahibi:")
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(genislik / 2, yukseklik - 9.5 * cm, ad_soyad)

    c.setFont("Helvetica", 13)
    c.drawCentredString(genislik / 2, yukseklik - 11.5 * cm, "Buluş Başlığı:")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(genislik / 2, yukseklik - 12.5 * cm, baslik)

    c.showPage()
    c.save()
    return tampon.getvalue()


print(f"{len(HEDEF_PATENTLER)} profile patent belgesi eklenecek.\n")

for hedef in HEDEF_PATENTLER:
    try:
        r = supabase.table("profiles").select("id, full_name").eq("full_name", hedef["full_name"]).limit(1).execute()
        if not r.data:
            print(f"  ✗ '{hedef['full_name']}' bulunamadı, atlanıyor")
            continue

        user_id = r.data[0]["id"]
        pdf = sahte_patent_pdf_uret(hedef["full_name"], hedef["baslik"])
        path = f"{user_id}/patent.pdf"

        supabase.storage.from_(PATENT_BUCKET).upload(
            path, pdf, {"content-type": "application/pdf", "upsert": "true"}
        )
        patent_url = supabase.storage.from_(PATENT_BUCKET).get_public_url(path)

        supabase.table("profiles").update(
            {"has_verified_patent": True, "patent_url": patent_url}
        ).eq("id", user_id).execute()

        print(f"  ✓ {hedef['full_name']} artık patentli")
    except Exception as e:
        print(f"  ✗ Hata ({hedef['full_name']}): {maskele(e)}")

print("\nTamamlandı!")
