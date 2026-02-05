"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.

TODO:
    * Consider renaming functions to improve human readability.
"""
import os
import sqlite3
from pathlib import Path

raw_mame_paths = [r'C:\Users\kazac\Downloads\wolfmame-0273',
                  r'C:\Users\kazac\Downloads\groovymame_0273.221d_win-7-8-10']

PersonalBestDataBase = dict[str, dict[str, int | str | list]]
"""In-memory representation of the 'personal_bests' table of the database."""


test_pb_info = {'DonPachi': {'hs': 900,
                             'distance': 'Stage 6',
                             'splits': [['Stage-1', 110], ['Stage-2', 200], ['Stage-3', 340],
                                        ['Stage-4', 420], ['Stage-5', 670], ['Stage-6', 900]]},

                'Galaga': {'hs': 2000,
                           'distance': 'Stage 3',
                           'splits': [['Stage-1', 550], ['Stage-2', 1620], ['Stage-3', 2000]]},

                'Libble Rabble': {'hs': 50069,
                                  'distance': 'Stage 5',
                                  'splits': [['Stage-1', 10000], ['Stage-2', 15069], ['Stage-3', 25069],
                                             ['Stage-4', 38069], ['Stage-5', 50069]]}}


def load_path_from_db(cursor: sqlite3.Cursor) -> list[Path]:
    """Load paths as strings from database. Convert to Path objects before returning them."""
    sql_query = """SELECT * FROM paths"""
    cursor.execute(sql_query)
    raw_results = cursor.fetchall()
    paths = []
    for entry in raw_results:
        path = Path(entry[1])
        paths.append(path)
    return paths


def save_paths_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, paths: list[Path]) -> None:
    """Format list of paths as rows. Insert them into database. """
    sql_statement = """INSERT OR IGNORE INTO paths VALUES (?, ?, ?, ?, ?);"""
    rows = []
    for path in paths:
        row = (None, str(path), path.name, None, None)
        rows.append(row)

    cursor.executemany(sql_statement, rows)
    connection.commit()


def id_from_description(name: str, cursor: sqlite3.Cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom description, from the database."""
    sql_statement = "SELECT id FROM roms WHERE description = ?"
    cursor.execute(sql_statement, (name,))
    rom_id = cursor.fetchall()
    rom_id = rom_id[0][0]
    return rom_id


def collate_pb_rows(cursor: sqlite3.Cursor, pb_info: PersonalBestDataBase) -> list[tuple]:
    """Serialize personal best highscore and distance information into rows for database insertion."""
    rows = []
    for key in pb_info:
        pb_dict = pb_info[key]
        rom_id = id_from_description(key, cursor)
        highscore = pb_dict['hs']
        distance = pb_dict['distance']
        row = (None, highscore, distance, rom_id)
        rows.append(row)
    return rows


def delete_split(connection: sqlite3.Connection, cursor: sqlite3.Cursor, rom_description: str, split_label: str) -> None:
    """Delete a split from the database. Rom id and split label text are used as unique identifier."""
    sql_statement = "DELETE FROM splits WHERE rom_id = ? AND label = ?"
    rom_id = id_from_description(rom_description, cursor)
    cursor.execute(sql_statement, (rom_id, split_label))
    connection.commit()


def get_split_pk(cursor:sqlite3.Cursor, rom_description: str, split_label: str) -> list[tuple]:
    """Retrieve a primary key from database. Rom id and split label are used as unique identifier."""
    sql_statement = "SELECT id FROM splits WHERE rom_id = ? AND label = ?"
    rom_id = id_from_description(rom_description, cursor)
    cursor.execute(sql_statement, (rom_id, split_label))
    results = cursor.fetchall()
    return results


def collate_splits(cursor: sqlite3.Cursor, pb_info: PersonalBestDataBase) -> list[tuple]:
    """Serialize splits information into rows for database insertion."""
    splits = []
    for pb in pb_info:
        pb_dict = pb_info[pb]
        split = pb_dict['splits']
        for item in split:
            # Results are returned raw and may be empty.
            split_primary_key = get_split_pk(cursor, pb, item[0])
            if split_primary_key:
                split_primary_key = split_primary_key[0][0]
            else:
                split_primary_key = None
            row = (split_primary_key, item[0], item[1], split.index(item), id_from_description(pb, cursor))
            splits.append(row)
    return splits


def save_pb_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, pb_info: PersonalBestDataBase) -> None:
    """Update database with provided personal best and split information.

    Rows are added if they do not exist, and updated otherwise.
    """
    pb_insert = ("INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = "
                 "excluded.highscore, distance = excluded.distance")
    splits_insert = ("INSERT INTO splits VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET label = excluded.label, "
                     "score = excluded.score, 'index' = excluded.'index'")

    pb_rows = collate_pb_rows(cursor, pb_info)
    splits = collate_splits(cursor, pb_info)

    cursor.executemany(pb_insert, pb_rows)
    cursor.executemany(splits_insert, splits)

    connection.commit()


def get_descriptions_and_names(cursor: sqlite3.Cursor) -> dict[str:str]:
    """Construct {rom_description:rom_name} dictionary.

    This dictionary is used as a quick in-memory reference that binds a roms description, to its name.
    The alternative would be querying them as needed.
    """
    sql_statement = """SELECT name, description FROM roms;"""
    cursor.execute(sql_statement)
    results = cursor.fetchall()
    descriptions_and_names = {}
    for item in results:
        descriptions_and_names[item[1]] = item[0]

    return descriptions_and_names


def get_roms_with_saves(mame_path: Path) -> list[str]:
    """Create and return a list of roms that have a save folder in the given MAME file path"""
    contents = os.listdir(mame_path / 'sta')
    return contents


def get_all_roms_with_saves(mame_paths: list[Path]) -> dict[str:dict[str:list[str]]]:
    """Retrieve all save state data."""
    all_save_states = {}
    for path in mame_paths:
        games_with_saves = get_roms_with_saves(path)
        save_states = get_save_names(games_with_saves, path)
        all_save_states[path] = save_states
    return all_save_states


def get_real_name(description_db: dict[str, str], rom_name: str) -> str:
    """Return the full name of a given rom"""
    for item in description_db.items():
        if item[1] == rom_name:
            real_name = item[0]
            return real_name


def get_save_names(games_with_saves: list[str], mame_folder: Path) -> dict[str, list[str]]:
    """Return all save files, and their respective roms."""
    save_states = {}
    for game in games_with_saves:
        saves = os.listdir(mame_folder / "sta" / game)

        for save in saves:
            save_index = saves.index(save)
            save, _ = os.path.splitext(save)
            saves[save_index] = save

        save_states[game] = saves
    return save_states


def rename_save_state_file(mame_folder: Path, rom_folder: str, old_save_name: str, new_save_name: str) -> None:
    """Rename a MAME save file"""
    os.rename(mame_folder / "sta" / rom_folder / (old_save_name + '.sta'),
              mame_folder / "sta" / rom_folder / (new_save_name + '.sta'))


def load_personal_bests_from_database(cursor: sqlite3.Cursor) -> PersonalBestDataBase:
    """Load and format all personal best information from the database."""
    pb_info: PersonalBestDataBase = {}

    pb_query = """SELECT roms.description, personal_bests.highscore, personal_bests.distance 
    FROM 'roms' JOIN 'personal_bests' ON roms.id = personal_bests.rom_id"""

    splits_query = """SELECT splits.label, splits.score, splits.'index', roms.description 
        FROM 'splits' JOIN 'roms' ON splits.rom_id = roms.id 
        ORDER BY roms.description, splits.'index'"""

    cursor.execute(pb_query)
    personal_bests = cursor.fetchall()

    for pb in personal_bests:
        pb_info[pb[0]] = {'hs': pb[1], 'distance': pb[2], 'splits': []}

    cursor.execute(splits_query)
    splits = cursor.fetchall()
    for split in splits:
        pb_info[split[3]]['splits'].append([split[0], split[1]])

    return pb_info
