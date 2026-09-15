# Co-Build AI — CLAUDE.md (En Güncel, v4)

Bu dosya Claude Code oturumlarında otomatik okunur. Projenin ne olduğunu, mimarisini, tamamlanan işleri ve bekleyen işleri özetler. Claude Code, bu dosyayı okuduktan sonra kısaca özetleyip kullanıcıdan (Esma) onay almalı.

**v4 notu:** Bu revizyon, hem `co-build-ai-server` hem `co-build-ai` (web) reposundaki gerçek kod okunarak hazırlandı (2026-09-15). v3'te "planlanıyor" / "kısmen başladı" denen **Patent RAG + Tescilli Mucit Çarpanı** ve **Dual-Role sistemi** aslında uçtan uca (backend + veritabanı + web UI) tamamlanmış durumda — kod, dokümantasyondan ileride kalmıştı. Ayrıca `co-build-ai/app/CLAUDE.md` adında, web tarafının kod-seviyesi güncel bir alt-özeti var; çelişki olursa bu kök dosya esas alınır ama alt dosya da faydalı bir günlük.

## 1. Proje Nedir

**Co-Build AI**: Teknik bilgisi olmayan fikir sahiplerini (founder) yazılımcılarla (developer) buluşturan bir pazar yeri platformu. Fikir sahibi projesini kendi cümleleriyle yazıyor, bir AI bunu profesyonel bir PRD'ye (teknik şartname) çeviriyor + gereken beceri etiketlerini çıkarıyor. Yazılımcılar bu projeleri keşfediyor, fikir sahipleri de yazılımcı profillerini keşfediyor.

## 2. Kullanıcı Profili

Esma — Python/ML deneyimli, web geliştirmede orta seviyeye ulaşmış (proje ilerledikçe öğrendi). Windows kullanıyor. Berna ile birlikte geliştiriyor. Adım adım, gerekçeli açıklamalarla ilerlemeyi tercih ediyor.

## 3. AI Altyapısı: RunPod/vLLM (Ollama DEĞİL)

Proje başlangıçta Ollama + Llama 3.1 8B ile yerel/CPU tabanlı çalışıyordu, **bu değişti**: CPU'da PRD üretimi çok yavaştı (1-5 dakika) ve Türkçe kalitesi zayıftı.

### Güncel AI Altyapısı
- **Model:** `Qwen/Qwen2.5-32B-Instruct-AWQ` (çok dillilik/Türkçe kalitesi için Llama'dan geçildi)
- **Motor:** vLLM — OpenAI-uyumlu API sunuyor (`/v1/chat/completions`)
- **Donanım:** RunPod'da kiralanan bir GPU sunucusu (RTX 4090, 24GB VRAM), saatlik ücretlendirme (~$0.75/saat)
- **Template:** RunPod'da "Runpod Pytorch 2.8.0" template'i, CUDA 12.8+ filtresiyle deploy edilmeli (filtresiz kiralamada "NVIDIA driver too old" hatası gerçekten yaşandı)
- **Kalıcı depo:** Pod'un container disk'i geçicidir (restart'ta sıfırlanabilir, gerçekten yaşandı). vLLM kurulumu ve model dosyaları **`/workspace` altında** (Network Volume, kalıcı):
  - Sanal ortam: `/workspace/vllm_env`
  - HF önbelleği: `/workspace/.cache/huggingface/`
- **Pod her yeniden başladığında** (Stop/Start sonrası) terminalde:
  ```bash
  cd /workspace
  source vllm_env/bin/activate
  vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ --quantization awq --max-model-len 4096 --gpu-memory-utilization 0.90
  ```
- **Bilinen risk:** RunPod bazen "Pod resume failed: not enough free GPUs on host machine" hatası verebiliyor (geçici, birkaç dakika sonra tekrar denenerek çözüldü). Sunum günü Pod'u en az 1-2 saat önce açıp hazır tutmak öneriliyor.
- **Maliyet:** İş bitince Pod **Stop** edilmeli; kalıcı depo sayesinde tekrar Start'ta sadece `vllm serve ...` yeterli.
- **Canlı testte ölçülen süre:** tüm döngü (üretim + öz-eleştiri + eşleştirme) ~35 saniyede tamamlanıyor — `main.py`'deki 5 dakikalık `JOB_TIMEOUT_SECONDS` bol bol yeterli bir pay.

### `.env` Değişkenleri (`co-build-ai-server`)
```
VLLM_BASE_URL=https://[pod-id]-8000.proxy.runpod.net/v1
VLLM_API_KEY=EMPTY
VLLM_MODEL_ADI=Qwen/Qwen2.5-32B-Instruct-AWQ
```
`VLLM_BASE_URL`, Pod yeniden deploy edilince (yeni Pod oluşursa) değişir — güncel URL RunPod panelinden (Connect → Port 8000 → HTTP Service) alınıp hem `.env` (server) hem `co-build-ai`'deki `NEXT_PUBLIC_AI_SERVICE_URL` (web) güncellenmeli. Kod bu değerleri `os.getenv()` ile okuyor, hardcode yok.

### İkinci Bilgisayara (Wi-Fi Eşleşmesine) Gerek Yok
RunPod internet üzerinden erişilebilir, hangi ağda olursa olsun bağlanılabiliyor. Next.js ve FastAPI aynı bilgisayarda çalışabilir (opsiyonel, teorik engel yok).

## 4. PRD Üretim Akışı — Artık Tek Prompt Değil, LangGraph Self-Reflection Döngüsü

`prd_agent.py` — ham fikirden PRD üretimi bir LangGraph durum makinesiyle yapılıyor:

```
prd_uret --> elestir --(onaylandı ya da 2. deneme)--> eslestir --> END
    ^                        |
    +-- (revize gerekli) ----+
```

- En fazla 2 üretim denemesi (ilk üretim + en fazla 1 düzeltme) — `iteration >= 2` olduğunda öz-eleştiri sonucu ne olursa olsun akış devam eder, sonsuz döngü yok.
- Öz-eleştiri hem LLM'e soruyor (8 bölümün tamamlığı + dil saflığı) hem de ayrıca bir regex ile (`_YABANCI_ALFABE_RE`) Çince/Kiril/Korece karakter sızmasını LLM'e güvenmeden kesin tespit ediyor.
- `elestir` düğümünden sonra `eslestir` düğümü otomatik olarak `matchmaking_engine.hibrit_eslestirme_yap` çağırıp önerilen geliştiricileri de aynı akışta döndürüyor — `main.py` artık ayrıca eşleştirme çağırmıyor, `prd_uret_ve_eslestir()` sonucu hem PRD hem `onerilen_gelistiriciler` içeriyor.
- Veri gizliliği: dış API (OpenAI/Anthropic vb.) yok, sadece kendi RunPod GPU'muzdaki vLLM.

### PRD İçeriği (Prompt Yapısı)
Tek birleşik prompt: Ürün Özeti, Hedef Kullanıcı, Temel Özellikler, Teknik Gereksinimler, Benzer Örnekler ve Farklılaşma, **Patent/Özgünlük Kontrolü** (bkz. Bölüm 6), Tahmini Altyapı Maliyeti Kategorisi, Beceri Etiketleri. Ayrıştırma (`_skills_ve_prd_ayikla`) birden fazla format dener çünkü model beceri başlığını tutarsız yazabiliyor (numaralı liste, farklı başlık ifadesi vb.) — bilinen bir kusur, tamamen çözülmedi.

## 5. Web Tarafı (Next.js — `co-build-ai` reposu)

- Next.js 16, App Router, TypeScript, Tailwind CSS v4
- Supabase: PostgreSQL + Authentication + RLS
- Tasarım paleti defalarca değişti (bkz. `co-build-ai/app/CLAUDE.md` → "Tasarım Geçmişi"); **güncel**: açık mavi zemin (`blue-50`) + beyaz/açık mavi sidebar + "bebek mavisi" (`blue-200`) vurgulu kartlar. Token isimleri (`bg-coral`, `text-ink` vb.) sabit kaldı, hex değerleri `globals.css`'teki `@theme` bloğunda sık değişti — class ismine değil gerçek hex'e güven.

### Dashboard Yapısı
`(dashboard)` route group altında sidebar + topbar düzeni (TailAdmin referanslı):
```
app/(dashboard)/
  ayarlar/ (tercihler, bildirimler, guvenlik, hesap, tehlikeli-bolge)
  panel/ (developer-projects.tsx, founder-developers.tsx, quick-match.tsx, direct-search.tsx)
  profil/ (edit-profile.tsx, [id]/page.tsx)
  mesajlar/
  projelerim/ (aktif, kabul-ettiklerim, teklifler, yururlukte)
  yildizlarim/
  layout.tsx
app/components/
  sidebar.tsx, topbar.tsx, notification-bell.tsx, role-switcher.tsx,
  project-match-card.tsx, project-progress-card.tsx, rate-offer-form.tsx,
  rating-stars.tsx, stat-circle.tsx, trending-widget.tsx, availability-badge.tsx,
  progress-ring.tsx, avatar.tsx, chat-box.tsx, logout-button.tsx, github-repo-badge.tsx
app/lib/roles.ts
app/proje/[id]/
  developer-project-view.tsx, offers-list.tsx, payment-section.tsx
```

### Dual-Role (Çift Rol) Sistemi — TAMAMLANDI (v3'te "kısmen başladı" deniyordu, artık geçersiz)
Kullanıcının hem founder hem developer olabilmesi özelliği **uçtan uca çalışıyor**, prototip değil:
- `profiles.user_type`: `"founder" | "developer" | "both"`; `profiles.active_role`: `"founder" | "developer"` (sadece `"both"` hesaplar için anlamlı — hangi modda gezindiğini tutar)
- Kayıt formunda (`app/kayit-ol/page.tsx`) "both" seçeneği var, seçilince `active_role: "founder"` ile başlıyor
- `app/lib/roles.ts`: `getActiveRole`, `canActAsDeveloper`, `canActAsFounder` yardımcıları
- `role-switcher.tsx`: sidebar'da mod değiştirme, Supabase'e `active_role` yazıyor, `router.refresh()`
- 17 dosyada kullanılıyor (panel, profil, projelerim/*, layout, quick-match, founder-developers, direct-search, yildizlarim) — yani gerçek, yaygın bir bağımlılık, izole bir deney değil

## 6. Patent RAG + Tescilli Mucit Çarpanı — TAMAMLANDI (v3'te "planlanıyor" deniyordu, artık geçersiz)

Bu özellik **hem AI servisinde hem veritabanında hem web arayüzünde tam olarak uygulanmış**:

1. **Veri seti:** Hugging Face `HUPD/hupd` (Harvard USPTO Patent Dataset), G06F/G06N sınıflı, `patent_veri_yukle.py` ile indirilip embed'leniyor → ayrı ChromaDB koleksiyonu `patent_ornekleri` (cosine similarity ile oluşturulmuş, bkz. `main.py`).
   - `--yil YIL` seçeneği (örn. `--yil 2016`) tek bir yılın küçük dosyasını indirip 3000-5000 hedef kayıt sayısına ulaşıyor; `--tam` 57.5GB'lık tüm arşivi indirir (pratik değil).
   - `datasets==2.19.0` sabitlenmiş — daha yeni sürüm HUPD'nin eski tip "loading script" yüklemesini kırıyor, YÜKSELTME.
2. **Patent çakışma kontrolü:** `main.py` içindeki `patent_cakismasi_kontrol_et()`, fikri `patent_ornekleri`'nde arar, `PATENT_BENZERLIK_ESIGI = 0.75` üzeri benzerlikte "YÜKSEK BENZERLİK UYARISI" ekliyor. PRD promptunda `## Patent/Özgünlük Kontrolü` bölümü olarak sunuluyor — kesin hukuki iddia üretmiyor, sadece ön bulgu + gerekirse hukuki danışmanlık önerisi.
3. **Tescilli Mucit Çarpanı:** `profiles.has_verified_patent` (boolean) sütunu var (`supabase_migration_patent_carpan.sql`). `matchmaking_engine.py`'de `PATENT_CARPAN = 1.15` — bu true olan geliştiricilerin RRF skoruna top_k seçilmeden ÖNCE uygulanıyor (yani gerçekten sıralamayı etkiliyor, sadece görünen skoru değil). Web tarafında `has_verified_patent` 7 dosyada kullanılıyor (profil, edit-profile, quick-match, founder-developers, direct-search vb.).
4. Kapsam kasıtlı olarak sınırlı: gerçek zamanlı, resmi patent ofisi entegrasyonu DEĞİL — statik bir veri seti üzerinden RAG tabanlı bir ön-kontrol prototipi.
5. Patent verisi indirme/embedding CPU'da çalışır, GPU/vLLM gerektirmez — RunPod Pod'u kapalıyken de yapılabilir. Sadece gerçek PRD/patent testi için Pod açık olmalı.

## 7. Eşleştirme Motoru (`matchmaking_engine.py` / `eslestirme_endpoints.py`)

- **Semantik arama:** `en_uygun_gelistiricileri_bul()` — PRD metnini `sentence-transformers/all-MiniLM-L6-v2` ile embed'leyip Supabase/pgvector'de (`match_developers` RPC) kosinüs benzerliğine göre top_k getirir.
- **Hibrit arama:** `hibrit_eslestirme_yap()` — semantik + BM25 (`rank_bm25`) sonuçlarını Reciprocal Rank Fusion (RRF, k=60) ile birleştirir; PRD'den çıkarılan beceri etiketleri BM25 sorgusuna ağırlıklandırılarak ekleniyor.
- **Skor normalizasyonu ÇÖZÜLDÜ (v3'te "0.03 gibi anlamsız değerler üretebiliyor" deniyordu):** `uyum_skorlarini_hesapla_ve_ata()` fonksiyonu, dönen sonuç kümesi içinde ham `hibrit_skor`'u 65-98 aralığına, ham `benzerlik_skoru`'nu (semantik-only durumda) 0-100'e ölçekleyip `uyum_skoru` alanına yazıyor — arayüz artık bu alanı doğrudan "%X uyum" olarak gösterebilir.
- `filtre_metadata` (`budget_type`, `sektor`) ile ön-filtreleme opsiyonel; migration çalıştırılmamış ortamlarda geriye dönük uyumlu şekilde sessizce atlanıyor.
- Endpoint'ler: `POST /gelistirici/vektorle`, `POST /eslestir/semantik-top5`, `POST /eslestir/hibrit`.

## 8. Veritabanı Şeması (Supabase) — Bilinen Tablolar

- `profiles` (id, user_type, active_role, full_name, bio, skills[], terms_accepted_at, cv_url, has_verified_patent) — hepsi arayüze bağlı
- `projects` (id, founder_id, title, raw_idea, generated_prd, required_skills[], status, idea_hash, idea_created_at, payment_type, payment_amount, matched_developers)
- `portfolio_items` (id, developer_id, title, description, file_url, item_type, issuer, item_date)
- `project_nda_acceptances`, `project_views` — **arayüze bağlı** (v3'teki "bağlanmadı" bilgisi artık geçersiz), `developer-project-view.tsx` üzerinden
- `offers` (id, project_id, developer_id, message, proposed_amount, proof_link, payment_type, status, completed_at, github_repo_url) — **teklif sistemi tam çalışıyor** (v3'teki "henüz yapılmadı" bilgisi artık geçersiz): ödeme tipi seçimi (Sabit Ücret/Ortaklık/Esnek), founder Kabul Et/Reddet, `offers-list.tsx` + `payment-section.tsx`
- `notifications`, `messages` — arayüze bağlı, Supabase Realtime açık
- `ratings` (id, offer_id, rater_id, rated_user_id, score, comment, unique(offer_id, rater_id)) — `offer.completed_at` set edildikten sonra değerlendirme açılıyor
- `developer_embeddings` (developer_id, full_name, skills, bio, kaynak_metin, embedding, opsiyonel budget_type/sektor) — eşleştirme motorunun pgvector tablosu

RLS tüm tablolarda aktif.

## 9. AI Servisi (`co-build-ai-server` reposu) — Dosya Envanteri

- `main.py` — FastAPI, asenkron PRD üretimi (`/prd-uret-baslat`, `/prd-durum/{id}`), 5 dakikalık timeout, `asyncio.Queue` + arka plan worker
- `prd_agent.py` — LangGraph self-reflection döngüsü (bkz. Bölüm 4)
- `matchmaking_engine.py`, `eslestirme_endpoints.py` — eşleştirme motoru (bkz. Bölüm 7)
- `veri_yukle.py` — startup RAG verisi yükleme (tek seferlik, çalıştırıldı): `sentence-transformers` + ChromaDB (`chroma_data/startup_ornekleri`, ~1500 kayıt, HackerNoon/where-startups-trend, MIT lisanslı)
- `patent_veri_yukle.py` — patent RAG verisi yükleme (bkz. Bölüm 6)
- `demo_kullanici_uret.py` + `demo_veri.json`, `demo_zengin_veri_uret.py`, `demo_bos_profil_doldur.py`, `demo_isim_degistir.py`, `demo_patent_arttir.py` — demo/sunum verisi üretme ve düzenleme script'leri (Supabase Admin API ile gerçek auth kullanıcıları)
- `gelistiricileri_toplu_vektorle.py` — mevcut tüm geliştiricileri toplu olarak `developer_embeddings`'e vektörleyen script
- `supabase_migration_*.sql` — sırasıyla: metadata_filter (budget_type/sektor), patent_carpan (has_verified_patent), patent_url, starred_developers, banner

### ✅ Düzeltildi (2026-09-15): `requirements.txt` ve `README.md`
`requirements.txt` UTF-16 kodlamasıyla kaydedilmişti (her karakter arasında boşluk, muhtemelen PowerShell `Out-File`/yönlendirme hatası) ve `langchain-openai`/`datasets` paketleri eksikti (`prd_agent.py` ve `patent_veri_yukle.py` bunlara ihtiyaç duyuyor). Yerel `venv`'deki gerçek çalışan `pip freeze` çıktısından UTF-8 olarak yeniden yazıldı; artık kullanılmayan `ollama`/`langchain-ollama` girdileri çıkarıldı. `README.md` de hâlâ eski Ollama mimarisini anlatıyordu — vLLM/RunPod, LangGraph self-reflection döngüsü, eşleştirme motoru ve patent RAG'ı yansıtacak şekilde güncellendi.

### GitHub Repo
`github.com/berna1727/co-build-ai-server` (Private). `startups.xlsx` (13MB, ham veri) yanlışlıkla commit edilmiş, temizlenmedi (düşük öncelik).

## 10. Git İş Akışı — ÖNEMLİ DENEYİMLER

- Proje **iki ayrı repo**: `co-build-ai` (esmacakar hesabı, Next.js) ve `co-build-ai-server` (berna1727 hesabı, Python/FastAPI, private)
- **Merge conflict yaşandı** (Esma'nın yerel dual-role değişiklikleri ile GitHub'daki Claude Code değişiklikleri çakıştı) — `profil/page.tsx`, `projelerim/yururlukte/page.tsx`, `proje/[id]/page.tsx` dosyalarında. Bu tür çakışmalarda Claude Code'un dosyaları okuyup iki tarafı da koruyarak birleştirmesi isteniyor, kullanıcı elle çözmüyor.
- Rutin: `git pull` (başlamadan önce) → çalış → `git add . && git commit -m "..." && git push`
- Kullanıcı, Claude Code'a büyük değişiklik yaptırmadan önce commit atma alışkanlığını henüz tam oturtmadı, hatırlatmak faydalı olabilir

## 11. Bilinçli Olarak v2'ye Ertelenen Özellikler

- Biyometrik KYC, Stripe/escrow gerçek ödeme (para transferi/escrow yok)
- NDA dijital imza
- Tinder-tarzı swipe eşleştirme (kesin olarak vazgeçildi)
- GitHub commit'e göre otomatik milestone/ödeme tetikleme
- Platform içi kod editörü/sandbox
- Gerçek zamanlı canlı web/rakip taraması
- Mobil uygulama
- Tam kapsamlı, resmi patent ofisi entegrasyonu (Bölüm 6'daki statik veri setli prototip bunun yerine MVP kapsamında)

## 12. Bilinen Riskler (RunPod/AI dışında)

- `.env.local`'deki `NEXT_PUBLIC_AI_SERVICE_URL` (web) ve `.env`'deki `VLLM_BASE_URL` (server), Pod yeniden deploy edilince değişir — ikisi de güncellenmezse istekler sessizce başarısız olabilir
- RunPod Pod kapalıyken PRD üretimi bekleyen bir proje sonsuza kadar "PRD hazırlanıyor" gösterir (sessizce retry eder, kullanıcıya hata göstermez)

## 13. Claude Code İçin Genel Yaklaşım

Bu proje, kod tabanının kullanıcının hafızasından ileride olduğu bir noktaydı — v4 revizyonuyla bu doküman kodla senkronize edildi, ama proje hızlı ilerliyor. Yeni bir işe başlamadan önce:
1. Mevcut dosyaları oku, bu dokümana körü körüne güvenme — özellikle "TAMAMLANDI" denen bölümlerin de zamanla değişmiş olabileceğini unutma
2. Belirsizlik varsa kullanıcıya "şu an X dosyası şöyle görünüyor, bu senin beklediğin gibi mi?" diye doğrulat
3. İki repo arasında geçiş yaparken (`co-build-ai` / `co-build-ai-server`) hangi repoda olduğunu netleştir — env değişkenleri, dosya yapıları ve git hesapları farklı

## 14. Kod Tarzı Notları

- Next.js App Router yapısı, client component'ler `"use client"` ile başlıyor
- Tailwind renkleri `globals.css`'te `@theme` bloğunda
- Python tarafında Türkçe fonksiyon/değişken isimleri (`benzer_ornekleri_bul`, `patent_cakismasi_kontrol_et` gibi)
- `.env` üzerinden okunan değerler `os.getenv()` ile, path'ler hardcode edilmiyor
- Kod yorumları Türkçe
- Sunucu tarafı, gizli anahtar gerektiren işlemler (web) `app/api/*/route.ts` altında (`SUPABASE_SERVICE_ROLE_KEY` asla client'a gitmiyor)
