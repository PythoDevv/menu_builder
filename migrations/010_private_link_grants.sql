-- Yopiq kanal linki: taklif sharti bajarilganda berilgan shaxsiy havolalar.
-- Bir odamga bitta kanal uchun faqat bitta havola beriladi.

CREATE TABLE IF NOT EXISTS private_link_grants (
    id SERIAL PRIMARY KEY,
    user_tg_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    invite_link VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_private_link_grant UNIQUE (user_tg_id, chat_id)
);

CREATE INDEX IF NOT EXISTS ix_private_link_grants_user_tg_id
    ON private_link_grants (user_tg_id);
