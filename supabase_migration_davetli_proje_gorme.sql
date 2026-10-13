-- Davet edilen yazilimci, proje TASLAK olsa bile (yayinlanmadan) PRD'yi gorebilsin.
-- Boylece founder projeyi herkese yayinlamak zorunda kalmadan sadece sectigi
-- kisiyle calisabilir. Mevcut politikalara DOKUNMAZ; ek bir SELECT izni ekler
-- (Postgres RLS'de birden fazla permissive policy OR ile birlesir).
-- Kosul: kullanicinin kendi notifications satirlarinda bu projeye ait
-- 'project_invite' tipinde bir davet olmasi.
create policy "Davet edilen yazilimci taslak projeyi gorebilir"
on projects for select
to authenticated
using (
  exists (
    select 1
    from notifications n
    where n.project_id = projects.id
      and n.user_id = auth.uid()
      and n.type = 'project_invite'
  )
);
