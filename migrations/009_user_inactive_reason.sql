-- Foydalanuvchiga xabar nega yetib bormasligi: 'blocked' | 'deactivated' | 'not_started'.
-- 'not_started' — botga /start bosmagan (faqat yopiq kanalga zayafka tashlagan) odam;
-- ular statistikaga, Excelga va rassilkaga kirmaydi.

ALTER TABLE users ADD COLUMN IF NOT EXISTS inactive_reason VARCHAR(16);

-- Eski bazada sabab yozilmagan: hozirgi barcha nofaollar "bloklagan" deb boshlanadi.
UPDATE users SET inactive_reason = 'blocked'
WHERE is_active = false AND inactive_reason IS NULL;

-- Zayafka tufayli yozilib qolgan, rassilkada yetib bormagan odamlar.
-- Bunday odam bazaga zayafka bilan bir xil soniyada tushgan (middleware -> handler),
-- referal orqali kelmagan va raqam qoldirmagan bo'ladi.
-- Aniq natija uchun keyin: python -m scripts.recheck_users
UPDATE users u SET inactive_reason = 'not_started'
WHERE u.is_active = false
  AND u.referred_by IS NULL
  AND u.phone IS NULL
  AND EXISTS (
      SELECT 1 FROM join_requests j
      WHERE j.user_tg_id = u.tg_id
        AND j.created_at >= u.created_at
        AND j.created_at < u.created_at + INTERVAL '3 seconds'
  );
