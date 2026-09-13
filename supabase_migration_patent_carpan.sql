-- ============================================================================
-- Co-Build AI — Tescilli Mucit Eşleştirme Çarpanı Migration'ı
-- ============================================================================
-- Bu dosyayı Supabase Dashboard > SQL Editor'de ELLE çalıştırın.
-- Amaç: Bir geliştiricinin doğrulanmış (tescilli) bir patenti varsa,
-- hibrit eşleştirme skoruna bir çarpan uygulanabilmesi için `profiles`
-- tablosuna bir bayrak (flag) kolonu eklemek (bkz. matchmaking_engine.py
-- içindeki PATENT_CARPAN sabiti ve hibrit_eslestirme_yap fonksiyonu).
-- ============================================================================

-- Yeni (opsiyonel) kolon — varsayılan false, mevcut kayıtları etkilemez,
-- geriye dönük uyumlu (backward-compatible).
alter table profiles add column if not exists has_verified_patent boolean default false;

-- Not: Bu kolonun `true` yapılması (yani "doğrulama") şu an bu migration'ın
-- kapsamında değil — kim doğrulayacak, hangi kanıt/süreçle doğrulanacak
-- ayrı bir iş kararı. Bu migration sadece alanı ekler; gerçek değerleri
-- siz (admin panel, manuel SQL update, ya da ayrı bir doğrulama akışıyla)
-- kendiniz set edeceksiniz, örnek:
--
--   update profiles set has_verified_patent = true where id = '<developer_id>';
