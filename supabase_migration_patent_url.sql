-- ============================================================================
-- Co-Build AI — Patent Belgesi Kendi Kendine Yükleme Migration'ı
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'de ELLE çalıştırın.
--
-- Amaç: Yazılımcının kendi profilinden CV yükler gibi bir patent belgesi
-- (PDF) yükleyebilmesi. Belge yüklendiğinde `has_verified_patent` de
-- otomatik true yapılır (kendi beyanı, admin onayı beklenmez — bkz.
-- supabase_migration_patent_carpan.sql'deki önceki not, bu davranış
-- kullanıcı isteğiyle bilinçli olarak basitleştirildi).
-- ============================================================================

alter table profiles add column if not exists patent_url text;

-- Storage bucket: patent-belgeleri (public — CV/portfolyo bucket'larıyla aynı desen)
insert into storage.buckets (id, name, public)
values ('patent-belgeleri', 'patent-belgeleri', true)
on conflict (id) do nothing;

create policy "Herkes patent belgelerini görebilir"
on storage.objects for select
using (bucket_id = 'patent-belgeleri');

create policy "Kullanıcılar kendi patent belgesini yükleyebilir"
on storage.objects for insert
with check (
  bucket_id = 'patent-belgeleri'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "Kullanıcılar kendi patent belgesini güncelleyebilir"
on storage.objects for update
using (
  bucket_id = 'patent-belgeleri'
  and (storage.foldername(name))[1] = auth.uid()::text
);
