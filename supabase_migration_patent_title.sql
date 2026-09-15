-- Patentin başlığını da saklayabilmek için (şu ana kadar sadece PDF içine
-- gömülüydü, ayrı bir "Patentler" bölümünde göstermek için DB'de lazım).
alter table profiles add column if not exists patent_title text;
