"""Var olan TUM CV, sertifika ve patent PDF'lerini duzgun (Turkce destekli)
fontla yeniden uretir.

Onceki demo script'leri (demo_kullanici_uret.py, demo_bos_profil_doldur.py,
demo_patent_arttir.py, demo_isim_degistir.py) reportlab'in varsayilan
Helvetica fontunu kullaniyordu; bu font Turkce'ye ozgu bazi harfleri
(g-breve, s-cedilla, noktasiz i, buyuk I-nokta) icermiyor ve PDF'lerde
bozuk/eksik gorunebiliyordu. Bu script, Windows'un Arial fontunu (Turkce
karakterleri tam destekler) kullanarak MEVCUT butun dosyalari, veritabanindaki
guncel icerikle (isim/bio/skills/baslik) AYNI storage path'ine yeniden yukler
- yeni kayit olusturmaz, URL'ler degismez.

Path'ler, veritabaninda zaten kayitli olan public URL'lerden ayiklanir (tahmin
etmez), bu yuzden herhangi bir onceki script'in dosya adlandirma deseninden
bagimsiz calisir.

DIKKAT: Bu script SUPABASE_SERVICE_KEY kullanir. Yalnizca gelistirme/demo
projeleri uzerinde calistirin.
"""

import io
import os
import sys
from urllib.parse import urlparse

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

CV_BUCKET = "cvs"
PORTFOLYO_BUCKET = "portfolyo-dosyalari"
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

# --- TURKCE DESTEKLI FONT KAYDI (Windows Arial) ---
_FONT_DIZINI = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("Arial", f"{_FONT_DIZINI}/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", f"{_FONT_DIZINI}/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", f"{_FONT_DIZINI}/ariali.ttf"))


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

    c.setFont("Arial-Bold", 18)
    c.drawString(2 * cm, y, ad_soyad)
    y -= 1 * cm

    c.setFont("Arial-Bold", 12)
    c.drawString(2 * cm, y, "Hakkında")
    y -= 0.7 * cm
    c.setFont("Arial", 10)
    for satir in _metni_sar(bio or "Henüz bir tanıtım eklenmedi.", 90):
        c.drawString(2 * cm, y, satir)
        y -= 0.5 * cm

    y -= 0.5 * cm
    c.setFont("Arial-Bold", 12)
    c.drawString(2 * cm, y, "Beceriler")
    y -= 0.7 * cm
    c.setFont("Arial", 10)
    c.drawString(2 * cm, y, ", ".join(skills or []))

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


def url_den_path_cikar(public_url: str, bucket_id: str) -> str | None:
    """Supabase public URL'inden bucket sonrasi gercek storage path'ini cikarir."""
    isaret = f"/public/{bucket_id}/"
    if isaret not in public_url:
        return None
    yol = public_url.split(isaret, 1)[1]
    # Sondaki ?t=... gibi cache-busting parametrelerini at
    return urlparse(yol).path


def dosya_yukle(bucket_id: str, path: str, veri: bytes) -> bool:
    try:
        supabase.storage.from_(bucket_id).upload(
            path, veri, {"content-type": "application/pdf", "upsert": "true"}
        )
        return True
    except Exception as e:
        print(f"    x Yuklenemedi ({bucket_id}/{path}): {maskele(e)}")
        return False


# Patent basliklari veritabaninda saklanmiyor (sadece PDF icine gomulu),
# bu yuzden demo_patent_arttir.py'deki orijinal metinle ayni sekilde
# burada da elle tutuluyor.
PATENT_BASLIKLARI = {
    "Selin Yıldız": "Görüntü Tabanlı Erken Teşhis Modeli için Veri Ön İşleme Yöntemi",
    "Onur Kurt": "Düşük Güç Tüketimli IoT Sensör Ağlarında Veri Toplama Yöntemi",
    "Deniz Koç": "Gerçek Zamanlı İşlem Anomalisi Tespiti için Hibrit Skor Yöntemi",
    "Mehmet Demir": "Çok Kiracılı Sistemlerde Otomatik Veritabanı Ölçekleme Yöntemi",
}

# --- 1) CV'LER ---
print("CV'ler yeniden uretiliyor...")
cv_profilleri = (
    supabase.table("profiles")
    .select("id, full_name, bio, skills, cv_url")
    .not_.is_("cv_url", "null")
    .execute()
    .data
)
for p in cv_profilleri:
    path = url_den_path_cikar(p["cv_url"], CV_BUCKET)
    if not path:
        print(f"  x {p['full_name']}: CV path'i cozulemedi, atlaniyor")
        continue
    pdf = sahte_cv_pdf_uret(p["full_name"] or "", p.get("bio") or "", p.get("skills") or [])
    if dosya_yukle(CV_BUCKET, path, pdf):
        print(f"  + {p['full_name']}: CV yenilendi")

# --- 2) PATENT BELGELERI ---
print("\nPatent belgeleri yeniden uretiliyor...")
patent_profilleri = (
    supabase.table("profiles")
    .select("id, full_name, patent_url")
    .not_.is_("patent_url", "null")
    .execute()
    .data
)
for p in patent_profilleri:
    baslik = PATENT_BASLIKLARI.get(p["full_name"])
    if not baslik:
        print(f"  x {p['full_name']}: bilinen bir patent basligi yok, atlaniyor")
        continue
    path = url_den_path_cikar(p["patent_url"], PATENT_BUCKET)
    if not path:
        print(f"  x {p['full_name']}: patent path'i cozulemedi, atlaniyor")
        continue
    pdf = sahte_patent_pdf_uret(p["full_name"] or "", baslik)
    if dosya_yukle(PATENT_BUCKET, path, pdf):
        print(f"  + {p['full_name']}: patent belgesi yenilendi")

# --- 3) SERTIFIKALAR ---
print("\nSertifikalar yeniden uretiliyor...")
sertifikalar = (
    supabase.table("portfolio_items")
    .select("id, developer_id, title, issuer, item_date, file_url")
    .eq("item_type", "certificate")
    .not_.is_("file_url", "null")
    .execute()
    .data
)
gelistirici_ad_cache: dict[str, str] = {}
for s in sertifikalar:
    dev_id = s["developer_id"]
    if dev_id not in gelistirici_ad_cache:
        r = supabase.table("profiles").select("full_name").eq("id", dev_id).limit(1).execute()
        gelistirici_ad_cache[dev_id] = r.data[0]["full_name"] if r.data else "Bilinmeyen"
    ad_soyad = gelistirici_ad_cache[dev_id]

    path = url_den_path_cikar(s["file_url"], PORTFOLYO_BUCKET)
    if not path:
        print(f"  x {ad_soyad} / {s['title']}: path cozulemedi (gercek bir dosya olmayabilir), atlaniyor")
        continue

    pdf = sahte_sertifika_pdf_uret(ad_soyad, s["title"], s.get("issuer") or "", s.get("item_date") or "")
    if dosya_yukle(PORTFOLYO_BUCKET, path, pdf):
        print(f"  + {ad_soyad} / {s['title']}: sertifika yenilendi")

print("\nTamamlandı!")
