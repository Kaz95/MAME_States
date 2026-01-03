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

local_mame_paths = ['C:\\Users\\kazac\\Downloads\\wolfmame-0273',
                    'C:\\Users\\kazac\\Downloads\\groovymame_0273.221d_win-7-8-10',
                    'C:\\Users\\kazac\\Downloads\\mame']

test_pb_info = {'DonPachi': {'hs': 900,
                             'distance': 'Stage 6',
                             'splits': [[0, 1, 110], [1, 2, 200], [2, 3, 340], [3, 4, 420], [4, 5, 670], [5, 6, 900]]},

                'Galaga': {'hs': 2000,
                           'distance': 'Stage 3',
                           'splits': [[0, 1, 550], [1, 2, 1620], [2, 3, 2000]]},

                'Libble Rabble': {'hs': 50069,
                                  'distance': 'Stage 5',
                                  'splits': [[0, 1, 10000], [1, 2, 15069], [2, 3, 25069], [3, 4, 38069],
                                             [4, 5, 50069]]}}


def save_to_json(pb_info):
    """Save the 'in-memory' copy of the personal best database to JSON."""
    with open('game_db.json', 'w') as json_db:
        json.dump(pb_info, json_db, indent=4)


def get_roms_from_paths(mame_paths: list[str]) -> set[str]:
    """Create a unique set of roms available in the given MAME folders."""
    roms = set()
    for path in mame_paths:
        with open('temp_rom_list.txt', 'w+') as rom_list:
            subprocess.run([path + '\\mame.exe', '-ll'], stdout=rom_list)
            rom_list.seek(0)
            next(rom_list)
            for line in rom_list:
                roms.add(line)
        os.remove('temp_rom_list.txt')
    return roms


def create_rom_list(roms: set[str]) -> None:
    """Create list of roms in a text file."""
    with open('logic/rom_list.txt', 'w') as rom_list:
        roms = list(roms)
        roms.sort()
        rom_list.writelines(roms)


def build_description_db(rom_list: str) -> dict[str, str]:
    """Create and return a dictionary containing save file names, for roms that have them.

    All resulting strings are stripped of white space and double quotes.
    """
    rom_db = {}
    with open(rom_list, 'r') as rom_list:
        for line in rom_list:
            description_start = line.index('"')
            description = line[description_start:]
            description = description.strip()
            description = description.strip('"')
            rom_name = line[:description_start]
            rom_name = rom_name.strip()
            rom_db[description] = rom_name
    return rom_db


def get_roms_with_saves(mame_path: str) -> list[str]:
    """Create and return a list of roms that have a save folder in the given MAME file path"""
    contents = os.listdir(mame_path + '\\sta')
    return contents


def get_all_roms_with_saves(mame_paths: list[str]) -> dict[str:dict[str:list[str]]]:
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


def get_save_names(games_with_saves: list[str], mame_folder: str) -> dict[str, list[str]]:
    """Return all save files, and their respective roms."""
    save_states = {}
    for game in games_with_saves:
        saves = os.listdir(mame_folder + "\\sta" + '\\' + game)

        for save in saves:
            save_index = saves.index(save)
            save, _ = os.path.splitext(save)
            saves[save_index] = save

        save_states[game] = saves
    return save_states


def rename_save_state_file(mame_folder: str, rom_folder: str, old_save_name: str, new_save_name: str) -> None:
    """Rename a MAME save file"""
    os.rename(mame_folder + "\\sta\\" + rom_folder + "\\" + old_save_name + '.sta',
              mame_folder + "\\sta\\" + rom_folder + "\\" + new_save_name + '.sta')

# if __name__ == '__main__':
#     roms = get_roms_from_paths(mame_paths)
#     new_create_rom_list(roms)
#     description_db = build_description_db('rom_list.txt')
#     # all_states = get_all_roms_with_saves(mame_paths)
#     # pprint.pprint(all_states)
#     print(get_real_name(description_db, 'ddp2100k'))
