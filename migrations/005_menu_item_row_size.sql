-- Har bir menyu tugmasi uchun qatordagi tugmalar soni.
-- DEFAULT 1 mavjud (eski) tugmalarni ham 1 talik qilib belgilaydi.

ALTER TABLE menu_items
ADD COLUMN IF NOT EXISTS row_size INTEGER NOT NULL DEFAULT 1
CONSTRAINT ck_menu_items_row_size CHECK (row_size BETWEEN 1 AND 4);
