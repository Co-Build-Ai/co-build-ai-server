"""Bos/yari-bos test profillerini (deneme, ikiz, dual hesap vb.) doldurur.

Amac: Platformda kayitli ama bio/skill/CV/portfolyo'su tamamen bos gorunen
birkac test hesabini, demo/sunum icin dolu ve gercekci gostermek.

Hedef profiller full_name'e gore eslesir; ID uretmez, YENI kullanici
OLUSTURMAZ - sadece var olan profillere yazar.

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


def dosya_yukle_ve_url_al(bucket_id: str, path: str, veri: bytes) -> str | None:
    try:
        supabase.storage.from_(bucket_id).upload(
            path, veri, {"content-type": "application/pdf", "upsert": "true"}
        )
        return supabase.storage.from_(bucket_id).get_public_url(path)
    except Exception as e:
        print(f"  x Dosya yuklenemedi ({path}): {maskele(e)}")
        return None


# --- HEDEF PROFILLER ---
# Bio/skills tamamen bos olan (gercek kullanici girdisi olmayan) test
# hesaplari - hepsi sifirdan dolduruluyor.
HEDEFLER = [
    {
        "full_name": "deneme deneme",
        "bio": "Full-stack web geliştirici olarak modern JavaScript ekosisteminde ürünler geliştiriyorum, hem arayüz hem sunucu tarafında rahatım.",
        "skills": ["React", "Node.js", "Express", "MongoDB"],
        "proje": {
            "title": "Basit Blog Platformu",
            "description": "Kullanıcıların yazı paylaşıp yorum yapabildiği, React ve Node.js ile geliştirilmiş bir blog uygulaması.",
        },
        "sertifika": {
            "title": "Meta Front-End Developer Sertifikası",
            "issuer": "Meta (Coursera)",
            "item_date": "2023-09-12",
        },
    },
    {
        "full_name": "yıldız koz",
        "bio": "Mobil uygulama geliştirme konusunda tutkulu bir yazılımcıyım, Flutter ile hem Android hem iOS için tek kod tabanından uygulamalar üretiyorum.",
        "skills": ["Flutter", "Dart", "Firebase", "REST API"],
        "proje": {
            "title": "Hava Durumu Mobil Uygulaması",
            "description": "Konum bazlı anlık hava durumu ve haftalık tahmin gösteren, Flutter ile geliştirilmiş bir mobil uygulama.",
        },
        "sertifika": {
            "title": "Flutter ile Mobil Uygulama Geliştirme",
            "issuer": "Udemy",
            "item_date": "2022-11-03",
        },
    },
    {
        "full_name": "Dual Test Kullanici",
        "bio": "Backend geliştirici olarak API tasarımı ve veritabanı optimizasyonu üzerine çalışıyorum, Python ekosistemini aktif kullanıyorum.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "proje": {
            "title": "Randevu Yönetim API'si",
            "description": "Küçük klinikler için randevu oluşturma, iptal ve hatırlatma bildirimlerini yöneten bir REST API.",
        },
        "sertifika": {
            "title": "Python ile Backend Geliştirme Sertifikası",
            "issuer": "BTK Akademi",
            "item_date": "2023-04-20",
        },
    },
    {
        "full_name": "dual hesap",
        "bio": "Kullanıcı deneyimine önem veren bir frontend geliştiricisiyim, tasarım sistemleri kurup Figma'dan koda geçişte rahatım.",
        "skills": ["Vue.js", "TailwindCSS", "JavaScript", "Figma"],
        "proje": {
            "title": "Kişisel Finans Takip Arayüzü",
            "description": "Kullanıcının gelir/gider kayıtlarını grafiklerle özetleyen, Vue.js ve TailwindCSS ile geliştirilmiş bir arayüz.",
        },
        "sertifika": {
            "title": "UI/UX Tasarım Temelleri",
            "issuer": "Google (Coursera)",
            "item_date": "2023-02-08",
        },
    },
    {
        "full_name": "ikiz",
        "bio": "DevOps ve bulut altyapısı üzerine çalışan bir mühendisim, CI/CD hatları kurup konteynerleştirilmiş sistemleri yönetiyorum.",
        "skills": ["AWS", "Docker", "Kubernetes", "Terraform"],
        "proje": {
            "title": "Otomatik Dağıtım Hattı (CI/CD)",
            "description": "GitHub Actions ve Terraform ile altyapıyı kod olarak yöneten, Kubernetes'e otomatik dağıtım yapan bir hat.",
        },
        "sertifika": {
            "title": "AWS Certified Cloud Practitioner",
            "issuer": "Amazon Web Services",
            "item_date": "2022-08-15",
        },
    },
    {
        "full_name": "ikiz yıldız",
        "bio": "Veri bilimi ve makine öğrenmesi alanında çalışan bir geliştiriciyim, gerçek dünya verileriyle tahmin modelleri kuruyorum.",
        "skills": ["Python", "Pandas", "Scikit-learn", "Jupyter"],
        "proje": {
            "title": "Öğrenci Başarı Tahmin Modeli",
            "description": "Devamsızlık ve ödev verilerini kullanarak öğrenci başarısını tahmin eden bir makine öğrenmesi modeli.",
        },
        "sertifika": {
            "title": "Makine Öğrenmesi Temelleri",
            "issuer": "Stanford (Coursera)",
            "item_date": "2023-06-01",
        },
    },
    {
        "full_name": "ceren soyak",
        "bio": "Oyun geliştirme konusunda tutkulu bir yazılımcıyım, Unity ile 2D/3D interaktif deneyimler tasarlıyorum.",
        "skills": ["Unity", "C#", "Blender", "Git"],
        "proje": {
            "title": "2D Platform Oyunu Prototipi",
            "description": "Unity ve C# ile geliştirilmiş, kendi çizdiği Blender varlıklarını kullanan bir 2D platform oyunu prototipi.",
        },
        "sertifika": {
            "title": "Unity ile Oyun Geliştirme Sertifikası",
            "issuer": "Udemy",
            "item_date": "2022-05-19",
        },
    },
]

# deneme4yazilimci: kendi yazdigi gercek bio/skills'e dokunmuyoruz,
# sadece CV + portfolyo ekliyoruz.
EK_SADECE_PORTFOLYO = [
    {
        "full_name": "deneme4yazilimci",
        "skills_for_cv": ["Python", "HTML", "CSS"],
        "proje": {
            "title": "Basit Görev Takip Uygulaması",
            "description": "Python (Flask) backend ve HTML/CSS arayüzüyle geliştirilmiş, kullanıcıların günlük görevlerini takip edebildiği bir uygulama.",
        },
        "sertifika": {
            "title": "Python ile Web Geliştirme Sertifikası",
            "issuer": "freeCodeCamp",
            "item_date": "2023-07-22",
        },
    },
]


def profil_bul(full_name: str):
    r = supabase.table("profiles").select("id, full_name, bio, skills").eq("full_name", full_name).limit(1).execute()
    return r.data[0] if r.data else None


def portfolyo_ekle(user_id: str, ad_soyad: str, proje: dict, sertifika: dict) -> None:
    # Tekrar calistirmada kopyalanmasin diye bu iki basligi once temizle
    supabase.table("portfolio_items").delete().eq("developer_id", user_id).eq("title", proje["title"]).execute()
    supabase.table("portfolio_items").delete().eq("developer_id", user_id).eq("title", sertifika["title"]).execute()

    supabase.table("portfolio_items").insert({
        "developer_id": user_id,
        "title": proje["title"],
        "description": proje["description"],
        "item_type": "project",
        "issuer": None,
        "item_date": None,
        "file_url": None,
    }).execute()

    sertifika_pdf = sahte_sertifika_pdf_uret(ad_soyad, sertifika["title"], sertifika["issuer"], sertifika["item_date"])
    sertifika_url = dosya_yukle_ve_url_al(PORTFOLYO_BUCKET, f"{user_id}/sertifika.pdf", sertifika_pdf)

    supabase.table("portfolio_items").insert({
        "developer_id": user_id,
        "title": sertifika["title"],
        "description": None,
        "item_type": "certificate",
        "issuer": sertifika["issuer"],
        "item_date": sertifika["item_date"],
        "file_url": sertifika_url,
    }).execute()


print(f"{len(HEDEFLER) + len(EK_SADECE_PORTFOLYO)} profil dolduruluyor.\n")

for hedef in HEDEFLER:
    try:
        profil = profil_bul(hedef["full_name"])
        if not profil:
            print(f"  x '{hedef['full_name']}' bulunamadi, atlaniyor")
            continue

        user_id = profil["id"]
        cv_pdf = sahte_cv_pdf_uret(hedef["full_name"], hedef["bio"], hedef["skills"])
        cv_url = dosya_yukle_ve_url_al(CV_BUCKET, f"{user_id}/cv.pdf", cv_pdf)

        supabase.table("profiles").update({
            "bio": hedef["bio"],
            "skills": hedef["skills"],
            "cv_url": cv_url,
        }).eq("id", user_id).execute()

        portfolyo_ekle(user_id, hedef["full_name"], hedef["proje"], hedef["sertifika"])

        print(f"  + {hedef['full_name']} dolduruldu (bio + skills + CV + proje + sertifika)")
    except Exception as e:
        print(f"  x Hata ({hedef['full_name']}): {maskele(e)}")

for hedef in EK_SADECE_PORTFOLYO:
    try:
        profil = profil_bul(hedef["full_name"])
        if not profil:
            print(f"  x '{hedef['full_name']}' bulunamadi, atlaniyor")
            continue

        user_id = profil["id"]
        bio_for_cv = profil.get("bio") or ""
        skills_for_cv = profil.get("skills") or hedef["skills_for_cv"]

        cv_pdf = sahte_cv_pdf_uret(hedef["full_name"], bio_for_cv, skills_for_cv)
        cv_url = dosya_yukle_ve_url_al(CV_BUCKET, f"{user_id}/cv.pdf", cv_pdf)

        supabase.table("profiles").update({"cv_url": cv_url}).eq("id", user_id).execute()

        portfolyo_ekle(user_id, hedef["full_name"], hedef["proje"], hedef["sertifika"])

        print(f"  + {hedef['full_name']} dolduruldu (mevcut bio/skills korundu, CV + proje + sertifika eklendi)")
    except Exception as e:
        print(f"  x Hata ({hedef['full_name']}): {maskele(e)}")

print("\nTamamlandi!")
