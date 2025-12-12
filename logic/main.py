"""This will be a program to rename MAME save states"""
import subprocess
import os


# TODO More descriptive comment
# Get list of rom names
def create_rom_list(mame_path: str) -> None:
    with open("logic/romlist.txt", "w") as romlist:
        subprocess.run([mame_path + '\\mame.exe', "-ll"], stdout=romlist)


# TODO Comment
def build_rom_db(romlist: str) -> dict[str, str]:
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


# Get list of save folder names
def get_roms_with_saves(mame_path: str) -> list[str]:
    contents = os.listdir(mame_path + '\\sta')
    return contents


# TODO Update Comment
# For save folder in list, get real name
def get_real_name(rom_db: dict[str, str], rom_name: str) -> str:
    real_name = rom_db[rom_name]
    return real_name


# TODO Update Comment
# For save folder in list, get save file names
def get_save_names(games_with_saves: list[str], mame_folder: str) -> dict[str, list[str]]:
    save_states = {}
    for game in games_with_saves:
        saves = os.listdir(mame_folder + "\\sta" + '\\' + game)

        for save in saves:
            i = saves.index(save)
            save, _ = os.path.splitext(save)
            saves[i] = save

        save_states[game] = saves
    return save_states


# TODO Comment
def rename(mame_folder: str, rom_folder: str, old_save_name: str, new_save_name: str) -> None:
    os.rename(mame_folder + "\\sta\\" + rom_folder + "\\" + old_save_name + '.sta',
              mame_folder + "\\sta\\" + rom_folder + "\\" + new_save_name + '.sta')


# TODO Rename to be more descriptive.
def change_mame_path(new_path: str) -> None:
    with open('logic/romlist.txt', 'r') as romlist:
        data = romlist.read().splitlines(True)
        data[0] = new_path + '\n'
    with open('logic/romlist.txt', 'w') as romlist:
        romlist.writelines(data)
