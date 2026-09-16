-- ============================================================================
-- Co-Build AI — Proje Vektörleme Migration'ı (Yazılımcı Tarafı "Doğrudan Arama")
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'de ELLE çalıştırın.
-- Amaç: developer_embeddings / match_developers çiftinin proje karşılığını
-- kurmak. Yazılımcı, "ne tür bir projede çalışmak istediğini" serbest
-- metinle tarif ediyor; biz bunu embedding'e çevirip YAYINLANMIŞ projeler
-- arasında en yakınlarını buluyoruz (bkz. matchmaking_engine.py içindeki
-- proje_profilini_vektorle / en_uygun_projeleri_bul).
--
-- Ön koşul: pgvector eklentisi zaten developer_embeddings için etkin
-- (bu migration'ı çalıştırmadan önce "create extension if not exists vector;"
-- zaten uygulanmış olmalı).
-- ============================================================================

-- 1) project_embeddings tablosu
create table if not exists project_embeddings (
    project_id uuid primary key references projects(id) on delete cascade,
    title text not null,
    required_skills text[] not null default '{}',
    kaynak_metin text not null,
    embedding vector(384) not null,
    updated_at timestamptz not null default now()
);

-- 2) Kosinüs benzerliği için indeks EKLEMİYORUZ (bilinçli karar):
--    ivfflat, listeleri veri sayısına göre iyi ayarlanmazsa (örn. az satırlı
--    bir tabloda lists=100) yanlış/eksik sonuçlar döndürebiliyor — canlıda
--    tam proje başlığıyla arama yapıldığında bile doğru projeyi bulamadığı
--    tespit edildi. project_embeddings satır sayısı küçük kaldığı sürece
--    (yüzlerce/birkaç bin) indekssiz sequential scan hem doğru hem yeterince
--    hızlı. İleride satır sayısı gerçekten büyürse (örn. > 10.000), lists'i
--    satır sayısına göre ayarlanmış (yaklaşık satır/1000) bir ivfflat ya da
--    hnsw indeksi eklenmesi düşünülebilir.

-- 3) match_projects RPC fonksiyonu — match_developers'ın proje karşılığı
create or replace function match_projects(
    query_embedding vector(384),
    match_count int default 5
)
returns table (
    project_id uuid,
    title text,
    required_skills text[],
    kaynak_metin text,
    benzerlik float
)
language plpgsql
as $$
begin
    return query
    select
        pe.project_id,
        pe.title,
        pe.required_skills,
        pe.kaynak_metin,
        (1 - (pe.embedding <=> query_embedding))::float as benzerlik
    from project_embeddings pe
    join projects p on p.id = pe.project_id
    where p.status = 'published'
    order by pe.embedding <=> query_embedding
    limit match_count;
end;
$$;
