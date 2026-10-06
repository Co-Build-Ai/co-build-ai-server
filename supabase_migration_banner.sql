-- ============================================================================
-- Co-Build AI — Profil Banner (Kapak Fotoğrafı) Migration'ı
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'de ELLE çalıştırın.

-- Yeni (opsiyonel) kolon — varsayılan null, mevcut kayıtları etkilemez.
alter table profiles add column if not exists banner_url text;

-- Not: "banners" storage bucket'ı zaten oluşturuldu (public). Bucket için
-- RLS politikası, "avatars" bucket'ıyla aynı desende olmalı — kullanıcı
-- kendi klasörüne (userId/...) yazabilsin, herkes okuyabilsin. Eğer
-- "avatars" bucket'ında zaten böyle bir politika varsa, aşağıdaki de aynı
-- mantıkla ekleniyor:

create policy "Kullanicilar kendi banner'ini yukleyebilir"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'banners'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "Kullanicilar kendi banner'ini guncelleyebilir"
on storage.objects for update
to authenticated
using (
  bucket_id = 'banners'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "Herkes banner gorebilir"
on storage.objects for select
to public
using (bucket_id = 'banners');
