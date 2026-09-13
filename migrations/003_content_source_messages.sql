ALTER TABLE contents
    ADD COLUMN IF NOT EXISTS source_chat_id BIGINT;

ALTER TABLE contents
    ADD COLUMN IF NOT EXISTS source_message_id INTEGER;
