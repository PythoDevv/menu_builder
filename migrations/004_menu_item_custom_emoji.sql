-- Foydalanuvchi menyusidagi har bir reply tugma uchun Premium custom emoji.
-- Emoji tugma matnidan alohida icon_custom_emoji_id sifatida yuboriladi.

ALTER TABLE menu_items
ADD COLUMN IF NOT EXISTS icon_custom_emoji_id VARCHAR(255);
