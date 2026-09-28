-- Har bir menyu tugmasining qatordagi ko'rinishini admin boshqaradi.
-- Mavjud va yangi tugmalar uchun standart qiymat: 2 tadan.

ALTER TABLE menu_items
ADD COLUMN IF NOT EXISTS buttons_per_row INTEGER NOT NULL DEFAULT 2;
