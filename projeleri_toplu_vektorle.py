"""
projeleri_toplu_vektorle.py
============================================================================
Co-Build AI — Mevcut YAYINLANMIŞ projeleri toplu (geriye dönük) vektörler
============================================================================

Ne işe yarar?
-------------
`project_embeddings` tablosu kurulduğunda içi boştur (yeni tablo). Yeni
yayınlanan projeler `PublishForm` üzerinden otomatik vektörlenir (bkz.
web tarafında `app/proje/[id]/payment-section.tsx`), ama bu özellik
eklenmeden ÖNCE yayınlanmış projeler `project_embeddings`'te yok — yazılımcı
tarafındaki "Doğrudan Arama" onları bulamaz. Bu script, `projects`
tablosundaki TÜM yayınlanmış (`status = 'published'`) projeleri tek tek
`matchmaking_engine.proje_profilini_vektorle` ile vektörleyip
`project_embeddings` tablosuna yazar.

Zaten vektörlenmiş bir proje tekrar işlenirse `proje_profilini_vektorle`
upsert yaptığı için sorun çıkmaz, sadece günceller — bu yüzden embedding
modeli değişirse ya da PRD güncellenirse bu script tekrar çalıştırılabilir.

Çalıştırma:
    python projeleri_toplu_vektorle.py

Gereksinim:
    - Bu dosya `matchmaking_engine.py` ile AYNI klasörde olmalı.
    - .env dosyasında SUPABASE_URL ve SUPABASE_SERVICE_KEY tanımlı olmalı.
    - `supabase_migration_project_embeddings.sql` Supabase SQL Editor'de
      ÇALIŞTIRILMIŞ olmalı (project_embeddings tablosu + match_projects RPC).
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

from matchmaking_engine import (
    EslestirmeMotoruHatasi,
    ProjeProfili,
    proje_profilini_vektorle,
)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    sys.exit(
        "HATA: SUPABASE_URL / SUPABASE_SERVICE_KEY .env dosyasında tanımlı değil.\n"
        "Çözüm: '.env.example' dosyasını referans alarak '.env' dosyanızı kontrol edin."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def yayinlanmis_projeleri_getir() -> list[dict]:
    yanit = (
        supabase.table("projects")
        .select("id, title, generated_prd, raw_idea, required_skills")
        .eq("status", "published")
        .execute()
    )
    return yanit.data or []


def main() -> None:
    projeler = yayinlanmis_projeleri_getir()
    if not projeler:
        print("projects tablosunda yayınlanmış (status='published') kayıt bulunamadı — vektörlenecek bir şey yok.")
        return

    print(f"{len(projeler)} yayınlanmış proje bulundu, vektörleniyor...\n")

    basarili, atlanan = 0, 0
    for satir in projeler:
        proje = ProjeProfili(
            project_id=satir["id"],
            title=satir.get("title") or "İsimsiz Proje",
            generated_prd=satir.get("generated_prd") or "",
            raw_idea=satir.get("raw_idea") or "",
            required_skills=satir.get("required_skills") or [],
        )
        try:
            proje_profilini_vektorle(proje)
            print(f"  ✓ {proje.title} vektörlendi")
            basarili += 1
        except EslestirmeMotoruHatasi as exc:
            print(f"  ✗ {proje.title} atlandı: {exc}")
            atlanan += 1

    print(f"\nTamamlandı. Vektörlenen: {basarili}, Atlanan: {atlanan}, Toplam: {len(projeler)}")


if __name__ == "__main__":
    main()
