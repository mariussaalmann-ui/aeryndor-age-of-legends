-- ============================================================================
-- AERYNDOR: AGE OF LEGENDS - PostgreSQL Production Schema (Kap. 1, 9, 10, 11, 15)
-- Kompatibel mit PostgreSQL 15+ sowie der lokalen SQLite-Entwicklungsdatenbank
-- ============================================================================

CREATE TABLE IF NOT EXISTS players (
    player_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(48) NOT NULL UNIQUE,
    class_id VARCHAR(24) NOT NULL DEFAULT 'warrior',
    gender VARCHAR(12) NOT NULL DEFAULT 'male',
    level INT NOT NULL DEFAULT 1,
    exp BIGINT NOT NULL DEFAULT 0,
    hp INT NOT NULL DEFAULT 950,
    max_hp INT NOT NULL DEFAULT 950,
    mp INT NOT NULL DEFAULT 260,
    max_mp INT NOT NULL DEFAULT 260,
    vit INT NOT NULL DEFAULT 16,
    int_stat INT NOT NULL DEFAULT 4,
    str INT NOT NULL DEFAULT 18,
    dex INT NOT NULL DEFAULT 12,
    stat_points INT NOT NULL DEFAULT 0,
    skill_points INT NOT NULL DEFAULT 1,
    yang BIGINT NOT NULL DEFAULT 2500,
    shards INT NOT NULL DEFAULT 5,
    reputation INT NOT NULL DEFAULT 1250,
    map_id VARCHAR(32) NOT NULL DEFAULT 'morgenwacht',
    pos_x DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    pos_z DOUBLE PRECISION NOT NULL DEFAULT 58.0,
    rot_y DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    active_mount VARCHAR(48) DEFAULT NULL,
    active_pet VARCHAR(48) DEFAULT NULL,
    skills_json TEXT NOT NULL DEFAULT '{}',
    passives_json TEXT NOT NULL DEFAULT '{}',
    quests_json TEXT NOT NULL DEFAULT '{}',
    autofarm_json TEXT NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_items (
    item_uid VARCHAR(64) PRIMARY KEY,
    player_id VARCHAR(64) NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    template_id VARCHAR(64) NOT NULL,
    category INT NOT NULL DEFAULT 0, -- 0=Normal, 1=Uppitems, 2=Fertigkeiten, 3=Kostüme, 9=Lager
    slot_index INT NOT NULL DEFAULT 0,
    equipped_slot VARCHAR(32) DEFAULT NULL,
    plus_level INT NOT NULL DEFAULT 0,
    quantity INT NOT NULL DEFAULT 1,
    bonuses_json TEXT NOT NULL DEFAULT '[]',
    locked_bonus_idx INT DEFAULT -1,
    reserved_shop_id VARCHAR(64) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS offline_shops (
    shop_id VARCHAR(64) PRIMARY KEY,
    owner_id VARCHAR(64) NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    owner_name VARCHAR(48) NOT NULL,
    title VARCHAR(80) NOT NULL,
    map_id VARCHAR(32) NOT NULL DEFAULT 'morgenwacht',
    pos_x DOUBLE PRECISION NOT NULL,
    pos_z DOUBLE PRECISION NOT NULL,
    vault_yang BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS offline_shop_listings (
    listing_id VARCHAR(64) PRIMARY KEY,
    shop_id VARCHAR(64) NOT NULL REFERENCES offline_shops(shop_id) ON DELETE CASCADE,
    item_uid VARCHAR(64) NOT NULL UNIQUE REFERENCES inventory_items(item_uid) ON DELETE CASCADE,
    price_yang BIGINT NOT NULL CHECK (price_yang > 0),
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_sales_log (
    sale_id VARCHAR(64) PRIMARY KEY,
    shop_id VARCHAR(64) NOT NULL,
    seller_id VARCHAR(64) NOT NULL,
    buyer_id VARCHAR(64) NOT NULL,
    buyer_name VARCHAR(48) NOT NULL,
    template_id VARCHAR(64) NOT NULL,
    plus_level INT NOT NULL,
    quantity INT NOT NULL,
    price_yang BIGINT NOT NULL,
    sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
