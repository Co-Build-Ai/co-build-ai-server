# Co-Build AI — CLAUDE.md (En Güncel, v3)

Bu dosya Claude Code oturumlarında otomatik okunur. Projenin ne olduğunu, mimarisini, tamamlanan işleri ve bekleyen işleri özetler. Claude Code, bu dosyayı okuduktan sonra kısaca özetleyip kullanıcıdan (Esma) onay almalı.

## 1. Proje Nedir

**Co-Build AI**: Teknik bilgisi olmayan fikir sahiplerini (founder) yazılımcılarla (developer) buluşturan bir pazar yeri platformu. Fikir sahibi projesini kendi cümleleriyle yazıyor, bir AI bunu profesyonel bir PRD'ye (teknik şartname) çeviriyor + gereken beceri etiketlerini çıkarıyor. Yazılımcılar bu projeleri keşfediyor, fikir sahipleri de yazılımcı profillerini keşfediyor.

## 2. Kullanıcı Profili

Esma — Python/ML deneyimli, web geliştirmede orta seviyeye ulaşmış (proje ilerledikçe öğrendi). Windows kullanıyor. Berna ile birlikte geliştiriyor. Adım adım, gerekçeli açıklamalarla ilerlemeyi tercih ediyor.

## 3. BÜYÜK MİMARİ DEĞİŞİKLİĞİ: Artık RunPod/vLLM Kullanılıyor (Ollama DEĞİL)

**ÇOK ÖNEMLİ — ESKİ BİLGİ GEÇERSİZ:** Proje başlangıçta Ollama + Llama 3.1 8B ile yerel/CPU tabanlı çalışıyordu. **Bu artık değişti.** Sebep: CPU'da PRD üretimi çok yavaştı (1-5 dakika) ve Türkçe kalitesi zayıftı (yarım kalan cümleler, İngilizce kelime karışması).

### Güncel AI Altyapısı
- **Model:** `Qwen/Qwen2.5-32B-Instruct-AWQ` (Llama değil, Qwen'e geçildi — çok dillilik/Türkçe kalitesi daha iyi bulundu)
- **Motor:** vLLM (Ollama değil) — OpenAI-uyumlu API sunuyor (`/v1/chat/completions`)
- **Donanım:** RunPod'da kiralanan bir GPU sunucusu (RTX 4090, 24GB VRAM), saatlik ücretlendirme (~$0.75/saat)
- **Template:** RunPod'da "Runpod Pytorch 2.8.0" template'i kullanılıyor, CUDA 12.8+ filtresiyle deploy edilmeli (eski/uyumsuz sürücülü host'lara denk gelmemek için — bu gerçek bir sorun yaşandı, "NVIDIA driver too old" hatası alındı, GPU/CUDA filtresi olmadan Pod kiralanınca tekrar olabilir)
- **Kalıcı depo:** RunPod Pod'unun **container disk'i geçicidir** (Pod restart olursa sıfırlanabilir, bu gerçekten yaşandı). Bu yüzden vLLM kurulumu ve model dosyaları **`/workspace` altına** (Network Volume, kalıcı) kuruldu:
  - Sanal ortam: `/workspace/vllm_env`
  - Hugging Face önbelleği: `/workspace/.cache/huggingface/` (bazı ortamlarda `HF_HOME` farklı davranabiliyor, kontrol edilmeli)
- **Pod her yeniden başladığında** (Stop/Start sonrası), terminalde şunlar gerekiyor:
  ```bash
  cd /workspace
  source vllm_env/bin/activate
  vllm serve Qwen/Qwen2.5-32B-Instruct-AWQ --quantization awq --max-model-len 4096 --gpu-memory-utilization 0.90
  ```
- **Bilinen risk:** RunPod bazen "Pod resume failed: not enough free GPUs on host machine" hatası verebiliyor — bu geçici, birkaç dakika sonra tekrar denenerek çözüldü. Sunum günü için Pod'u erkenden (en az 1-2 saat önce) başlatıp hazır tutmak öneriliyor.
- **Maliyet bilinci:** GPU saatlik ücretlendirildiği için, iş bitince Pod **Stop** edilmeli. Kalıcı depo sayesinde tekrar Start edildiğinde yeniden kurulum gerekmiyor, sadece `vllm serve ...` komutu tekrar çalıştırılıyor.

### `.env` Dosyasında Kullanılan Değişkenler (`co-build-ai-server`)
```
VLLM_BASE_URL=https://[pod-id]-8000.proxy.runpod.net/v1
VLLM_API_KEY=EMPTY
VLLM_MODEL_ADI=Qwen/Qwen2.5-32B-Instruct-AWQ
```
**Not:** `VLLM_BASE_URL`, Pod her yeniden deploy edildiğinde (yeni bir Pod oluşturulursa) değişebilir — güncel URL'i RunPod panelinden (Connect → Port 8000 → HTTP Service) alıp `.env`'i güncellemek gerekir. Kod, bu değerleri `os.getenv()` ile okuyor, `main.py` içine sabit yazılmadı.

### Kod Tarafında Değişen Şey
`main.py`'de artık `OllamaLLM` DEĞİL, **`ChatOpenAI`** (LangChain'in OpenAI-uyumlu istemcisi) kullanılıyor — çünkü vLLM, OpenAI API formatını taklit ediyor. Bu, gerçek OpenAI'a bağlandığı anlamına gelmiyor, `openai_api_base` parametresi RunPod'un kendi adresine yönlendiriliyor.

### Artık İkinci Bilgisayara (Wi-Fi Eşleşmesine) Gerek Yok
Önceden iki bilgisayarın aynı Wi-Fi/hotspot ağında olması gerekiyordu (Ollama yerel ağdaydı). **Artık gerekmiyor** — RunPod sunucusu gerçek internet üzerinden erişilebilir, hangi ağda olursa olsun (İBB Wi-Fi dahil) bağlanılabiliyor. Next.js ve FastAPI'nin aynı bilgisayarda çalışması bile mümkün hale geldi (opsiyonel, henüz taşınmadı, ama teorik engel yok).

## 4. Web Tarafı (Next.js — `co-build-ai` reposu)

- Next.js 16, App Router, TypeScript, Tailwind CSS v4
- Supabase: PostgreSQL + Authentication + RLS
- Tasarım sistemi: coral `#fd5e51`, periwinkle `#9fc2fa`, petal `#ffdef9`, ink `#3d3229`; fontlar: Plus Jakarta Sans, Fraunces, JetBrains Mono

### Dashboard Yeniden Yapılandırıldı
`(dashboard)` route group altında, sidebar + topbar düzeni kuruldu (TailAdmin referans alınarak). Şu an var olan sayfa yapısı (Claude Code tarafından genişletildi, kullanıcının bilmediği/hatırlamadığı kısımlar olabilir):
```
app/(dashboard)/
  ayarlar/ (tercihler, bildirimler, guvenlik, hesap, tehlikeli-bolge alt sayfaları)
  panel/ (developer-projects.tsx, founder-developers.tsx, quick-match.tsx)
  profil/ (founder-projects.tsx)
  mesajlar/
  projelerim/ (aktif, kabul-ettiklerim, teklifler, yururlukte alt sayfaları)
  yildizlarim/
  layout.tsx
app/components/
  sidebar.tsx, topbar.tsx, notification-bell.tsx, role-switcher.tsx,
  project-match-card.tsx, project-progress-card.tsx, rate-offer-form.tsx,
  rating-stars.tsx, stat-circle.tsx, trending-widget.tsx, availability-badge.tsx,
  progress-ring.tsx, avatar.tsx, chat-box.tsx, logout-button.tsx
app/lib/roles.ts
app/proje/[id]/
  developer-project-view.tsx, offers-list.tsx, payment-section.tsx
```
**Not:** Bu dosyaların TAM işlevsel durumu (hangisi test edildi, hangisi yarım) kullanıcı tarafından teyit edilmedi — Claude Code kendi oturumlarında bunları oluşturmuş, kullanıcı bazılarını hiç görmemiş olabilir. Yeni bir işe başlamadan önce mevcut kodu okuyup gerçek durumu tespit et, varsayımda bulunma.

### Dual-Role (Çift Rol) Sistemi — KISMEN BAŞLADI
`role-switcher.tsx` ve `app/lib/roles.ts` dosyaları oluşturulmuş — bu, daha önce "v2'nin ilk maddesi, MVP bitince yapılacak" diye planlanan **çift rol** (kullanıcının hem founder hem developer olabilmesi) özelliğinin **başlangıcı** gibi görünüyor. Bu, MVP tamamlanmadan erken başlatılmış olabilir — kullanıcıyla bu kapsam değişikliğini netleştir, çakışan/yarım kalan kısımları tamamla.

## 5. Veritabanı Şeması (Supabase) — Bilinen Tablolar

- `profiles` (id, user_type, full_name, bio, skills[], terms_accepted_at) — **`user_type` muhtemelen dual-role için değişiyor olabilir, kontrol et**
- `projects` (id, founder_id, title, raw_idea, generated_prd, required_skills[], status, idea_hash, idea_created_at, payment_type, payment_amount)
- `portfolio_items` (id, developer_id, title, description, file_url, item_type, issuer, item_date)
- `project_nda_acceptances`, `project_views` — durumu teyit edilmeli (arayüze bağlandı mı, bağlanmadı mı — önceki bilgi "bağlanmadı" idi ama `developer-project-view.tsx` dosyasının varlığı bunun değişmiş olabileceğini gösteriyor)
- `offers` — `offers-list.tsx`, `rate-offer-form.tsx`, `payment-section.tsx` dosyalarının varlığı, teklif sisteminin **kısmen veya tamamen kodlanmış** olabileceğini gösteriyor — MVP planında "henüz yapılmadı" deniyordu, bu artık geçersiz olabilir, kontrol et
- **YENİ EKLENECEK (henüz yapılmadı):** `profiles.has_verified_patent` (boolean) — Patent RAG özelliği için planlanıyor (bkz. Bölüm 8)

RLS tüm tablolarda aktif.

## 6. AI Servisi (`co-build-ai-server` reposu)

### Mevcut Yapı
- `main.py` — FastAPI, asenkron PRD üretimi (`/prd-uret-baslat`, `/prd-durum/{id}`), timeout mekanizması (5 dakika, `JOB_TIMEOUT_SECONDS`), eş zamanlı istek kuyruğu (`queue.Queue` + tek worker thread) eklendi
- `veri_yukle.py` — RAG için startup verisi yükleme script'i (tek seferlik, çalıştırıldı)
- `demo_kullanici_uret.py` + `demo_veri.json` — Demo/sunum verisi (15 yazılımcı + portfolyo, 8 fikir sahibi + bio, 8 proje), Supabase Admin API ile gerçek auth kullanıcıları olarak yüklendi
- `eslestirme_endpoints.py`, `matchmaking_engine.py` — **YENİ (kullanıcı hatırlamıyor, detayları bilinmiyor)**: Founder'a PRD sonrası 5 uygun yazılımcı öneren semantik eşleştirme sistemi. `rank_bm25`, `langchain_community` gibi ek kütüphaneler gerektiriyor. Skor hesaplama mantığı (`benzerlik_skoru`, `hibrit_skor`) düşük/anlamsız değerler üretiyor olabilir (0.03 gibi), muhtemelen normalizasyon sorunu var, incelenip düzeltilmeli.
- RAG (startup örnekleri): `sentence-transformers` (`all-MiniLM-L6-v2`) + ChromaDB (`chroma_data/startup_ornekleri` koleksiyonu, ~1500 kayıt, HackerNoon/where-startups-trend veri setinden, MIT lisanslı)

### Prompt Yapısı
Tek birleşik prompt: PRD (Ürün Özeti, Hedef Kullanıcı, Temel Özellikler, Teknik Gereksinimler, Benzer Örnekler ve Farklılaşma, Tahmini Altyapı Maliyeti Kategorisi) + Beceri Etiketleri. Ayrıştırma birden fazla format dener (`## Beceri Etiketleri`, `**Beceri Etiketleri**`, düz metin) çünkü model tutarsız formatlıyor — bazen numaralı liste de yazabiliyor, ayrıştırma bunu her zaman yakalamayabilir, bilinen bir kusur.

### GitHub Repo
`github.com/berna1727/co-build-ai-server` (Private). README.md (İngilizce, profesyonel) ve requirements.txt eklendi. `startups.xlsx` (13MB, ham veri) yanlışlıkla commit edilmiş, temizlenmedi (düşük öncelik).

## 7. Git İş Akışı — ÖNEMLİ DENEYİMLER

- Proje artık **iki ayrı repo**: `co-build-ai` (esmacakar hesabı) ve `co-build-ai-server` (berna1727 hesabı)
- **Merge conflict yaşandı** (Esma'nın yerel dual-role değişiklikleri ile GitHub'daki Claude Code değişiklikleri çakıştı) — `profil/page.tsx`, `projelerim/yururlukte/page.tsx`, `proje/[id]/page.tsx` dosyalarında. Bu tür çakışmalarda Claude Code'un dosyaları okuyup iki tarafı da koruyarak birleştirmesi isteniyor, kullanıcı elle çözmüyor.
- Rutin: `git pull` (başlamadan önce) → çalış → `git add . && git commit -m "..." && git push`
- Kullanıcı, Claude Code'a büyük değişiklik yaptırmadan önce commit atma alışkanlığını henüz tam oturtmadı, hatırlatmak faydalı olabilir

## 8. AKTİF OLARAK PLANLANAN: Patent RAG + Tescilli Mucit Çarpanı

Bu, henüz uygulanmamış olabilir — kullanıcı bu promptu verdiyse aşağıdaki gibi ilerlenmeli, vermediyse bu bir sonraki iş.

**Kapsam:**
1. **Patent veri seti:** Hugging Face `HUPD/hupd` (Harvard USPTO Patent Dataset) — Google Cloud/BigQuery DEĞİL (kredi kartı/ön provizyon gerektirdiği için vazgeçildi). G06F/G06N sınıflı, 3000-5000 kayıt, ayrı bir ChromaDB koleksiyonu (`patent_ornekleri`).
2. **Patent çakışma kontrolü:** PRD üretim akışına yeni bir bölüm (`## Patent/Özgünlük Kontrolü`) — bulunan benzer patentleri gösterir, yüksek benzerlikte hukuki danışmanlık önerir, kesin hukuki iddia üretmez.
3. **Tescilli Mucit Çarpanı:** `profiles.has_verified_patent` (boolean, yeni sütun) — eşleştirme motorunda bu true olan yazılımcıların skoruna `PATENT_CARPAN = 1.15` çarpanı uygulanır.
4. Bu iş **RunPod Pod'u kapalıyken de yapılabilir** — patent verisi indirme/embedding işlemi CPU'da çalışır, GPU'ya (dolayısıyla vLLM'e) ihtiyaç duymaz. Sadece gerçek PRD/patent kontrolü testi için Pod açık olmalı.

**Not — Daha önce v2'ye ertelenmiş bir özellik (patent karşılaştırması) şimdi kısmi/prototip olarak MVP'ye alınıyor.** Kapsamı net: gerçek zamanlı, resmi patent ofisi entegrasyonu DEĞİL, statik bir veri seti üzerinden RAG tabanlı bir ön-kontrol prototipi.

## 9. Bilinçli Olarak v2'ye Ertelenen Özellikler (Hâlâ Geçerli)

- Biyometrik KYC, Stripe/escrow gerçek ödeme
- Tinder-tarzı swipe eşleştirme (kesin olarak vazgeçildi)
- GitHub commit'e göre otomatik milestone/ödeme tetikleme
- Platform içi kod editörü/sandbox
- Gerçek zamanlı canlı web/rakip taraması
- Mobil uygulama
- Tam kapsamlı, resmi patent ofisi entegrasyonu (yukarıdaki prototip bunun yerine geçiyor, MVP kapsamında)

## 10. Belirsiz/Kontrol Edilmesi Gereken Noktalar (Claude Code İçin Uyarı)

Bu proje, kullanıcının kendisinin de "Claude Code baya geride kalmış" dediği bir noktada — yani **kod tabanı, kullanıcının hafızasından daha ileride**. Yeni bir işe başlamadan önce:
1. Mevcut dosyaları oku, varsayımda bulunma
2. Kullanıcıya "şu an X dosyası şöyle görünüyor, bu senin beklediğin gibi mi?" diye doğrulat
3. Özellikle `offers`, `project_nda_acceptances`, `project_views`, dual-role sisteminin **gerçek/güncel durumunu** ilk iş olarak netleştir

## 11. Kod Tarzı Notları

- Next.js App Router yapısı, client component'ler `"use client"` ile başlıyor
- Tailwind renkleri `globals.css`'te `@theme` bloğunda
- Python tarafında Türkçe fonksiyon/değişken isimleri (`benzer_ornekleri_bul`, `patent_cakismasi_kontrol_et` gibi)
- `.env` üzerinden okunan değerler `os.getenv()` ile, path'ler hardcode edilmiyor
- Kod yorumları Türkçe

---

**Bu dosyayı okuyan Claude Code'a not:** Kullanıcı (Esma) Python/ML deneyimli, web geliştirmede artık orta seviyede. Adım adım, gerekçeli ilerlemeyi seviyor. **En kritik nokta:** proje son birkaç oturumda hızla büyüdü (RunPod geçişi, dashboard genişlemesi, eşleştirme motoru, dual-role başlangıcı) ve kullanıcının kendisi bile tüm değişikliklerin farkında değil — bu yüzden varsayımda bulunmak yerine önce mevcut kodu okuyup durumu netleştirmek, sonra ilerlemek en güvenlisi.
