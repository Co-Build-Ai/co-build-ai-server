-- "Gönderilen Teklifler" sayfası icin: notifications tablosu su ana kadar
-- sadece ALICIYI (user_id) tutuyordu, GONDEREN hic kaydedilmiyordu. Founder'in
-- kendi gonderdigi davetleri (Dogrudan Arama / PRD sonrasi top-5) listeleyebilmesi
-- icin sender_id ekleniyor + bunu okuyabilmesi icin bir select politikasi.

alter table notifications add column if not exists sender_id uuid references auth.users(id) on delete set null;

create policy "Gönderen kendi gönderdiği bildirimleri görebilir"
on notifications for select
to authenticated
using (sender_id = auth.uid());
