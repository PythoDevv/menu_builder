-- Majburiy obuna postidagi kanalga bog'liq bo'lmagan URL tugmalar.

CREATE TABLE IF NOT EXISTS subscription_buttons (
    id SERIAL PRIMARY KEY,
    title VARCHAR(64) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
