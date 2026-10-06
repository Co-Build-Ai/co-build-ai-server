# Co-Build AI Server — CLAUDE.md (v5, 2026-09-16)

Bu dosya Claude Code oturumlarında otomatik okunur. **v5 notu:** Bu revizyon, tüm dosyalar tek tek okunarak ve gerçek `git log` ile hazırlandı. Önceki sürümün iddia ettiği bazı "düzeltildi" notları **doğru değildi** (aşağıda işaretlendi) — bir sonraki oturumda bu dosyaya da körü körüne güvenme, özellikle "düzeltildi" notlarını tekrar doğrula.

## 1. Proje Nedir

`co-build-ai` (Next.js) platformunun AI servisi: ham fikri PRD'ye çeviren LangGraph agent'ı, patent RAG ön-kontrolü, ve geliştirici/proje eşleştirme motorunu barındıran FastAPI uygulaması. Kapsamlı proje özeti için `co-build-ai` reposundaki kök `CLAUDE.md` (v5)'e bak — burada sadece bu repoya özel detaylar var.

## 2. `main.py` — FastAPI Uygulaması

**Endpoint'ler (doğrudan main.py'de):**
- `GET /` — health check
- `POST /prd-uret-baslat` — `{project_id, title, raw_idea, budget_type?, sektor?}` alır, asenkron kuyruğa ekler, `{"status":"started","kuyruk_sirasi":N}` döner
- `GET /prd-durum/{project_id}` — `job_store` dict'inden durumu okur

Ayrıca `app.include_router(eslestirme_router)` ile `eslestirme_endpoints.py`'deki 5 endpoint mount ediliyor (bkz. Bölüm 5).

**Kuyruk mekanizması:** tek bir `asyncio.Queue` (`istek_kuyrugu`) + `lifespan()` içinde başlatılan tek bir arka plan worker (`kuyruk_isleyici()`), işleri **sırayla tek tek** işliyor. Sonuçlar `job_store: dict[str, dict]` içinde — **bellek-içi, kalıcı değil**, sunucu restart'ında kaybolur.

**Timeout:** her istek için ayrı bir `asyncio.create_task` (`timeout_kontrolcusu`), `JOB_TIMEOUT_SECONDS = 300` (5 dk) sonra hâlâ `"processing"` ise zorla `"error"` yapıyor. İş zaten bitmişse bu task sessizce no-op olur (iptal edilmiyor ama zararsız).

**CORS:** tamamen açık (`allow_origins=["*"]`).

**ChromaDB koleksiyonları (main.py'de açılıyor):** `startup_ornekleri` (varsayılan mesafe metriği, cosine DEĞİL — `veri_yukle.py` ile tutarlı ama `patent_ornekleri`'nden farklı) ve `patent_ornekleri` (`hnsw:space: cosine` açıkça belirtilmiş).

**Patent kontrolü akışı:** `patent_cakismasi_kontrol_et()` main.py'de, graph'tan ÖNCE çağrılıyor, sonucu düz metin olarak PRD prompt'una enjekte ediliyor (bkz. kök CLAUDE.md Bölüm 5).

## 3. `prd_agent.py` — LangGraph Self-Reflection Döngüsü

Detaylar için kök `CLAUDE.md` Bölüm 5'e bak. Ek teknik notlar:
- İki ayrı `ChatOpenAI` client: `llm` (max_tokens=1024, üretim için), `elestiri_llm` (max_tokens=300, öz-eleştiri için). İkisi de aynı `VLLM_*` env değişkenlerini okuyor.
- `_YABANCI_ALFABE_RE`: CJK/Kana/Hangul/Kiril Unicode aralıklarını yakalayan regex, LLM'e sormadan önce çalışıyor.
- `_skills_ve_prd_ayikla`: virgülle ayrılmış ve madde-işaretli listeleri parse ediyor, `MAKS_SKILLS = 8` (prompt ≤5 istiyor, küçük bir tutarsızlık).

## 4. `matchmaking_engine.py`

- `en_uygun_gelistiricileri_bul()` — semantik arama, `HuggingFaceEmbeddings(all-MiniLM-L6-v2, normalize_embeddings=True)`, Supabase RPC `match_developers`.
- `hibrit_eslestirme_yap()` — semantik top-20 + BM25 (tüm havuz, `_tum_gelistirici_havuzunu_getir`, max `BM25_ADAY_HAVUZU_BOYUTU=200`), RRF (`_RRF_K=60`).
- `PATENT_CARPAN = 1.15` — RRF skoruna, `sorted()[:top_k]` seçiminden ÖNCE uygulanıyor (satır ~726). `_patentli_gelistiricileri_getir()` `profiles.has_verified_patent`'i okuyor, migration yoksa sessizce boş küme + uyarı log'u (geriye dönük uyumlu).
- `uyum_skorlarini_hesapla_ve_ata()` — hibrit skor varsa 65-98'e, yoksa ham kosinüs benzerliği 0-100'e ölçekleniyor.
- `filtre_metadata` (`budget_type`/`sektor`) — RPC'ye `filter_budget_type`/`filter_sektor` olarak geçiyor, boşsa atlanıyor.
- **`developer_embeddings` tablosu:** developer_id, full_name, skills, bio, kaynak_metin, embedding(384), opsiyonel budget_type/sektor. Upsert: `gelistirici_profilini_vektorle()`.
- **⚠️ `project_embeddings` tablosu da burada yönetiliyor** (önceki dokümantasyonda hiç yoktu): `proje_profilini_vektorle()` / `en_uygun_projeleri_bul()`, RPC `match_projects`. Bu, geliştiricinin "bana uygun proje bul" aramasını besliyor. Toplu karşılığı: `projeleri_toplu_vektorle.py` (status='published' tüm projeleri vektörler).
- `EMBEDDING_BOYUTU = 384` sabit.

## 5. `eslestirme_endpoints.py` — 5 Endpoint (Önceki Dokümantasyonda 3 Deniyordu)

1. `POST /gelistirici/vektorle`
2. `POST /eslestir/semantik-top5`
3. `POST /eslestir/hibrit`
4. `POST /proje/vektorle` — **YENİ dokümante edildi**, proje ilanını vektörler
5. `POST /eslestir/proje-top5` — **YENİ dokümante edildi**, yayınlanmış projelerde semantik arama (geliştirici → proje yönü)

## 6. Patent RAG Veri Yükleme (`patent_veri_yukle.py`)

- Kaynak: HuggingFace `HUPD/hupd`. Filtre: CPC/IPC kodu `G06F` veya `G06N` ile başlıyor + boş olmayan özet. Hedef: 3000-5000 kayıt (`HEDEF_MIN_KAYIT`/`HEDEF_MAKS_KAYIT`).
- Üç mod: varsayılan (`sample` config), `--yil YYYY` (tek yılın küçük dosyasını doğrudan indirir, script'in kendi önerdiği yöntem), `--tam` (57.5GB, interaktif onay gerekir, pratik değil).
- `datasets==2.19.0` bilerek sabit — daha yeni sürüm HUPD'nin eski "loading script" yöntemini kırıyor.
- ChromaDB koleksiyonu: `patent_ornekleri` (`hnsw:space: cosine`).
- **Gerçek kayıt sayısı kod/yorumlarda doğrulanabilir değil** — sadece hedef aralık (3000-5000) var, "şu an X kayıt var" gibi iddialar ölçülmüş gerçek değil, tahmindir.

## 7. Startup RAG Verisi (`veri_yukle.py`)

`startups.xlsx` (sheet "main", kolonlar: Startups Name/description/industry), boş/kısa (<30 karakter) açıklamalar atılıyor, ilk 1500 satırla sınırlı (`df.head(1500)`, gerçek bir üst sınır, sadece açıklama değil). ChromaDB koleksiyonu: `startup_ornekleri`.

## 8. Demo/Sunum Script'leri — Tam Envanter

Hepsi aynı güvenlik desenini kullanır: `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` zorunlu, şablon değer kontrolü, sır maskeleme, `EVET` yazarak onay (ya da `DEMO_SEED_ONAY=true`).

| Script | Ne yapar | Dokunduğu hesaplar |
|---|---|---|
| `demo_kullanici_uret.py` | `demo_veri.json`'dan temel seed: yazılımcı+girişimci+proje, sahte CV/sertifika PDF | `demo.yazilimci{i}@...`, `demo.girisimci{i}@...` |
| `demo_zengin_veri_uret.py` | "Zengin" set: 10 yazılımcı (3'ü patentli), 5 girişimci, 10 proje (şablon PRD, gerçek LLM çağrısı yok), teklifler + karşılıklı rating | `zengin.dev{i}@...`, `zengin.founder{i}@...` |
| `demo_bos_profil_doldur.py` | İsimsiz test hesaplarına (full_name eşleşmesiyle) bio/skill/CV/portfolyo doldurur | "deneme deneme", "yıldız koz", "Dual Test Kullanici", "dual hesap", "ikiz", "ikiz yıldız", "ceren soyak", "deneme4yazilimci" (sadece portfolyo, bio/skill'i korunur) |
| `demo_isim_degistir.py` | Yukarıdaki placeholder isimleri gerçekçi Türkçe isimlere çevirir, CV/sertifika PDF'lerini yeni isimle yeniden üretir | deneme deneme→Efe Karaca, deneme4yazilimci→Yusuf Güler, **yıldız koz→Bora Aydın**, Dual Test Kullanici→Cansu Erdoğan, dual hesap→Tuna Eren, ikiz→Mert Sönmez, ceren soyak→Melis Soysal |
| `demo_patent_arttir.py` | 4 hesaba patent ekler (has_verified_patent + PDF) | Selin Yıldız, Onur Kurt, Deniz Koç, Mehmet Demir |
| `demo_patent_basliklarini_doldur.py` | `patent_title` kolonunu geriye dönük doldurur | Selin Yıldız, Onur Kurt, Deniz Koç, Mehmet Demir, **Bora Aydın**, Deniz Aydemir, Kaan Yıldırım, Zeynep Kaya |
| `demo_pdf_fontlarini_duzelt.py` | TÜM mevcut CV/patent/sertifika PDF'lerini Arial (Türkçe karakter destekli) fontla, URL'den path çözerek aynı yere yeniden üretir | cv_url/patent_url'i olan her profil + her certificate portfolio öğesi |
| `demo_bora_aydin_zenginlestir.py` | **Tek kişiye özel, hardcoded UUID:** birincil patent + ikincil patent (certificate-as-patent) + 4 AI/sinyal işleme/pazarlama projesi | **Bora Aydın** (`f934028e-8115-4dfb-a701-4feca1c55bca`) |
| `demo_ceyda_portfolyo_ekle.py` | **Tek kişiye özel, hardcoded UUID:** 2 proje + 2 sertifika daha, 1 eski sertifikayı Arial ile yeniler | **Ceyda Alemdar** (`dea88211-a103-4787-a4b9-0bb95f5a544e`) — full_name hiçbir seed/rename script'inde geçmiyor, muhtemelen gerçek bir web kaydı |
| `demo_profil_fotolari_yukle.py` / `_2.py` / `_3.py` | Sırasıyla 13/11/15 profile `Downloads\profile pics` klasöründen cinsiyete göre elle eşlenmiş avatar yükler; `_3.py` emoji/özel karakterli dosya adları için `os.scandir` prefix-eşleşmesi kullanıyor | Toplam ~39 isim, tam liste script içinde |
| `demo_profil_fotolari_yukle_4.py` | Farklı bir klasörden (`Downloads\foto`), kalan avatarsız erkek profilleri doldurur, PNG destekli | Deniz Aydemir, Barış Güneş, Burak Çelik, Yusuf Güler |

**Geliştirici makinesine özel, taşınabilir değil:** `C:\Users\DELL\Downloads\profile pics`, `C:\Users\DELL\Downloads\foto`, `C:\Windows\Fonts` gibi mutlak Windows path'leri — bunlar tek-seferlik kişisel script'ler, deploy edilen serviste yer almıyor, bilerek böyle.

## 9. `gelistiricileri_toplu_vektorle.py` / `projeleri_toplu_vektorle.py`

- `gelistiricileri_toplu_vektorle.py`: `user_type in ["developer", "both"]` filtreli (kod içi yorumda bunun bilerek düzeltildiği not edilmiş — eskiden sadece `"developer"` filtreleniyordu, dual-role hesapları atlıyordu).
- `projeleri_toplu_vektorle.py`: `status='published'` tüm projeleri `project_embeddings`'e vektörler — önceki dokümantasyonda hiç bahsedilmiyordu.

## 10. `supabase_migration_*.sql` — 10 Dosyanın Tam Listesi (Önceki Dokümantasyon Sadece 5 Tanesini Biliyordu)

| Dosya | Ne ekliyor |
|---|---|
| `supabase_migration_metadata_filter.sql` | `developer_embeddings.budget_type`/`sektor` + `match_developers` RPC'sine filtre parametreleri (fonksiyon overload çakışması için `drop function` notu dahil) |
| `supabase_migration_patent_carpan.sql` | `profiles.has_verified_patent boolean default false` |
| `supabase_migration_patent_url.sql` | `profiles.patent_url` + `patent-belgeleri` bucket + RLS (self-upload, admin onayı yok) |
| `supabase_migration_starred_developers.sql` | `starred_developers` tablosu + RLS (yıldızlama butonu bu olmadan sessizce çalışmıyordu) |
| `supabase_migration_banner.sql` | `profiles.banner_url` + `banners` bucket RLS |
| `supabase_migration_patent_title.sql` | `profiles.patent_title` — **önceki dokümantasyonda yoktu** |
| `supabase_migration_bildirim_gonderen.sql` | `notifications.sender_id` + select politikası — **önceki dokümantasyonda yoktu** |
| `supabase_migration_proje_disi_davet.sql` | `notifications` insert politikası: `project_id IS NULL` + `type='project_invite'` izni (Doğrudan Arama/Hızlı Eşleştirme'den proje bağlamı olmadan davet) — **önceki dokümantasyonda yoktu** |
| `supabase_migration_project_embeddings.sql` | `project_embeddings` tablosu + `match_projects` RPC; **kasıtlı olarak vektör indexi yok** (az kayıtta ivfflat yanlış sonuç veriyordu) — **önceki dokümantasyonda yoktu, tüm bir tablo eksikti** |

## 11. `requirements.txt` — 2026-09-16'da Gerçekten Düzeltildi

**Önceki not "UTF-8'e çevrildi" diyordu ama YANLIŞTI** — dosya hâlâ UTF-16LE'ydi (`aiohappyeyeballs==2.7.1` her karakter arası `\x00` ile). 2026-09-16'da gerçekten UTF-8'e çevrildi VE eksik olan `reportlab==4.2.5` eklendi (tüm `demo_*.py` script'leri `reportlab` kullanıyor ama pakette hiç yoktu — temiz bir `pip install -r requirements.txt` demo script'lerini çalıştıramazdı). **Bir sonraki oturumda bu dosyanın gerçekten UTF-8 kaldığını `file requirements.txt` ile doğrula** — bu ikinci kez "düzeltildi" deniyor.

Önemli bağımlılık versiyonları: `fastapi==0.141.1`, `langchain==1.3.15` (+core/community/huggingface/openai), `langgraph==1.2.11`, `chromadb==1.5.9`, `sentence-transformers==6.0.0`, `datasets==2.19.0` (bilerek düşük), `rank-bm25==0.2.2`, `supabase==2.31.0`, `torch==2.13.0`, `transformers==5.15.1`.

## 12. GitHub Repo

`github.com/berna1727/co-build-ai-server` (Private). `startups.xlsx` (13MB, ham veri) hâlâ commit'li, temizlenmedi (düşük öncelik). `chroma_data/` ve `venv/` çalışma ağacında mevcut — `.gitignore` kapsamını yeni bir push öncesi kontrol et.

## 13. Git Geçmişi Özeti

Toplam **17 commit** var (2026-09-16 itibarıyla, `git log --oneline | wc -l` ile doğrulandı — önceki bir oturumda yanlışlıkla "40" denmişti). Repo Ollama+RAG basit bir FastAPI servisi olarak başladı, sonra README/secret temizliği, sonra "model büyümeye gitti" (LangGraph/hibrit arama/patent RAG eklendi), en son iki commit demo veri cilası: placeholder hesap isimlerini gerçekçi isimlere çevirme + dual-role vektörleme filtresini düzeltme + davet/patent altyapısını tamamlama. Yani **şu an aktif iş, yeni özellik geliştirme değil, sunum/demo cilası ve zaten var olan özelliklerdeki boşlukları kapatma** aşamasında.

## 14. Kod Tarzı Notları

- Python tarafında Türkçe fonksiyon/değişken isimleri (`benzer_ornekleri_bul`, `patent_cakismasi_kontrol_et` gibi), kod yorumları Türkçe.
- `.env` üzerinden okunan değerler `os.getenv()` ile — RunPod'a özgü HİÇBİR env değişkeni kodda yok, sadece jenerik `VLLM_*`.
- Demo/tek-seferlik script'lerdeki hardcoded Windows path'leri ve UUID'ler bilinçli — taşınabilir olmaları beklenmiyor.
