-- Adminlarni paneldan boshqarish uchun jadval.
-- .env dagi ADMINS bu yerga yozilmaydi, ular baribir admin bo'lib qolaveradi.

CREATE TABLE IF NOT EXISTS admins (
    id          SERIAL PRIMARY KEY,
    tg_id       BIGINT NOT NULL,
    full_name   VARCHAR(255) NOT NULL DEFAULT '',
    username    VARCHAR(64),
    added_by    BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_admins_tg_id ON admins (tg_id);
