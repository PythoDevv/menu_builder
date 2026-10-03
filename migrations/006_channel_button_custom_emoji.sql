-- Majburiy obuna oynasidagi kanal inline tugmasi uchun premium emoji ikonka.

ALTER TABLE channels
ADD COLUMN IF NOT EXISTS icon_custom_emoji_id VARCHAR(255);
