"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.

TODO:
    * Consider renaming functions to improve human readability.
"""
import subprocess
import os


def create_rom_list(mame_path: str) -> None:
    """Create text file containing all roms derived from a given MAME file path."""
    with open("logic/romlist.txt", "w") as romlist:
        subprocess.run([mame_path + '\\mame.exe', "-ll"], stdout=romlist)


def build_rom_db(romlist: str) -> dict[str, str]:
    """Create and return a dictionary containing save file names, for roms that have them.

    All resulting strings are stripped of white space and double quotes."""
    rom_db = {}
    with open(romlist, 'r') as romlist:
        next(romlist)
        for line in romlist:
            description_start = line.index('"')
            description = line[description_start:]
            description = description.strip()
            description = description.strip('"')
            rom_name = line[:description_start]
            rom_name = rom_name.strip()
            rom_db[rom_name] = description
    return rom_db


def get_roms_with_saves(mame_path: str) -> list[str]:
    """Create and return a list of roms that have a save folder in the given MAME file path"""
    contents = os.listdir(mame_path + '\\sta')
    return contents


def get_real_name(rom_db: dict[str, str], rom_name: str) -> str:
    """Return the full name of a given rom"""
    real_name = rom_db[rom_name]
    return real_name


def get_save_names(games_with_saves: list[str], mame_folder: str) -> dict[str, list[str]]:
    """Return all save files, and their respective roms."""
    save_states = {}
    for game in games_with_saves:
        saves = os.listdir(mame_folder + "\\sta" + '\\' + game)

        for save in saves:
            i = saves.index(save)
            save, _ = os.path.splitext(save)
            saves[i] = save

        save_states[game] = saves
    return save_states


def rename(mame_folder: str, rom_folder: str, old_save_name: str, new_save_name: str) -> None:
    """Rename a MAME save file"""
    os.rename(mame_folder + "\\sta\\" + rom_folder + "\\" + old_save_name + '.sta',
              mame_folder + "\\sta\\" + rom_folder + "\\" + new_save_name + '.sta')


def change_mame_path(new_path: str) -> None:
    """Change the saved MAME path

    Finds and replaces the first line, in the romlist.txt file, with a MAME path that will be used as the working
    directory for the MAMEStates application."""
    with open('logic/romlist.txt', 'r') as romlist:
        data = romlist.read().splitlines(True)
        data[0] = new_path + '\n'
    with open('logic/romlist.txt', 'w') as romlist:
        romlist.writelines(data)
