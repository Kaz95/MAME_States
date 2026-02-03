"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.

TODO:
    * Consider renaming functions to improve human readability.
"""
import pprint
import sqlite3
import subprocess
import os
import json

from pathlib import Path

paths_db = Path('paths.json')
pb_db = Path('game_db.json')
rom_db = Path('logic/rom_list.txt')

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

# TODO Deprecated
def load_paths_from_json(paths_database) -> list[Path]:
    """Load JSON file containing raw MAME paths and return them as a list of Path objects."""
    with open(paths_database, 'r') as db:
        formatted_paths = []
        raw_paths = json.load(db)
        for path in raw_paths:
            formatted_paths.append(Path(path))

        return formatted_paths


# TODO Deprecated
def get_raw_paths(formatted_paths: list[Path]) -> list[str]:
    """Convert a list of Path objects into their string representations. Return them as a new list."""
    raw_paths = []
    for path in formatted_paths:
        path = str(path)
        raw_paths.append(path)

    return raw_paths

def save_paths_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, paths: list[Path]):
    sql_statement = """INSERT OR IGNORE INTO paths VALUES (?, ?, ?, ?, ?);"""
    rows = []
    for path in paths:
        row = (None, str(path), path.name, None, None)
        rows.append(row)

    cursor.executemany(sql_statement, rows)
    connection.commit()


# TODO Deprecated
def save_raw_paths_to_json(paths: list[str], paths_database) -> None:
    """Save raw MAME paths to JSON."""
    with open(paths_database, 'w') as db:
        json.dump(paths, db, indent=4)


def save_pb_to_json(pb_info: dict[str, dict], pb_database) -> None:
    """Save the 'in-memory' copy of the personal best database to JSON."""
    with open(pb_database, 'w') as db:
        json.dump(pb_info, db, indent=4)


def generate_rom_list(mame_path: Path, rom_database) -> None:
    """Generate a full list of rom names and save to a text file: 'romlist.txt'."""
    with open(rom_database, 'w') as rom_list:
        subprocess.run([mame_path / 'mame.exe', '-ll'], stdout=rom_list)

def new_build_descriptioin_db(cursor: sqlite3.Cursor):
    sql = """SELECT name, description FROM roms;"""
    cursor.execute(sql)
    results = cursor.fetchall()
    description_db = {}
    for item in results:
        description_db[item[1]] = item[0]

    return description_db

def build_description_db(rom_list: Path) -> dict[str, str]:
    """Create and return a dictionary containing long form names as keys, and rom names as values.

    All resulting strings are stripped of white space and double quotes.
    """
    description_db = {}
    with open(rom_list, 'r') as rom_list:
        next(rom_list)
        for line in rom_list:
            description_start = line.index('"')
            description = line[description_start:]
            description = description.strip()
            description = description.strip('"')
            rom_name = line[:description_start]
            rom_name = rom_name.strip()
            description_db[description] = rom_name
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


def load_game_info(pb_database: Path) -> PersonalBestDataBase:
    """Load JSON file containing personal best information. Return the loaded information."""
    with open(pb_database, 'r') as game_info:
        game_dict = json.load(game_info)
        return game_dict

if __name__ == '__main__':
    mame_path = Path("C:\\Users\\kazac\\Downloads\\mame")
    subprocess.run([mame_path / 'mame.exe', 'ddp2100k'])