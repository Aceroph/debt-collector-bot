CREATE TABLE currencies (
	id SERIAL PRIMARY KEY,
	name text NOT NULL,
	icon text DEFAULT '',
	allowed_roles integer[]
);

CREATE TABLE banks (
	userId integer NOT NULL,
	guildId integer NOT NULL,
	currencyId integer NOT NULL,
	wallet money DEFAULT 20.00,
	bank money DEFAULT 0.00
);

CREATE TABLE transactions (
	userId integer PRIMARY KEY,
	guildId integer NOT NULL,
	currencyId integer NOT NULL,
	amount money NOT NULL,
	targetId integer DEFAULT 0,
	reason text NOT NULL,
	reversible boolean DEFAULT FALSE,
	timestamp timestamp DEFAULT NOW()
);

CREATE TABLE guildConfigs (
	guildId integer PRIMARY KEY,
	config json DEFAULT '{}'
);

