-- Foydalanuvchi menyusidagi reply tugma rangi.
-- NULL -> Telegramning oddiy (default) ko'rinishi.

ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS button_style VARCHAR(16);
