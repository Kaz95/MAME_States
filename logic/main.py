"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.

TODO:
    * pass in filepaths as args to avoid absolute paths
    * Consider renaming functions to improve human readability.
"""
import pprint
import subprocess
import os
import json
from pathlib import Path

json_db = Path('game_db.json')
rom_db = Path('logic/rom_list.txt')

local_mame_paths = [Path(r'C:\Users\kazac\Downloads\wolfmame-0273'),
                    Path(r'C:\Users\kazac\Downloads\groovymame_0273.221d_win-7-8-10')]

test_pb_info = {'DonPachi': {'hs': 900,
                             'distance': 'Stage 6',
                             'splits': [[0, 'Stage-1', 110], [1, 'Stage-2', 200], [2, 'Stage-3', 340],
                                        [3, 'Stage-4', 420], [4, 'Stage-5', 670], [5, 'Stage-6', 900]]},

                'Galaga': {'hs': 2000,
                           'distance': 'Stage 3',
                           'splits': [[0, 'Stage-1', 550], [1, 'Stage-2', 1620], [2, 'Stage-3', 2000]]},

                'Libble Rabble': {'hs': 50069,
                                  'distance': 'Stage 5',
                                  'splits': [[0, 'Stage-1', 10000], [1, 'Stage-2', 15069], [2, 'Stage-3', 25069],
                                             [3, 'Stage-4', 38069],[4, 'Stage-5', 50069]]}}


def save_to_json(pb_info: dict[str, dict]) -> None:
    """Save the 'in-memory' copy of the personal best database to JSON."""
    with open(json_db, 'w') as db:
        json.dump(pb_info, db, indent=4)


def generate_rom_list(mame_path: Path) -> None:
    with open(rom_db, 'w') as rom_list:
        subprocess.run([mame_path / 'mame.exe', '-ll'], stdout=rom_list)


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

# if __name__ == '__main__':
#     mame_path = r'C:\Users\kazac\Downloads\mame'
#     generate_rom_list(mame_path)
#     roms = get_roms_from_paths(mame_paths)
#     new_create_rom_list(roms)
#     description_db = build_description_db('rom_list.txt')
#     # all_states = get_all_roms_with_saves(mame_paths)
#     # pprint.pprint(all_states)
#     print(get_real_name(description_db, 'ddp2100k'))
