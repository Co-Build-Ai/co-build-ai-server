"""Supabase'e demo kullanici ve proje verisi yukler.

DIKKAT: Bu script SUPABASE_SERVICE_KEY kullanir. Bu anahtar Row Level
Security'yi bypass eder ve tam admin yetkisine sahiptir. Yalnizca gelistirme /
demo projeleri uzerinde calistirin.
"""

import io
import json
import os
import random
import sys

from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from supabase import create_client

load_dotenv()

CV_BUCKET = "cvs"
PORTFOLYO_BUCKET = "portfolyo-dosyalari"

# --- ORTAM DEGISKENLERI ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "DemoSifre123!")

_eksik = [
    isim
    for isim, deger in (
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY),
    )
    if not deger
]
if _eksik:
    sys.exit(
        f"HATA: eksik ortam degiskeni: {', '.join(_eksik)}\n"
        "Cozum: '.env.example' dosyasini '.env' olarak kopyalayip degerleri doldurun."
    )

# Sablon degerin kazara kullanilmasini yakala. Kalibi burada literal olarak
# yazmiyoruz; aksi halde pre-commit sir taramasi bu dosyayi yanlis pozitif isaretler.
_SABLON_ISARETLERI = ("replace_me", "your-service-key", "buraya", "changeme")
if any(isaret in SUPABASE_SERVICE_KEY.lower() for isaret in _SABLON_ISARETLERI):
    sys.exit("HATA: SUPABASE_SERVICE_KEY hala sablon degerinde. .env dosyasini doldurun.")


# --- SIR MASKELEME ---
# Supabase istemcisinden gelen hata mesajlari istek baglamini icerebilir.
# Ekrana/log'a basilan hicbir metinde sir gorunmemesini garanti ediyoruz.
_GIZLI_DEGERLER = tuple(
    deger for deger in (SUPABASE_SERVICE_KEY, DEMO_PASSWORD) if deger and len(deger) >= 8
)


def maskele(metin: object) -> str:
    """Verilen metindeki tum sir degerlerini '***GIZLI***' ile degistirir."""
    sonuc = str(metin)
    for sir in _GIZLI_DEGERLER:
        sonuc = sonuc.replace(sir, "***GIZLI***")
    return sonuc


# --- SAHTE PDF URETIMI (CV / SERTIFIKA) ---
# Demo profillerinin bos gorunmemesi icin gercekten indirilebilir/goruntulenebilir
# birer PDF uretip Supabase Storage'a yukluyoruz. Icerik tamamen demo_veri.json'dan
# geliyor, gercek bir kisiye/kuruma ait degil.
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
    for satir in _metni_sar(bio, 90):
        c.drawString(2 * cm, y, satir)
        y -= 0.5 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Beceriler")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, ", ".join(skills))

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


def bucket_hazirla(bucket_id: str) -> None:
    """Bucket yoksa public olarak olusturur; varsa sessizce gecer."""
    try:
        supabase.storage.create_bucket(bucket_id, options={"public": True})
        print(f"  ✓ '{bucket_id}' bucket'i olusturuldu")
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            print(f"  ⚠ '{bucket_id}' bucket'i kontrol edilirken uyari: {maskele(e)}")


def kullanici_id_bul_veya_olustur(email: str, password: str) -> tuple[str, bool]:
    """Auth kullanicisi yoksa olusturur, varsa mevcut id'sini bulur.

    Script'in birden fazla kez calistirilabilmesi (idempotent olmasi) icin:
    demo hesaplar daha once olusturulmus olabilir, bu durumda yeniden
    auth.admin.create_user cagirmak hata verir. Boyle bir hata alinirsa
    mevcut kullaniciyi e-postaya gore arayip id'sini geri donuyoruz.
    """
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        return auth_response.user.id, True
    except Exception as e:
        hata_metni = str(e).lower()
        if "already" not in hata_metni and "exists" not in hata_metni and "registered" not in hata_metni:
            raise

        sayfa = 1
        while True:
            sonuc = supabase.auth.admin.list_users(page=sayfa, per_page=200)
            kullanicilar = sonuc if isinstance(sonuc, list) else getattr(sonuc, "users", [])
            if not kullanicilar:
                break
            for kullanici in kullanicilar:
                if kullanici.email == email:
                    return kullanici.id, False
            sayfa += 1

        raise RuntimeError(f"'{email}' zaten kayitli ama admin kullanici listesinde bulunamadi") from e


def dosya_yukle_ve_url_al(bucket_id: str, path: str, veri: bytes) -> str | None:
    try:
        supabase.storage.from_(bucket_id).upload(
            path, veri, {"content-type": "application/pdf", "upsert": "true"}
        )
        return supabase.storage.from_(bucket_id).get_public_url(path)
    except Exception as e:
        print(f"  ✗ Dosya yuklenemedi ({path}): {maskele(e)}")
        return None


# --- GUVENLIK ONAYI ---
# Yanlislikla canli bir projeye yazmayi onlemek icin acik onay istenir.
def onay_al() -> None:
    if os.getenv("DEMO_SEED_ONAY", "").strip().lower() in ("1", "true", "evet", "yes"):
        return
    print("Bu islem asagidaki Supabase projesine ADMIN yetkisiyle yazacak:")
    print(f"  {SUPABASE_URL}")
    print("  (service key yuklendi, degeri gosterilmiyor)")
    try:
        cevap = input("Devam etmek icin 'EVET' yazin: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nIptal edildi (onay alinamadi).")
    if cevap != "EVET":
        sys.exit("Iptal edildi.")


onay_al()

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("Storage bucket'lari kontrol ediliyor...")
bucket_hazirla(CV_BUCKET)
bucket_hazirla(PORTFOLYO_BUCKET)

# --- VERIYI DOSYADAN OKU ---
with open("demo_veri.json", "r", encoding="utf-8") as f:
    data = json.load(f)

developers = data["developers"]
founders = data["founders"]
projects = data["projects"]

print(f"\n{len(developers)} yazılımcı, {len(founders)} fikir sahibi, {len(projects)} proje yüklenecek.\n")

# --- YAZILIMCI HESAPLARI OLUŞTUR ---
print("Yazılımcı hesapları oluşturuluyor...")
developer_ids = []
for i, dev in enumerate(developers):
    email = f"demo.yazilimci{i}@cobuildai-demo.com"
    try:
        user_id, yeni_mi = kullanici_id_bul_veya_olustur(email, DEMO_PASSWORD)
        developer_ids.append(user_id)

        # Sahte CV PDF'i uret ve yukle
        cv_pdf = sahte_cv_pdf_uret(dev["full_name"], dev["bio"], dev["skills"])
        cv_url = dosya_yukle_ve_url_al(CV_BUCKET, f"{user_id}/cv.pdf", cv_pdf)

        supabase.table("profiles").upsert({
            "id": user_id,
            "user_type": "developer",
            "full_name": dev["full_name"],
            "bio": dev["bio"],
            "skills": dev["skills"],
            "cv_url": cv_url,
        }).execute()

        # Script yeniden calistirildiginda portfolyo ogelerinin
        # kopyalanmamasi icin oncekileri silip yeniden ekliyoruz.
        supabase.table("portfolio_items").delete().eq("developer_id", user_id).execute()

        # Portfolyo ogelerini ekle (proje + sertifika)
        for j, oge in enumerate(dev.get("portfolio", [])):
            file_url = None
            if oge["item_type"] == "certificate":
                sertifika_pdf = sahte_sertifika_pdf_uret(
                    dev["full_name"], oge["title"], oge["issuer"], oge["item_date"]
                )
                file_url = dosya_yukle_ve_url_al(
                    PORTFOLYO_BUCKET, f"{user_id}/{j}.pdf", sertifika_pdf
                )

            supabase.table("portfolio_items").insert({
                "developer_id": user_id,
                "title": oge["title"],
                "description": oge.get("description"),
                "item_type": oge["item_type"],
                "issuer": oge.get("issuer"),
                "item_date": oge.get("item_date"),
                "file_url": file_url,
            }).execute()

        durum = "oluşturuldu" if yeni_mi else "güncellendi"
        print(f"  ✓ {dev['full_name']} {durum} (CV + {len(dev.get('portfolio', []))} portfolyo öğesi)")
    except Exception as e:
        print(f"  ✗ Hata ({dev['full_name']}): {maskele(e)}")

# --- FİKİR SAHİBİ HESAPLARI OLUŞTUR ---
print("\nFikir sahibi hesapları oluşturuluyor...")
founder_ids = []
for i, founder in enumerate(founders):
    email = f"demo.girisimci{i}@cobuildai-demo.com"
    try:
        user_id, yeni_mi = kullanici_id_bul_veya_olustur(email, DEMO_PASSWORD)
        founder_ids.append(user_id)

        supabase.table("profiles").upsert({
            "id": user_id,
            "user_type": "founder",
            "full_name": founder["full_name"],
        }).execute()

        durum = "oluşturuldu" if yeni_mi else "güncellendi"
        print(f"  ✓ {founder['full_name']} {durum}")
    except Exception as e:
        print(f"  ✗ Hata ({founder['full_name']}): {maskele(e)}")

# --- PROJELERİ, RASTGELE FİKİR SAHİPLERİNE BAĞLAYARAK EKLE ---
print("\nProjeler ekleniyor...")
for proj in projects:
    if not founder_ids:
        print("  ✗ Hiç fikir sahibi oluşturulamadığı için projeler eklenemiyor.")
        break
    random_founder = random.choice(founder_ids)
    try:
        supabase.table("projects").insert({
            "founder_id": random_founder,
            "title": proj["title"],
            "raw_idea": proj["raw_idea"],
            "required_skills": proj["required_skills"],
            "status": "published",
        }).execute()
        print(f"  ✓ {proj['title']} eklendi")
    except Exception as e:
        print(f"  ✗ Hata ({proj['title']}): {maskele(e)}")

print("\nTamamlandı!")
print(f"Toplam: {len(developer_ids)} yazılımcı, {len(founder_ids)} fikir sahibi, {len(projects)} proje işlendi.")
