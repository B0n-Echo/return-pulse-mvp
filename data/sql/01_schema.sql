-- ============================================================================
-- Dhaga & Co. Return Pulse: Postgres schema
-- Run this first, then 02_data.sql.
-- Re-running this file DROPS and recreates every table below.
-- ============================================================================

DROP VIEW  IF EXISTS returns_enriched;
DROP TABLE IF EXISTS corrections, classified_returns, weekly_issue_counts, settings,
                     eval_return_labels, reviews, returns, order_items, orders,
                     customers, products, vendors CASCADE;

-- ---------------------------------------------------------------------------
-- SOURCE TABLES (what Dhaga already has; shaped like Dhaga data)
-- ---------------------------------------------------------------------------

CREATE TABLE vendors (
    vendor_id            TEXT PRIMARY KEY,
    vendor_name          TEXT NOT NULL,
    vendor_city          TEXT,
    size_chart_version   TEXT,          -- inconsistent on purpose ("vendor-own", "unknown")
    lead_time_days_note  TEXT           -- free text, "held in people's heads"
);

CREATE TABLE products (
    sku           TEXT PRIMARY KEY,
    product_name  TEXT NOT NULL,
    department    TEXT NOT NULL,        -- Womenswear / Kidswear / Menswear
    subcategory   TEXT NOT NULL,
    vendor_id     TEXT REFERENCES vendors(vendor_id),
    colour_raw    TEXT,                 -- typed many different ways on purpose
    fabric_raw    TEXT,                 -- free text on purpose
    price_inr     INTEGER,
    size_scheme   TEXT,                 -- adult / kids
    launch_date   DATE
);

CREATE TABLE customers (
    customer_id    TEXT PRIMARY KEY,
    customer_name  TEXT,
    gender         TEXT,
    age            INTEGER,
    city           TEXT,
    state          TEXT,
    city_tier      INTEGER,
    pincode        TEXT,
    signup_date    DATE
);

CREATE TABLE orders (
    order_id         TEXT PRIMARY KEY,
    customer_id      TEXT REFERENCES customers(customer_id),
    order_date       DATE NOT NULL,
    payment_mode     TEXT NOT NULL,     -- COD / UPI / CARD / WALLET
    order_status     TEXT NOT NULL,     -- DELIVERED / RTO / CANCELLED / IN_TRANSIT
    delivered_date   DATE,
    courier          TEXT,
    ship_city        TEXT,
    ship_state       TEXT,
    ship_pincode     TEXT,
    city_tier        INTEGER,
    order_total_inr  INTEGER
);

CREATE TABLE order_items (
    order_item_id   TEXT PRIMARY KEY,
    order_id        TEXT REFERENCES orders(order_id),
    sku             TEXT REFERENCES products(sku),
    size            TEXT,
    quantity        INTEGER,
    unit_price_inr  INTEGER
);

CREATE TABLE returns (
    return_id        TEXT PRIMARY KEY,
    order_id         TEXT REFERENCES orders(order_id),
    order_item_id    TEXT REFERENCES order_items(order_item_id),
    sku              TEXT REFERENCES products(sku),
    return_date      DATE NOT NULL,
    raised_via       TEXT,              -- APP / WHATSAPP
    reason_dropdown  TEXT NOT NULL,     -- one of 6 reasons, or 'Other'
    other_text       TEXT,              -- free text, only when dropdown = 'Other'
    return_status    TEXT
);

CREATE TABLE reviews (
    review_id    TEXT PRIMARY KEY,
    sku          TEXT REFERENCES products(sku),
    customer_id  TEXT REFERENCES customers(customer_id),
    order_id     TEXT REFERENCES orders(order_id),
    rating       INTEGER CHECK (rating BETWEEN 1 AND 5),
    review_text  TEXT,
    review_date  DATE
);

-- ---------------------------------------------------------------------------
-- EVALUATION ONLY: the "right answer" for every return.
-- Real Dhaga data would NOT have this. Never feed it to the model.
-- Use it to measure your classifier's accuracy for the build note.
-- ---------------------------------------------------------------------------
CREATE TABLE eval_return_labels (
    return_id             TEXT PRIMARY KEY REFERENCES returns(return_id),
    true_issue            TEXT NOT NULL,
    true_secondary_issue  TEXT,
    is_mixed              BOOLEAN
);

-- ---------------------------------------------------------------------------
-- OUTPUT TABLES (what YOUR pipeline writes; empty at the start)
-- ---------------------------------------------------------------------------

CREATE TABLE classified_returns (
    return_id       TEXT PRIMARY KEY REFERENCES returns(return_id),
    issue_type      TEXT NOT NULL,      -- too_small, too_large, colour_mismatch, quality, damaged,
                                        -- wrong_item, changed_mind, delivery_late, unclear, failed
    confidence      NUMERIC(3,2),
    evidence_phrase TEXT,
    evidence_found  BOOLEAN,            -- quote found in the comment? NULL when no quote is expected
    source          TEXT NOT NULL,      -- dropdown / cheap_model / strong_model / gate
    model_name      TEXT,
    classified_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE weekly_issue_counts (
    week_start    DATE NOT NULL,
    issue_type    TEXT NOT NULL,
    vendor_id     TEXT,
    subcategory   TEXT,
    size          TEXT,
    ship_city     TEXT,
    return_count  INTEGER NOT NULL,
    PRIMARY KEY (week_start, issue_type, vendor_id, subcategory, size, ship_city)
);

CREATE TABLE corrections (
    id                SERIAL PRIMARY KEY,
    return_id         TEXT REFERENCES returns(return_id),
    model_issue_type  TEXT,
    is_correct        BOOLEAN NOT NULL,
    corrected_issue   TEXT,
    note              TEXT,
    corrected_by      TEXT DEFAULT 'neha',
    corrected_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
INSERT INTO settings (key, value) VALUES
    ('confidence_threshold', '0.75'),
    ('min_returns_per_hotspot', '20');

-- ---------------------------------------------------------------------------
-- HELPER VIEW: every return with its product, vendor, size and location.
-- This is pipeline step 1 ("Join") done in SQL.
-- ---------------------------------------------------------------------------
CREATE VIEW returns_enriched AS
SELECT r.return_id, r.return_date, date_trunc('week', r.return_date)::date AS week_start,
       r.raised_via, r.reason_dropdown, r.other_text, r.return_status,
       r.order_id, o.order_date, o.payment_mode, o.ship_city, o.ship_state, o.city_tier, o.courier,
       oi.size, oi.unit_price_inr,
       p.sku, p.product_name, p.department, p.subcategory, p.colour_raw, p.fabric_raw,
       v.vendor_id, v.vendor_name
FROM returns r
JOIN orders o       ON o.order_id = r.order_id
JOIN order_items oi ON oi.order_item_id = r.order_item_id
JOIN products p     ON p.sku = r.sku
JOIN vendors v      ON v.vendor_id = p.vendor_id;

CREATE INDEX idx_returns_date ON returns(return_date);
CREATE INDEX idx_returns_sku ON returns(sku);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_items_order ON order_items(order_id);
