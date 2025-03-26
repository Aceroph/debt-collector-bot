CREATE TABLE currencies (
	id bigserial PRIMARY KEY,
	name text NOT NULL,
	owner bigint DEFAULT 0,
	icon text DEFAULT '',
	created_at timestamp DEFAULT NOW(),
	hidden boolean DEFAULT FALSE,
	allowed_roles integer[]
);

CREATE TABLE banks (
	userid bigint NOT NULL,
	currencyid integer NOT NULL,
	wallet money DEFAULT 20.00,
	bank money DEFAULT 0.00
);

CREATE TABLE transactions (
	userid bigint PRIMARY KEY,
	guildid bigint NOT NULL,
	currencyid integer NOT NULL,
	amount money NOT NULL,
	targetid bigint DEFAULT 0,
	reason text NOT NULL,
	reversible boolean DEFAULT FALSE,
	timestamp timestamp DEFAULT NOW()
);

CREATE TABLE guildconfigs (
	guildid bigint PRIMARY KEY,
	config json DEFAULT '{"currencies": []}'
);

