from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer

import prd_agent
from eslestirme_endpoints import router as eslestirme_router

logger = logging.getLogger("cobuild.main")

# RAG için: embedding modeli ve ChromaDB bağlantısı
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_data")
startup_collection = chroma_client.get_or_create_collection(name="startup_ornekleri")
# Patent koleksiyonu: cosine benzerliği kullanıyoruz ki eşik kontrolü
# (PATENT_BENZERLIK_ESIGI) doğrudan "1 - mesafe" ile hesaplanabilsin.
# Bkz. patent_veri_yukle.py — aynı ayarla oluşturulmalı.
patent_collection = chroma_client.get_or_create_collection(
    name="patent_ornekleri",
    metadata={"hnsw:space": "cosine"},
)

PATENT_BENZERLIK_ESIGI = 0.75  # cosine benzerliği bu değeri aşarsa "yüksek benzerlik" uyarısı


def benzer_ornekleri_bul(raw_idea: str, n_results: int = 3) -> str:
    """Kullanıcının fikrine en yakın gerçek proje örneklerini ChromaDB'de arar."""
    query_embedding = embedding_model.encode([raw_idea]).tolist()
    results = startup_collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
    )

    if not results["documents"] or not results["documents"][0]:
        return "Bulunamadı."

    ornekler = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        isim = meta.get("name", "Bilinmeyen")
        sektor = meta.get("industry", "Belirtilmemiş")
        kisa_aciklama = doc[:200] + ("..." if len(doc) > 200 else "")
        ornekler.append(f"- {isim} ({sektor}): {kisa_aciklama}")

    return "\n".join(ornekler)


def patent_cakismasi_kontrol_et(raw_idea: str, n_results: int = 3) -> str:
    """
    Kullanıcının fikrini `patent_ornekleri` koleksiyonunda (bkz.
    patent_veri_yukle.py) arar ve en yakın patentleri, varsa "yüksek
    benzerlik" uyarısıyla birlikte metin olarak döner.

    ÖNEMLİ: Bu SADECE otomatik, kaba bir ön kontroldür — kesin bir hukuki
    tespit/iddia ÜRETMEZ. Gerçek bir patent çakışması değerlendirmesi için
    her zaman bir patent avukatına/vekiline danışılmalıdır.
    """
    if patent_collection.count() == 0:
        return "Patent veri seti henüz yüklenmemiş (bkz. patent_veri_yukle.py)."

    query_embedding = embedding_model.encode([raw_idea]).tolist()
    results = patent_collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
    )

    if not results["documents"] or not results["documents"][0]:
        return "İlgili bir patent bulunamadı."

    satirlar = []
    en_yuksek_benzerlik = 0.0
    for doc, meta, mesafe in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        # Koleksiyon cosine uzayında oluşturulduğu için: benzerlik = 1 - mesafe
        benzerlik = 1 - mesafe
        en_yuksek_benzerlik = max(en_yuksek_benzerlik, benzerlik)
        patent_no = meta.get("patent_number", "Bilinmeyen")
        baslik = meta.get("title", "Başlıksız")
        kisa_ozet = doc[:200] + ("..." if len(doc) > 200 else "")
        satirlar.append(
            f"- Patent No: {patent_no} | {baslik} (benzerlik: {benzerlik:.2f})\n  {kisa_ozet}"
        )

    sonuc = "\n".join(satirlar)
    if en_yuksek_benzerlik > PATENT_BENZERLIK_ESIGI:
        sonuc += (
            f"\n\nYÜKSEK BENZERLİK UYARISI: En yakın patentle benzerlik oranı "
            f"{en_yuksek_benzerlik:.2f} — eşik değeri ({PATENT_BENZERLIK_ESIGI}) aşıldı."
        )

    return sonuc


class FikirRequest(BaseModel):
    project_id: str
    title: str
    raw_idea: str
    budget_type: str | None = None  # örn: "Sabit Ücret" / "Hisse" — metadata ön-filtreleme için
    sektor: str | None = None       # örn: "Fintech" — metadata ön-filtreleme için


# İş durumlarını geçici olarak bellekte tutan basit bir depo
# (proje_id -> {"status": "processing" / "done" / "error", ...})
job_store: dict[str, dict] = {}
# İstekleri sırayla işlemek için asenkron kuyruk
istek_kuyrugu: asyncio.Queue = asyncio.Queue()

JOB_TIMEOUT_SECONDS = 300  # 5 dakika — RunPod RTX 4090 + vLLM (Qwen2.5-32B-AWQ) ile
# canlı testte tüm döngü (üretim + eleştiri + eşleştirme) ~35 saniyede tamamlandı,
# bu yüzden 5 dakika bol bol yeterli bir güvenlik payı.


async def kuyruk_isleyici():
    """Kuyruktaki işleri tek tek, sırayla işler. Uygulama boyunca arka planda çalışan asenkron görev."""
    while True:
        project_id, title, raw_idea, budget_type, sektor = await istek_kuyrugu.get()
        await prd_is_akisini_calistir(project_id, title, raw_idea, budget_type, sektor)
        istek_kuyrugu.task_done()


async def timeout_kontrolcusu(project_id: str):
    """Belirtilen süre sonunda iş hâlâ 'processing' ise, hata durumuna düşürür."""
    await asyncio.sleep(JOB_TIMEOUT_SECONDS)
    if job_store.get(project_id, {}).get("status") == "processing":
        job_store[project_id] = {
            "status": "error",
            "message": "İşlem zaman aşımına uğradı (5 dakika). Lütfen tekrar deneyin.",
        }  # zaman aşımı management


async def prd_is_akisini_calistir(
    project_id: str, title: str, raw_idea: str, budget_type: str | None, sektor: str | None
):
    try:
        benzer_ornekler = await asyncio.to_thread(benzer_ornekleri_bul, raw_idea)
        patent_kontrolu = await asyncio.to_thread(patent_cakismasi_kontrol_et, raw_idea)

        sonuc = await prd_agent.prd_uret_ve_eslestir(
            title=title,
            raw_idea=raw_idea,
            benzer_ornekler=benzer_ornekler,
            patent_kontrolu=patent_kontrolu,
            budget_type=budget_type,
            sektor=sektor,
        )

        job_store[project_id] = {
            "status": "done",
            "prd": sonuc["prd"],
            "skills": sonuc["skills"],
            "onerilen_gelistiriciler": sonuc["onerilen_gelistiriciler"],
        }
    except ConnectionError as e:
        logger.exception("LLM sunucusuna (vLLM) bağlanılamadı (project_id=%s)", project_id)
        job_store[project_id] = {
            "status": "error",
            "message": f"LLM sunucusuna bağlanılamadı. vLLM (RunPod GPU) çalıştığından ve VLLM_BASE_URL'in doğru olduğundan emin olun. Detay: {e}",
        }
    except Exception as e:
        logger.exception("PRD üretim akışında beklenmeyen hata (project_id=%s)", project_id)
        job_store[project_id] = {"status": "error", "message": str(e)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_gorevi = asyncio.create_task(kuyruk_isleyici())
    yield
    worker_gorevi.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(eslestirme_router)


@app.get("/")
def read_root():
    return {"status": "AI servisi çalışıyor"}


@app.post("/prd-uret-baslat")
async def prd_uret_baslat(request: FikirRequest):
    kuyruktaki_sira = istek_kuyrugu.qsize()
    job_store[request.project_id] = {
        "status": "processing",
        "kuyruk_sirasi": kuyruktaki_sira,
    }

    await istek_kuyrugu.put(
        (request.project_id, request.title, request.raw_idea, request.budget_type, request.sektor)
    )

    asyncio.create_task(timeout_kontrolcusu(request.project_id))

    return {"status": "started", "kuyruk_sirasi": kuyruktaki_sira}


@app.get("/prd-durum/{project_id}")
def prd_durum(project_id: str):
    return job_store.get(project_id, {"status": "not_found"})
