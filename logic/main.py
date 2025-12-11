"""This will be a program to rename MAME save states"""
import pprint
import subprocess
import os

# Hardcode an address path to mame folder
# mame_folder = "C:\\Users\\kazac\\Downloads\\wolfmame-0273"


# Get list of rom names
def create_rom_list(mame_path):
    with open("logic/romlist.txt", "w") as romlist:
        subprocess.run([mame_path + '\\mame.exe', "-ll"], stdout=romlist)

def build_rom_db(romlist):
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

# Get list of save folders
def get_roms_with_saves(mame_path):
    contents = os.listdir(mame_path + '\\sta')
    return contents

# TODO Bugged. Roms like 'vr' can trigger wrong description. Make dict and use as DB for now.
# For save folder in list, get real name
def get_real_name(rom_db, rom_name):
    real_name = rom_db[rom_name]
    return real_name

# For save folder in list, get save file names
def get_save_names(games_with_saves, mame_folder):
    save_states = {}
    for game in games_with_saves:
        saves = os.listdir(mame_folder + "\\sta" + '\\' + game)

        for save in saves:
            i = saves.index(save)
            save, _ = os.path.splitext(save)
            saves[i] = save

        # print(saves)
        save_states[game] = saves
    return save_states

def rename(mame_folder, rom_folder, old_save_name, new_save_name):
    os.rename(mame_folder + "\\sta\\" + rom_folder + "\\" + old_save_name + '.sta',
              mame_folder + "\\sta\\" + rom_folder + "\\" + new_save_name + '.sta')

# TODO Rename to be more descriptive.
def change_mame_path(new_path):
    with open('logic/romlist.txt', 'r') as romlist:
        data = romlist.read().splitlines(True)
        data[0] = new_path + '\n'
    with open('logic/romlist.txt', 'w') as romlist:
        romlist.writelines(data)

# Collate and list information

# Write GUI

# Fine

if __name__ == '__main__':
    change_mame_path('something else')
    # with open('romlist.txt', 'r') as romlist:
    #     data = romlist.read().splitlines(True)
    #     data[0] = 'hasdasdssssssasdsdasssssssssssssasd\n'
    # with open('romlist.txt', 'w') as romlist:
    #
    #     romlist.writelines(data)


    # get_romlist(mame_folder)
    # has_saves = get_roms_with_saves(mame_folder)
    # pprint.pprint(get_save_names(has_saves))
    # pprint.pprint(has_saves)
    # for rom in has_saves:
    #     real_name = get_real_name('romlist.txt', rom)
    #     real_name.strip('"')
    #     print(real_name)
    # savess = get_save_names(has_saves)

    # pprint.pp(saves)

