-- ============================================================================
-- Co-Build AI — Yıldızlanan Yazılımcılar (starred_developers) Migration'ı
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'de ELLE çalıştırın.
--
-- Neden gerekli: Frontend kodu (app/(dashboard)/yildizlarim/,
-- app/components/developer-match-row.tsx, app/proje/[id]/matched-developers.tsx,
-- app/(dashboard)/panel/page.tsx) `starred_developers` tablosunu okuyup
-- yazıyor, ama bu tablo Supabase'de hiç oluşturulmamış — yıldızlama butonu
-- arayüzde tıklanabiliyor ama hiçbir şey kaydetmiyordu (hata sessizce
-- yutuluyordu).
-- ============================================================================

create table if not exists starred_developers (
  id uuid primary key default gen_random_uuid(),
  founder_id uuid not null references profiles(id) on delete cascade,
  developer_id uuid not null references profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (founder_id, developer_id)
);

alter table starred_developers enable row level security;

create policy "Founder kendi yıldızladıklarını görebilir"
on starred_developers for select
using (auth.uid() = founder_id);

create policy "Founder yıldızlama ekleyebilir"
on starred_developers for insert
with check (auth.uid() = founder_id);

create policy "Founder kendi yıldızını kaldırabilir"
on starred_developers for delete
using (auth.uid() = founder_id);
