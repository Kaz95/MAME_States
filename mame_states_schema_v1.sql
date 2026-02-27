BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "paths" (
	"id"	INTEGER,
	"path"	TEXT CONSTRAINT "unique_path" UNIQUE,
	"name"	TEXT,
	"version"	TEXT,
	"last_updated"	TEXT,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "personal_bests" (
	"id"	INTEGER,
	"highscore"	INTEGER NOT NULL,
	"other_fields"	TEXT,
	"rom_id"	INTEGER UNIQUE,
	PRIMARY KEY("id"),
	FOREIGN KEY("rom_id") REFERENCES "roms"("id")
);
CREATE TABLE IF NOT EXISTS "playlists" (
	"id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL UNIQUE,
	"sort_order"	INTEGER NOT NULL UNIQUE,
	"date_created"	TEXT NOT NULL,
	"last_updated"	TEXT,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "roms" (
	"id"	INTEGER,
	"name"	TEXT,
	"description"	TEXT,
	"manufacturer"	TEXT,
	"year"	INTEGER,
	"parent"	TEXT,
	"hres"	INTEGER,
	"vres"	INTEGER,
	"rotate"	INTEGER,
	"refresh"	REAL,
	"video"	TEXT,
	"sound"	TEXT,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "roms_playlists" (
	"rom_id"	INTEGER NOT NULL,
	"playlist_id"	INTEGER NOT NULL,
	"sort_order"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("rom_id","playlist_id"),
	FOREIGN KEY("playlist_id") REFERENCES "playlists"("id"),
	FOREIGN KEY("rom_id") REFERENCES "roms"("id")
);
CREATE TABLE IF NOT EXISTS "splits" (
	"id"	INTEGER,
	"label"	TEXT,
	"score"	INTEGER,
	"index"	INTEGER,
	"rom_id"	INTEGER,
	PRIMARY KEY("id"),
	FOREIGN KEY("rom_id") REFERENCES "roms"("id")
);
COMMIT;
