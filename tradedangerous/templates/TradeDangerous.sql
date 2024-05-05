-- Definitions for all of the tables used in the SQLite
-- cache database.
--
-- Source data for TradeDangerous is stored in various
-- ".csv" files which provide relatively constant data
-- such as star names, the list of known tradeable items,
-- etc.
--
-- Per-station price data is sourced from ".prices" files
-- which are designed to be human readable text that
-- closely aproximates the in-game UI.
--
-- When the .SQL file or the .CSV files change, TD will
-- destroy and rebuild the cache next time it is run.
--
-- When the .prices file is changed, only the price data
-- is reset.
--
-- You can edit this file, if you really need to, if you know
-- what you are doing. Or you can use the 'sqlite3' command
-- to edit the .db database and then use the '.dump' command
-- to regenerate this file, except then you'll lose this nice
-- header and I might have to wag my finger at you.
--
-- -Oliver

PRAGMA foreign_keys=ON;
PRAGMA synchronous=OFF;
PRAGMA temp_store=MEMORY;
PRAGMA journal_mode=wal;
PRAGMA auto_vacuum=INCREMENTAL;

BEGIN TRANSACTION;


-- Top-level tables (no references to other tables)

CREATE TABLE Added
(
  added_id      INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
  name          VARCHAR(40) COLLATE nocase NOT NULL UNIQUE
);


CREATE TABLE Category
(
  category_id   INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
  name          VARCHAR(40) NOT NULL UNIQUE COLLATE nocase
);


CREATE TABLE Ship
(
  ship_id       INTEGER PRIMARY KEY NOT NULL UNIQUE,
  name          VARCHAR(40) NOT NULL UNIQUE COLLATE nocase,
  cost          INTEGER NOT NULL
) WITHOUT ROWID;


CREATE TABLE Upgrade
(
  upgrade_id    INTEGER PRIMARY KEY NOT NULL UNIQUE,
  name          VARCHAR(40) NOT NULL UNIQUE COLLATE nocase,
  class         NUMBER NOT NULL,
  rating        CHAR(1) NOT NULL,
  ship          VARCHAR(40) NOT NULL COLLATE nocase
) WITHOUT ROWID;


-- Second tier tables (references 1+ top-tier, and has references from other tables)

CREATE TABLE Item
(
  item_id       INTEGER PRIMARY KEY NOT NULL UNIQUE,
  name          VARCHAR(40) NOT NULL UNIQUE COLLATE nocase,
  category_id   INTEGER NOT NULL,
  ui_order      INTEGER NOT NULL,
  avg_price     INTEGER,
  fdev_id       INTEGER,

  CONSTRAINT fk_Item_category_id_Category FOREIGN KEY (category_id) REFERENCES Category(category_id) ON DELETE CASCADE
) WITHOUT ROWID;
DROP INDEX IF EXISTS idx_item_by_fdev_id;
CREATE INDEX ix_Item_fdev_id ON Item (fdev_id);


CREATE TABLE System
(
  system_id     INTEGER PRIMARY KEY NOT NULL UNIQUE,
  name          VARCHAR(40) NOT NULL UNIQUE COLLATE nocase,
  pos_x         DOUBLE NOT NULL,
  pos_y         DOUBLE NOT NULL,
  pos_z         DOUBLE NOT NULL,
  added_id      INTEGER,
  modified      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,

  CONSTRAINT fk_System_added_id_Added FOREIGN KEY (added_id) REFERENCES Added(added_id) ON DELETE CASCADE
) WITHOUT ROWID;
DROP INDEX IF EXISTS idx_system_by_pos;
CREATE INDEX ix_System_pos_x_pos_y_pos_z ON System (pos_x, pos_y, pos_z);


CREATE TABLE Station
(
  station_id    INTEGER PRIMARY KEY NOT NULL UNIQUE,
  name          VARCHAR(40) NOT NULL COLLATE nocase,
  system_id     INTEGER NOT NULL,
  ls_from_star  INTEGER NOT NULL
                  CHECK (ls_from_star >= 0),
  blackmarket   CHAR(1) NOT NULL
                  CHECK (blackmarket IN ('?', 'Y', 'N')),
  max_pad_size  CHAR(1) NOT NULL
                  CHECK (max_pad_size IN ('?', 'S', 'M', 'L')),
  market        CHAR(1) NOT NULL
                  CHECK (market IN ('?', 'Y', 'N')),
  shipyard      CHAR(1) NOT NULL
                  CHECK (shipyard IN ('?', 'Y', 'N')),
  modified      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  outfitting    CHAR(1) NOT NULL
                  CHECK (outfitting IN ('?', 'Y', 'N')),
  rearm         CHAR(1) NOT NULL
                  CHECK (rearm IN ('?', 'Y', 'N')),
  refuel        CHAR(1) NOT NULL
                  CHECK (refuel IN ('?', 'Y', 'N')),
  repair        CHAR(1) NOT NULL
                  CHECK (repair     IN ('?', 'Y', 'N')),
  planetary     CHAR(1) NOT NULL
                  CHECK (planetary  IN ('?', 'Y', 'N')),
  type_id       INTEGER NOT NULL,

  CONSTRAINT fk_Station_system_id_System FOREIGN KEY (system_id) REFERENCES System(system_id) ON DELETE CASCADE
) WITHOUT ROWID;
DROP INDEX IF EXISTS idx_station_by_system;
CREATE INDEX ix_Station_system_id ON Station (system_id);
DROP INDEX IF EXISTS idx_station_by_name;
CREATE INDEX ix_Station_name ON Station (name);


-- Leaf tier tables: Not referenced, and reference 1+ top-tier table


CREATE TABLE ShipVendor
(
  ship_id       INTEGER NOT NULL,
  station_id    INTEGER NOT NULL,
  modified      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,

  CONSTRAINT pk_ShipVendor PRIMARY KEY (ship_id, station_id),

  CONSTRAINT fk_ShipVendor_ship_id_Ship       FOREIGN KEY (ship_id)    REFERENCES Ship(ship_id)       ON DELETE CASCADE,
  CONSTRAINT fk_ShipVendor_station_id_Station FOREIGN KEY (station_id) REFERENCES Station(station_id) ON DELETE CASCADE
) WITHOUT ROWID;
CREATE INDEX ix_ShipVendor_station_id ON ShipVendor (station_id);


CREATE TABLE UpgradeVendor
(
  upgrade_id    INTEGER NOT NULL,
  station_id    INTEGER NOT NULL,
  modified      DATETIME NOT NULL,

  CONSTRAINT pk_UpgradeVendor PRIMARY KEY (upgrade_id, station_id),

  CONSTRAINT fk_UpgradeVendor_upgrade_id_Upgrade FOREIGN KEY (upgrade_id) REFERENCES Upgrade(upgrade_id) ON DELETE CASCADE,
  CONSTRAINT fk_UpgradeVendor_station_id_Station FOREIGN KEY (station_id) REFERENCES Station(station_id) ON DELETE CASCADE
) WITHOUT ROWID;
DROP INDEX IF EXISTS idx_vendor_by_station_id;
CREATE INDEX ix_UpgradeVendor_station_id ON UpgradeVendor (station_id);


CREATE TABLE RareItem
(
  rare_id       INTEGER PRIMARY KEY NOT NULL UNIQUE,
  station_id    INTEGER NOT NULL,
  category_id   INTEGER NOT NULL,
  name          VARCHAR(40) NOT NULL UNIQUE COLLATE nocase,
  cost          INTEGER,
  max_allocation  INTEGER,
  illegal       CHAR(1) NOT NULL
                  CHECK (illegal IN ('?', 'Y', 'N')),
  suppressed    CHAR(1) NOT NULL
                  CHECK (suppressed IN ('?', 'Y', 'N')),

  CONSTRAINT fk_RareItem_station_id_Station   FOREIGN KEY (station_id)  REFERENCES Station(station_id)   ON DELETE CASCADE,
  CONSTRAINT fk_RareItem_category_id_Category FOREIGN KEY (category_id) REFERENCES Category(category_id) ON DELETE CASCADE
) WITHOUT ROWID;
CREATE INDEX ix_RareItem_station_id ON RareItem (station_id);
CREATE INDEX ix_RareItem_category_id ON RareItem (category_id);


CREATE TABLE StationItem
(
  station_id    INTEGER NOT NULL,
  item_id       INTEGER NOT NULL,
  demand_price  INT NOT NULL,
  demand_units  INT NOT NULL,
  demand_level  INT NOT NULL,
  supply_price  INT NOT NULL,
  supply_units  INT NOT NULL,
  supply_level  INT NOT NULL,
  modified      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  from_live     INTEGER DEFAULT 0 NOT NULL,

  CONSTRAINT pk_StationItem PRIMARY KEY  (station_id, item_id),

  CONSTRAINT fk_StationItem_station_id_Station FOREIGN KEY (station_id) REFERENCES Station(station_id) ON DELETE CASCADE,
  CONSTRAINT fk_StationItem_item_id_Item       FOREIGN KEY (item_id)    REFERENCES Item(item_id)       ON DELETE CASCADE
) WITHOUT ROWID;
DROP INDEX IF EXISTS si_mod_stn_itm;
CREATE INDEX ix_StationItem_modified_station_id ON StationItem(modified, station_id);
DROP INDEX IF EXISTS si_itm_dmpdr;
CREATE INDEX ix_StationItem_item_id_demand_price ON StationItem(item_id, station_id, demand_price) WHERE demand_price > 0;
DROP INDEX IF EXISTS si_itm_suppr;
CREATE INDEX ix_StationItem_item_id_supply_price ON StationItem(item_id, station_id, supply_price) WHERE supply_price > 0;


-- Not used yet
-- These should replace the StationItems table.
CREATE TABLE IF NOT EXISTS StationDemand
(
    station_id      INTEGER NOT NULL,
    item_id         INTEGER NOT NULL,
    price           INTEGER NOT NULL,
    units           INTEGER NOT NULL,
    level           INTEGER NOT NULL,
    modified        INTEGER NOT NULL,
    from_live       INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT pk_StationDemand PRIMARY KEY (station_id, item_id),
    CONSTRAINT fk_StationDemand_station_id_Station FOREIGN KEY (station_id) REFERENCES Station (station_id) ON DELETE CASCADE,
    CONSTRAINT fk_StationDemand_item_id_Item       FOREIGN KEY (item_id)    REFERENCES Item    (item_id)    ON DELETE CASCADE
) WITHOUT ROWID;
DELETE FROM StationDemand;
CREATE INDEX idx_StationDemand_item ON StationDemand (item_id);

CREATE TABLE IF NOT EXISTS StationSupply
(
    station_id      INTEGER NOT NULL,
    item_id         INTEGER NOT NULL,
    price           INTEGER NOT NULL,
    units           INTEGER NOT NULL,
    level           INTEGER NOT NULL,
    modified        INTEGER NOT NULL,
    from_live       INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT pk_StationSupply PRIMARY KEY (station_id, item_id),
    CONSTRAINT fk_StationSupply_station_id_Station FOREIGN KEY (station_id) REFERENCES Station (station_id) ON DELETE CASCADE,
    CONSTRAINT fk_StationSupply_item_id_Item       FOREIGN KEY (item_id)    REFERENCES Item    (item_id)    ON DELETE CASCADE
) WITHOUT ROWID;
DELETE FROM StationSupply;
CREATE INDEX idx_StationSupply_item ON StationSupply (item_id);

CREATE VIEW StationBuying AS
SELECT  station_id,
        item_id,
        demand_price AS price,
        demand_units AS units,
        demand_level AS level,
        modified
  FROM  StationItem
 WHERE  demand_price > 0
;

CREATE VIEW StationSelling AS
SELECT  station_id,
        item_id,
        supply_price AS price,
        supply_units AS units,
        supply_level AS level,
        modified
  FROM  StationItem
 WHERE  supply_price > 0
;


--
-- The next two tables (FDevShipyard, FDevOutfitting) are
-- used to map the FDev API IDs to data ready for EDDN.
--
-- The column names are the same as the header line from
-- the EDCD/FDevIDs csv files, so we can just download the
-- files (shipyard.csv, outfitting.csv) and save them
-- as (FDevShipyard.csv, FDevOutfitting.csv) into the
-- data directory.
--
-- see https://github.com/EDCD/FDevIDs
--
-- The commodity.csv is not needed because TD and EDDN
-- are using the same names.
--
-- -Bernd

CREATE TABLE FDevShipyard
(
  id          INTEGER PRIMARY KEY NOT NULL UNIQUE,
  symbol      VARCHAR(40),
  name        VARCHAR(40) NOT NULL COLLATE nocase,
  entitlement VARCHAR(50)
) WITHOUT ROWID;


CREATE TABLE FDevOutfitting
(
   id         INTEGER PRIMARY KEY NOT NULL UNIQUE,
   symbol     VARCHAR(40),
   category   CHAR(10)
              CHECK (category IN ('hardpoint','internal','standard','utility')),
   name       VARCHAR(40) NOT NULL COLLATE nocase,
   mount      VARCHAR(10)
              CHECK (mount IN (NULL, 'Fixed','Gimballed','Turreted')),
   guidance   VARCHAR(10)
              CHECK (guidance IN (NULL, 'Dumbfire','Seeker','Swarm')),
   ship       VARCHAR(40) COLLATE nocase,
   class      VARCHAR(1) NOT NULL,
   rating     VARCHAR(1) NOT NULL,
   entitlement VARCHAR(50)
) WITHOUT ROWID;


PRAGMA user_version = 2;  -- Match to tradedb.py SCHEMA_VERSION


COMMIT;
