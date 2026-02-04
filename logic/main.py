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

PersonalBestDataBase = dict[str, dict[str, any]]

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

def load_path_from_db(cursor: sqlite3.Cursor):
    sql_query = """SELECT * FROM paths"""
    cursor.execute(sql_query)
    raw_results = cursor.fetchall()
    paths = []
    for entry in raw_results:
        path = Path(entry[1])
        paths.append(path)
    return paths

def save_paths_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, paths: list[Path]):
    sql_statement = """INSERT OR IGNORE INTO paths VALUES (?, ?, ?, ?, ?);"""
    rows = []
    for path in paths:
        row = (None, str(path), path.name, None, None)
        rows.append(row)

    cursor.executemany(sql_statement, rows)
    connection.commit()


def id_from_name(name_, cursor_):
    sql = "SELECT id FROM roms WHERE description = ?"
    cursor_.execute(sql, (name_,))
    romid = cursor_.fetchall()
    romid = romid[0][0]
    return romid

def collate_pb_rows(cursor_, pb_info):
        rows = []
        for key in pb_info:
            pb_dict = pb_info[key]
            rom_id = id_from_name(key, cursor_)
            highscore = pb_dict['hs']
            distance = pb_dict['distance']
            row = (None, highscore, distance, rom_id)
            rows.append(row)
        return rows

def delete_split(connection, cursor_, name_, label):
    delete_row = "DELETE FROM splits WHERE rom_id = ? AND label = ?"
    rom_id = id_from_name(name_, cursor_)
    cursor_.execute(delete_row, (rom_id, label))
    connection.commit()

def get_split_pk(cursor_, name_, label):
    id_query = "SELECT id FROM splits WHERE rom_id = ? AND label = ?"
    rom_id = id_from_name(name_, cursor_)
    cursor_.execute(id_query, (rom_id, label))
    results = cursor_.fetchall()
    return results

def get_splits(cursor_, pb_info):
    splits = []
    for pb in pb_info:
        pb_dict = pb_info[pb]
        split = pb_dict['splits']
        for item in split:
            split_pk = get_split_pk(cursor_, pb, item[0])
            if split_pk:
                split_pk = split_pk[0][0]
            else:
                split_pk = None
            row = (split_pk, item[0], item[1], split.index(item), id_from_name(pb, cursor_))
            splits.append(row)
    return splits

def save_pb_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, pb_info: PersonalBestDataBase):
    pb_insert = "INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = excluded.highscore, distance = excluded.distance"
    splits_insert = "INSERT INTO splits VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET label = excluded.label, score = excluded.score, 'index' = excluded.'index'"

    pb_rows = collate_pb_rows(cursor, pb_info)
    splits = get_splits(cursor, pb_info)

    cursor.executemany(pb_insert, pb_rows)
    cursor.executemany(splits_insert, splits)

    connection.commit()


def new_build_descriptioin_db(cursor: sqlite3.Cursor):
    sql = """SELECT name, description FROM roms;"""
    cursor.execute(sql)
    results = cursor.fetchall()
    description_db = {}
    for item in results:
        description_db[item[1]] = item[0]

    return description_db


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

def load_personal_bests_from_database(cursor: sqlite3.Cursor):
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
