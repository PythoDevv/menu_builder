-- Taklif (referal) tizimi.
-- menu_items.required_referrals — tugmani ochish uchun kerakli taklif soni (0 -> shartsiz).
-- users.referred_by — foydalanuvchini kim taklif qilgan (taklif qilganning tg_id si).

ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS required_referrals INTEGER NOT NULL DEFAULT 0;

ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT;

CREATE INDEX IF NOT EXISTS ix_users_referred_by ON users (referred_by);
