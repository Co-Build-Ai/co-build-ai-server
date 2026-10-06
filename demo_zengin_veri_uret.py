"""
demo_zengin_veri_uret.py
============================================================================
Co-Build AI — Zengin Demo Veri Üretici (Tek Seferlik Script)
============================================================================
Amaç: demo_kullanici_uret.py'nin ürettiği temel veriye ek olarak, PROFİLİ,
PRD'si, üzerinde çalıştığı projesi, teklifi (handshake) ve rating'i DOLU
DOLU görünen bir "zengin" demo seti eklemek — özellikle:

    - Bazı geliştiricilerin `has_verified_patent = true` olması (Tescilli
      Mucit Eşleştirme Çarpanı'nı test edebilmek için)
    - `offers` tablosunda pending/accepted/completed karışık durumlar
    - Tamamlanan tekliflere karşılıklı `ratings` kayıtları (rating
      sistemini uçtan uca test edebilmek için)

DİKKAT: demo_kullanici_uret.py ile AYNI güvenlik desenini kullanır
(SUPABASE_SERVICE_KEY, admin yetkisi, DEMO_SEED_ONAY onayı). Farklı e-posta
öneki (`zengin.*@cobuildai-demo.com`) kullanır, mevcut demo verisiyle
ÇAKIŞMAZ — üstüne EKLENİR, üzerine yazmaz.

ÖN KOŞUL: `profiles.has_verified_patent` kolonu Supabase'de olmalı — bkz.
supabase_migration_patent_carpan.sql. Script başında bu kontrol edilir;
kolon yoksa açıkça durur (sessizce atlamaz — bu script'in asıl amacı
patent çarpanını test etmek).

Kullanım
--------
    python demo_zengin_veri_uret.py
"""

from __future__ import annotations

import os
import sys

# Windows konsolu bazen cp1254 gibi bir kod sayfasi kullaniyor ve ✓/✗ gibi
# Unicode karakterleri yazdiramiyor (UnicodeEncodeError). UTF-8'e zorluyoruz.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# --- ORTAM DEĞİŞKENLERİ (demo_kullanici_uret.py ile aynı desen) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "DemoSifre123!")

_eksik = [
    isim
    for isim, deger in (("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY))
    if not deger
]
if _eksik:
    sys.exit(f"HATA: eksik ortam değişkeni: {', '.join(_eksik)}")

_SABLON_ISARETLERI = ("replace_me", "your-service-key", "buraya", "changeme")
if any(isaret in SUPABASE_SERVICE_KEY.lower() for isaret in _SABLON_ISARETLERI):
    sys.exit("HATA: SUPABASE_SERVICE_KEY hala şablon değerinde. .env dosyasını doldurun.")

_GIZLI_DEGERLER = tuple(deger for deger in (SUPABASE_SERVICE_KEY, DEMO_PASSWORD) if deger and len(deger) >= 8)


def maskele(metin: object) -> str:
    sonuc = str(metin)
    for sir in _GIZLI_DEGERLER:
        sonuc = sonuc.replace(sir, "***GIZLI***")
    return sonuc


def onay_al() -> None:
    if os.getenv("DEMO_SEED_ONAY", "").strip().lower() in ("1", "true", "evet", "yes"):
        return
    print("Bu işlem aşağıdaki Supabase projesine ADMIN yetkisiyle yazacak:")
    print(f"  {SUPABASE_URL}")
    try:
        cevap = input("Devam etmek için 'EVET' yazın: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nİptal edildi (onay alınamadı).")
    if cevap != "EVET":
        sys.exit("İptal edildi.")


onay_al()
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- ÖN KOŞUL KONTROLÜ: has_verified_patent kolonu var mı? ---
try:
    supabase.table("profiles").select("has_verified_patent").limit(1).execute()
except Exception:
    sys.exit(
        "HATA: 'profiles.has_verified_patent' kolonu bulunamadı.\n"
        "Önce supabase_migration_patent_carpan.sql dosyasını Supabase SQL "
        "Editor'de çalıştırın, sonra bu script'i tekrar deneyin."
    )


# ============================================================================
# VERİ TANIMLARI
# ============================================================================

GELISTIRICILER = [
    {"full_name": "Deniz Aydemir", "skills": ["Python", "Django", "PostgreSQL", "Docker"], "bio": "8 yıllık backend geliştirici, ölçeklenebilir API mimarileri konusunda uzman. 2 tescilli patenti bulunuyor.", "has_verified_patent": True},
    {"full_name": "Ece Korkmaz", "skills": ["React", "TypeScript", "Next.js", "TailwindCSS"], "bio": "Frontend odaklı, kullanıcı deneyimine önem veren bir yazılımcıyım. Design sistemleri kurmayı seviyorum.", "has_verified_patent": False},
    {"full_name": "Kaan Yıldırım", "skills": ["Machine Learning", "PyTorch", "Python", "MLOps"], "bio": "Makine öğrenmesi mühendisiyim, görüntü işleme alanında bir buluşum için patent başvurum onaylandı.", "has_verified_patent": True},
    {"full_name": "Selin Doğan", "skills": ["React Native", "Swift", "Kotlin", "Firebase"], "bio": "Mobil uygulama geliştirme konusunda 5 yıllık deneyimim var, hem iOS hem Android yayınladım.", "has_verified_patent": False},
    {"full_name": "Mert Aksoy", "skills": ["Node.js", "Express", "MongoDB", "Redis"], "bio": "Full-stack geliştirici, gerçek zamanlı sistemler ve mesajlaşma altyapıları kuruyorum.", "has_verified_patent": False},
    {"full_name": "Zeynep Kaya", "skills": ["Go", "Kubernetes", "gRPC", "AWS"], "bio": "DevOps ve backend arasında bir yazılımcıyım, dağıtık sistemler tasarımı üzerine bir patentim var.", "has_verified_patent": True},
    {"full_name": "Emir Şahin", "skills": ["Vue.js", "Nuxt", "GraphQL", "PostgreSQL"], "bio": "Frontend ve backend arasında rahat geçiş yapabilen bir full-stack geliştiriciyim.", "has_verified_patent": False},
    {"full_name": "Ayşe Yılmaz", "skills": ["Flutter", "Dart", "Firebase", "REST API"], "bio": "Flutter ile çapraz platform mobil uygulamalar geliştiriyorum, 10+ uygulama yayınladım.", "has_verified_patent": False},
    {"full_name": "Burak Çelik", "skills": ["Java", "Spring Boot", "Microservices", "Kafka"], "bio": "Kurumsal ölçekte mikroservis mimarileri kuran bir backend mühendisiyim.", "has_verified_patent": False},
    {"full_name": "Naz Arslan", "skills": ["Python", "FastAPI", "LangChain", "Vector DB"], "bio": "Yapay zeka destekli ürünler geliştiriyorum, RAG mimarileri konusunda deneyimliyim.", "has_verified_patent": False},
]

FOUNDERLAR = [
    {"full_name": "Onur Demirtaş", "bio": "Seri girişimci, 2 startup kurdu."},
    {"full_name": "Elif Toprak", "bio": "Ürün yöneticisi kökenli, teknik olmayan bir kurucu."},
    {"full_name": "Cem Yalçın", "bio": "E-ticaret sektöründen, yeni bir fikri hayata geçirmek istiyor."},
    {"full_name": "Gizem Aktaş", "bio": "Sağlık teknolojileri alanında bir fikri var."},
    {"full_name": "Tolga Erdem", "bio": "Eğitim teknolojileri girişimcisi."},
]


def ornek_prd_uret(baslik: str, ozet: str, ozellikler: list[str], beceriler: list[str], maliyet: str) -> str:
    """
    Gerçek bir LLM çağrısı yapmadan, gerçekçi görünümlü, 8 bölümlü bir PRD
    metni üretir (bkz. prd_agent.py'deki PRD_PROMPT ile aynı format).
    Demo/test verisi için — RunPod/vLLM'e bağımlılığı kaldırır.
    """
    ozellik_metni = "\n".join(f"- {o}" for o in ozellikler)
    beceri_metni = ", ".join(beceriler)
    return f"""## Ürün Özeti
{ozet}

## Hedef Kullanıcı
Bu ürün, {baslik.lower()} alanında çözüm arayan son kullanıcılar ve işletmeler için tasarlanmıştır.

## Temel Özellikler
{ozellik_metni}

## Teknik Gereksinimler
Bu proje için gereken beceri/teknoloji alanları: {beceri_metni}.

## Benzer Örnekler ve Farklılaşma
Veri tabanımızda doğrudan bir örnek bulunamadı, bu potansiyel bir avantaj olabilir.

## Patent/Özgünlük Kontrolü
Otomatik patent taraması sonucunda belirgin bir patent çakışması tespit edilmedi. Not: Bu sadece otomatik bir ön kontroldür, kesin bir hukuki tespit değildir.

## Tahmini Altyapı Maliyeti Kategorisi
{maliyet} Not: Bu, yapay zeka tarafından üretilen kaba bir tahmindir, gerçek maliyetler için bir teknik danışmana başvurulması önerilir.

## Beceri Etiketleri
{beceri_metni}"""


PROJE_SABLONLARI = [
    {
        "title": "Komşu Alet Paylaşım Uygulaması",
        "raw_idea": "Komşuların nadiren kullandıkları aletleri (matkap, merdiven vb.) birbirleriyle paylaşabildiği bir uygulama.",
        "ozet": "Komşu Alet Paylaşım Uygulaması, mahalle sakinlerinin nadiren kullandıkları ev aletlerini güvenli bir şekilde birbirleriyle paylaşmasını sağlayan bir platformdur.",
        "ozellikler": ["Alet listeleme ve arama", "Konum bazlı eşleştirme", "Güvenli mesajlaşma", "Değerlendirme sistemi"],
        "required_skills": ["React Native", "Node.js", "PostgreSQL", "Firebase"],
        "maliyet": "Düşük.",
        "payment_type": "fixed", "payment_amount": 45000,
    },
    {
        "title": "Akıllı Fatura Takip Sistemi",
        "raw_idea": "Kullanıcıların tüm faturalarını (elektrik, su, internet) tek yerden takip edip hatırlatma alabildiği bir uygulama.",
        "ozet": "Akıllı Fatura Takip Sistemi, kullanıcıların farklı kurumlardan gelen faturalarını tek bir yerden görüntülemesini ve son ödeme tarihlerinde hatırlatma almasını sağlar.",
        "ozellikler": ["OCR ile fatura tarama", "Otomatik hatırlatma bildirimleri", "Harcama analizi ve grafikler", "Banka entegrasyonu"],
        "required_skills": ["Python", "FastAPI", "React", "PostgreSQL"],
        "maliyet": "Orta.",
        "payment_type": "fixed", "payment_amount": 60000,
    },
    {
        "title": "Yapay Zeka Destekli CV Analiz Aracı",
        "raw_idea": "İşe alım uzmanlarının CV'leri otomatik analiz edip pozisyona uygunluk skoru verdiği bir araç.",
        "ozet": "Bu araç, yüklenen CV'leri doğal dil işleme ile analiz ederek ilan edilen pozisyona uygunluk skoru üretir ve işe alım sürecini hızlandırır.",
        "ozellikler": ["CV'den otomatik bilgi çıkarma", "Pozisyon eşleştirme skoru", "Aday karşılaştırma paneli", "PDF/Word desteği"],
        "required_skills": ["Python", "Machine Learning", "FastAPI", "Vector DB"],
        "maliyet": "Orta.",
        "payment_type": "equity", "payment_amount": 5,
    },
    {
        "title": "Bisiklet Tamir Kiosku Randevu Sistemi",
        "raw_idea": "Şehir içindeki bisiklet tamir kiosklarına online randevu alınabilen bir sistem.",
        "ozet": "Kullanıcıların şehir genelindeki bisiklet tamir kiosklarına uygunluk durumuna göre online randevu almasını sağlayan bir sistemdir.",
        "ozellikler": ["Kiosk müsaitlik takvimi", "Online randevu alma", "SMS/e-posta hatırlatma", "Tamir geçmişi kaydı"],
        "required_skills": ["Vue.js", "Node.js", "MongoDB", "Redis"],
        "maliyet": "Düşük.",
        "payment_type": "fixed", "payment_amount": 35000,
    },
    {
        "title": "Uzaktan Sağlık Takip Platformu",
        "raw_idea": "Kronik hastalığı olan hastaların vital verilerini uzaktan doktorlarıyla paylaşabildiği bir platform.",
        "ozet": "Uzaktan Sağlık Takip Platformu, kronik hastaların tansiyon, şeker gibi vital verilerini düzenli kaydedip doktorlarıyla güvenli şekilde paylaşmasını sağlar.",
        "ozellikler": ["Vital veri girişi ve grafik takibi", "Doktor-hasta güvenli mesajlaşma", "Anormal değer uyarıları", "KVKK uyumlu veri saklama"],
        "required_skills": ["Flutter", "FastAPI", "PostgreSQL", "AWS"],
        "maliyet": "Yüksek.",
        "payment_type": "fixed", "payment_amount": 90000,
    },
    {
        "title": "Yerel Üretici Pazaryeri",
        "raw_idea": "Küçük yerel üreticilerin (reçel, peynir, el işi) ürünlerini doğrudan tüketiciye satabildiği bir pazaryeri.",
        "ozet": "Yerel Üretici Pazaryeri, küçük ölçekli yerel üreticilerin ürünlerini aracısız olarak doğrudan tüketicilere ulaştırmasını sağlayan bir e-ticaret platformudur.",
        "ozellikler": ["Üretici mağaza sayfaları", "Sipariş ve kargo takibi", "Ödeme entegrasyonu", "Ürün değerlendirme sistemi"],
        "required_skills": ["Next.js", "Node.js", "PostgreSQL", "Stripe"],
        "maliyet": "Orta.",
        "payment_type": "equity", "payment_amount": 8,
    },
    {
        "title": "Öğrenci Not Paylaşım Platformu",
        "raw_idea": "Üniversite öğrencilerinin ders notlarını ve özetlerini paylaşıp puanlayabildiği bir platform.",
        "ozet": "Öğrenci Not Paylaşım Platformu, üniversite öğrencilerinin ders notlarını, özetlerini ve sınav sorularını güvenli bir ortamda paylaşmasını sağlar.",
        "ozellikler": ["Not/döküman yükleme", "Ders ve bölüm bazlı arama", "Puanlama ve yorum sistemi", "Üniversite e-postası doğrulama"],
        "required_skills": ["React", "Django", "PostgreSQL", "AWS S3"],
        "maliyet": "Düşük.",
        "payment_type": "fixed", "payment_amount": 30000,
    },
    {
        "title": "Ev Bitkisi Bakım Asistanı",
        "raw_idea": "Kullanıcının ev bitkilerinin fotoğrafını çekip tür tanıma ve bakım önerisi aldığı bir mobil uygulama.",
        "ozet": "Ev Bitkisi Bakım Asistanı, kullanıcının çektiği fotoğraflardan bitki türünü tanıyıp sulama/ışık gibi bakım önerileri sunan bir mobil uygulamadır.",
        "ozellikler": ["Görüntüden bitki türü tanıma", "Kişiselleştirilmiş bakım takvimi", "Sulama hatırlatmaları", "Topluluk soru-cevap bölümü"],
        "required_skills": ["React Native", "Machine Learning", "Python", "Firebase"],
        "maliyet": "Orta.",
        "payment_type": "fixed", "payment_amount": 55000,
    },
    {
        "title": "Kurumsal Şikayet Yönetim Sistemi",
        "raw_idea": "Şirketlerin müşteri şikayetlerini tek bir panelden takip edip çözüm süresini ölçebildiği bir sistem.",
        "ozet": "Kurumsal Şikayet Yönetim Sistemi, işletmelerin farklı kanallardan gelen müşteri şikayetlerini tek panelde toplayıp çözüm sürecini takip etmesini sağlar.",
        "ozellikler": ["Çoklu kanal şikayet toplama", "Otomatik önceliklendirme", "Çözüm süresi raporlama", "Ekip görevlendirme"],
        "required_skills": ["Java", "Spring Boot", "PostgreSQL", "Kafka"],
        "maliyet": "Yüksek.",
        "payment_type": "fixed", "payment_amount": 85000,
    },
    {
        "title": "Freelancer Zaman Takip Aracı",
        "raw_idea": "Freelancer'ların proje bazlı çalışma sürelerini takip edip otomatik fatura oluşturabildiği bir araç.",
        "ozet": "Freelancer Zaman Takip Aracı, serbest çalışanların proje bazlı harcadıkları süreyi kaydedip bu verilerden otomatik fatura/rapor oluşturmasını sağlar.",
        "ozellikler": ["Proje bazlı zaman takibi", "Otomatik fatura oluşturma", "Müşteri raporlama", "Takvim entegrasyonu"],
        "required_skills": ["Vue.js", "FastAPI", "PostgreSQL", "Stripe"],
        "maliyet": "Düşük.",
        "payment_type": "equity", "payment_amount": 6,
    },
]

TEKLIF_MESAJLARI = [
    "Bu proje ilgimi çekti, benzer bir sistemi daha önce geliştirmiştim. Detayları konuşabilir miyiz?",
    "Gereksinimlerinizi inceledim, önerdiğim teknoloji yığınıyla 6-8 haftada teslim edebilirim.",
    "Portföyümdeki benzer bir projeyi paylaşmak isterim, uygunsanız görüşme ayarlayalım.",
    "Bu alanda deneyimim var, teklifimi gözden geçirip geri dönüş yapabilirsiniz.",
]


# ============================================================================
# 1) GELİŞTİRİCİ HESAPLARI
# ============================================================================

print(f"\n{len(GELISTIRICILER)} geliştirici, {len(FOUNDERLAR)} fikir sahibi, {len(PROJE_SABLONLARI)} proje oluşturulacak.\n")

print("Geliştirici hesapları oluşturuluyor...")
developer_ids: list[str] = []
for i, dev in enumerate(GELISTIRICILER):
    email = f"zengin.dev{i}@cobuildai-demo.com"
    try:
        auth_resp = supabase.auth.admin.create_user({"email": email, "password": DEMO_PASSWORD, "email_confirm": True})
        user_id = auth_resp.user.id
        developer_ids.append(user_id)

        supabase.table("profiles").insert({
            "id": user_id,
            "user_type": "developer",
            "active_role": "developer",
            "full_name": dev["full_name"],
            "bio": dev["bio"],
            "skills": dev["skills"],
            "availability": "available",
            "has_verified_patent": dev["has_verified_patent"],
        }).execute()

        patent_etiketi = " [PATENTLİ]" if dev["has_verified_patent"] else ""
        print(f"  ✓ {dev['full_name']}{patent_etiketi} oluşturuldu")
    except Exception as e:
        print(f"  ✗ Hata ({dev['full_name']}): {maskele(e)}")

# ============================================================================
# 2) FOUNDER HESAPLARI
# ============================================================================

print("\nFikir sahibi hesapları oluşturuluyor...")
founder_ids: list[str] = []
for i, founder in enumerate(FOUNDERLAR):
    email = f"zengin.founder{i}@cobuildai-demo.com"
    try:
        auth_resp = supabase.auth.admin.create_user({"email": email, "password": DEMO_PASSWORD, "email_confirm": True})
        user_id = auth_resp.user.id
        founder_ids.append(user_id)

        supabase.table("profiles").insert({
            "id": user_id,
            "user_type": "founder",
            "active_role": "founder",
            "full_name": founder["full_name"],
            "bio": founder["bio"],
        }).execute()

        print(f"  ✓ {founder['full_name']} oluşturuldu")
    except Exception as e:
        print(f"  ✗ Hata ({founder['full_name']}): {maskele(e)}")

if not developer_ids or not founder_ids:
    sys.exit("HATA: Geliştirici veya fikir sahibi oluşturulamadı, devam edilemiyor.")

# ============================================================================
# 3) PROJELER (PRD dolu, founder'lara dağıtılmış)
# ============================================================================

print("\nProjeler ekleniyor (PRD dahil)...")
project_ids: list[str] = []
for i, sablon in enumerate(PROJE_SABLONLARI):
    founder_id = founder_ids[i % len(founder_ids)]
    prd = ornek_prd_uret(
        baslik=sablon["title"],
        ozet=sablon["ozet"],
        ozellikler=sablon["ozellikler"],
        beceriler=sablon["required_skills"],
        maliyet=sablon["maliyet"],
    )
    try:
        sonuc = supabase.table("projects").insert({
            "founder_id": founder_id,
            "title": sablon["title"],
            "raw_idea": sablon["raw_idea"],
            "generated_prd": prd,
            "required_skills": sablon["required_skills"],
            "status": "published",
            "payment_type": sablon["payment_type"],
            "payment_amount": sablon["payment_amount"],
        }).execute()
        project_ids.append(sonuc.data[0]["id"])
        print(f"  ✓ {sablon['title']} eklendi (PRD dahil)")
    except Exception as e:
        print(f"  ✗ Hata ({sablon['title']}): {maskele(e)}")

# ============================================================================
# 4) TEKLİFLER (handshake) — karışık durumlarda: pending / accepted / completed
# ============================================================================

print("\nTeklifler (offers) ekleniyor...")
tamamlanan_teklifler: list[dict] = []  # rating eklemek için sakla

teklif_plani = []
for i, project_id in enumerate(project_ids):
    # Her projeye 1-2 geliştiriciden teklif: biri "tamamlanmış" (accepted +
    # completed_at dolu — DİKKAT: offers.status check constraint'i sadece
    # pending/accepted/rejected kabul ediyor, ayrı bir 'completed' değeri
    # YOK; tamamlanma completed_at ile işaretleniyor), biri pending/accepted.
    dev_a = developer_ids[i % len(developer_ids)]
    dev_b = developer_ids[(i + 3) % len(developer_ids)]
    durum_a = ["tamamlanmis", "accepted", "pending"][i % 3]
    teklif_plani.append((project_id, dev_a, durum_a))
    if i % 2 == 0:  # bazı projelere ikinci bir teklif de ekle (çeşitlilik için)
        teklif_plani.append((project_id, dev_b, "pending"))

for i, (project_id, developer_id, durum) in enumerate(teklif_plani):
    db_status = "accepted" if durum == "tamamlanmis" else durum
    kayit = {
        "project_id": project_id,
        "developer_id": developer_id,
        "message": TEKLIF_MESAJLARI[i % len(TEKLIF_MESAJLARI)],
        "proposed_amount": 30000 + (i * 2500),
        "status": db_status,
        "payment_type": "fixed",
    }
    if db_status == "accepted":
        kayit["github_repo_url"] = f"https://github.com/demo-org/proje-{i}"
    if durum == "tamamlanmis":
        kayit["completed_at"] = "now()"

    try:
        sonuc = supabase.table("offers").insert(kayit).execute()
        eklenen = sonuc.data[0]
        print(f"  ✓ Teklif eklendi (durum={durum})")
        if durum == "tamamlanmis":
            tamamlanan_teklifler.append({
                "offer_id": eklenen["id"],
                "developer_id": developer_id,
                "project_id": project_id,
            })
    except Exception as e:
        print(f"  ✗ Hata (teklif {i}): {maskele(e)}")

# ============================================================================
# 5) RATING'LER — tamamlanan tekliflerde karşılıklı (founder<->developer)
# ============================================================================

print("\nTamamlanan tekliflere rating ekleniyor...")
proje_founder_map = {p_id: founder_ids[i % len(founder_ids)] for i, p_id in enumerate(project_ids)}

RATING_YORUMLARI_FOUNDER = [
    "Çok profesyonel bir çalışma oldu, teşekkürler!",
    "Teslim süresine sadık kaldı, iletişimi de çok iyiydi.",
    "Beklentilerimin üzerinde bir sonuç aldık.",
]
RATING_YORUMLARI_DEV = [
    "Net bir brief verdi, süreç boyunca hızlı geri dönüş aldım.",
    "Ödeme zamanında yapıldı, keyifli bir iş birliğiydi.",
    "Beklentiler baştan netti, tekrar çalışmak isterim.",
]

for i, teklif in enumerate(tamamlanan_teklifler):
    founder_id = proje_founder_map.get(teklif["project_id"])
    if not founder_id:
        continue
    try:
        # Founder -> Developer
        supabase.table("ratings").insert({
            "offer_id": teklif["offer_id"],
            "rater_id": founder_id,
            "rated_user_id": teklif["developer_id"],
            "score": 4 + (i % 2),  # 4 veya 5
            "comment": RATING_YORUMLARI_FOUNDER[i % len(RATING_YORUMLARI_FOUNDER)],
        }).execute()
        # Developer -> Founder
        supabase.table("ratings").insert({
            "offer_id": teklif["offer_id"],
            "rater_id": teklif["developer_id"],
            "rated_user_id": founder_id,
            "score": 4 + ((i + 1) % 2),
            "comment": RATING_YORUMLARI_DEV[i % len(RATING_YORUMLARI_DEV)],
        }).execute()
        print(f"  ✓ Karşılıklı rating eklendi (offer {teklif['offer_id'][:8]}...)")
    except Exception as e:
        print(f"  ✗ Hata (rating, offer {teklif['offer_id'][:8]}...): {maskele(e)}")

print("\nTamamlandı!")
print(f"Toplam: {len(developer_ids)} geliştirici ({sum(1 for d in GELISTIRICILER if d['has_verified_patent'])} patentli), "
      f"{len(founder_ids)} fikir sahibi, {len(project_ids)} proje, {len(teklif_plani)} teklif, "
      f"{len(tamamlanan_teklifler) * 2} rating işlendi.")
