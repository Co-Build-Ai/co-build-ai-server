-- Dogrudan Arama / Hizli Eslestirme gibi belirli bir projeye bagli olmayan
-- "Teklif Gonder" davetleri icin: mevcut notifications insert politikasi
-- muhtemelen project_id uzerinden proje sahipligini kontrol ediyor, bu da
-- project_id NULL oldugunda (arama sonucu bir projeye bagli degilken) insert'i
-- reddediyor. Bu, mevcut politikaya DOKUNMADAN, ek bir izin politikasi ekler
-- (Postgres RLS'de birden fazla permissive policy OR ile birlesir).
create policy "Founder proje disi davet bildirimi gonderebilir"
on notifications for insert
to authenticated
with check (
  project_id is null
  and type = 'project_invite'
);
