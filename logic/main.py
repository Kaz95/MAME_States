"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.
"""
import json
import os
import pprint
import sqlite3
import subprocess
from math import trunc
from pathlib import Path
import zipfile

import xmltodict

raw_mame_paths = [r'C:\Users\kazac\Downloads\wolfmame-0273',
                  r'C:\Users\kazac\Downloads\groovymame_0273.221d_win-7-8-10',
                  r'C:\Users\kazac\Downloads\mame']

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


###############
# Save States #
###############
def get_roms_with_saves(mame_path: Path) -> list[str]:
    """Create and return a list of roms that have a save folder in the given MAME file path"""
    contents = os.listdir(mame_path / 'sta')
    return contents


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


def get_all_input_files(mame_paths: list[Path]):
    all_inps = {}
    for path in mame_paths:
        inp_folder = path / 'inp'
        if inp_folder.is_dir():
            all_inps[path] = [item.name for item in inp_folder.iterdir()]
    return all_inps


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


def rename_save_state_file(mame_folder: Path, rom_folder: str, old_save_name: str, new_save_name: str) -> None:
    """Rename a MAME save file"""
    os.rename(mame_folder / "sta" / rom_folder / (old_save_name + '.sta'),
              mame_folder / "sta" / rom_folder / (new_save_name + '.sta'))


#########
# Paths #
#########
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


##################
# Personal Bests #
##################
def new_load_personal_bests_from_database(cursor: sqlite3.Cursor) -> PersonalBestDataBase:
    """Load and format all personal best information from the database."""
    pb_info: PersonalBestDataBase = {}

    pb_query = """SELECT roms.description, personal_bests.highscore, personal_bests.other_fields 
    FROM 'roms' JOIN 'personal_bests' ON roms.id = personal_bests.rom_id"""

    splits_query = """SELECT splits.label, splits.score, splits.'index', roms.description 
        FROM 'splits' JOIN 'roms' ON splits.rom_id = roms.id 
        ORDER BY roms.description, splits.'index'"""

    cursor.execute(pb_query)
    personal_bests = cursor.fetchall()

    for pb in personal_bests:
        if pb[2]:
            other_fields = json.loads(pb[2])
        else:
            other_fields = None
        pb_info[pb[0]] = {'hs': pb[1], 'other_fields': other_fields, 'splits': []}

    cursor.execute(splits_query)
    splits = cursor.fetchall()
    for split in splits:
        pb_info[split[3]]['splits'].append([split[0], split[1]])

    return pb_info


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

def new_save_pb_to_database(connection, cursor, pb_info):
    """Update database with provided personal best and split information.

       Rows are added if they do not exist, and updated otherwise.
       """
    pb_insert = ("INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = "
                 "excluded.highscore, other_fields = excluded.other_fields WHERE excluded.highscore > highscore")
    splits_insert = ("INSERT INTO splits VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET label = excluded.label, "
                     "score = excluded.score, 'index' = excluded.'index'")

    pb_rows = new_collate_pb_rows(cursor, pb_info)
    splits = collate_splits(cursor, pb_info)

    cursor.executemany(pb_insert, pb_rows)
    cursor.executemany(splits_insert, splits)

    connection.commit()


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


def delete_personal_best(connection: sqlite3.Connection, cursor: sqlite3.Cursor, rom_description: str) -> None:
    """Delete 'highscore' and 'distance' data from database, for a given rom."""
    sql_statement = "DELETE FROM personal_bests WHERE rom_id = ?"
    rom_id = id_from_description(rom_description, cursor)
    cursor.execute(sql_statement, (rom_id,))
    connection.commit()


def delete_splits(connection: sqlite3.Connection, cursor: sqlite3.Cursor, rom_description: str) -> None:
    """Delete all 'splits' data from database, for a given rom."""
    sql_statement = "DELETE FROM splits WHERE rom_id = ?"
    rom_id = id_from_description(rom_description, cursor)
    cursor.execute(sql_statement, (rom_id,))
    connection.commit()


def delete_split(connection: sqlite3.Connection, cursor: sqlite3.Cursor, rom_description: str,
                 split_label: str) -> None:
    """Delete a single split from the database. Rom id and split label text are used as unique identifier."""
    sql_statement = "DELETE FROM splits WHERE rom_id = ? AND label = ?"
    rom_id = id_from_description(rom_description, cursor)
    cursor.execute(sql_statement, (rom_id, split_label))
    connection.commit()


def get_rom_info(cursor: sqlite3.Cursor):
    sql_statement = "SELECT * FROM roms"
    cursor.execute(sql_statement)
    results = cursor.fetchall()
    return results


##########
# Helper #
##########
def id_from_description(name: str, cursor: sqlite3.Cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom description, from the database."""
    sql_statement = "SELECT id FROM roms WHERE description = ?"
    cursor.execute(sql_statement, (name,))
    rom_id = cursor.fetchall()
    rom_id = rom_id[0][0]
    return rom_id

def id_from_rom_name(name: str, cursor: sqlite3.Cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom description, from the database."""
    sql_statement = "SELECT id FROM roms WHERE name = ?"
    cursor.execute(sql_statement, (name,))
    rom_id = cursor.fetchall()
    rom_id = rom_id[0][0]
    return rom_id


def new_collate_pb_rows(cursor: sqlite3.Cursor, pb_info: PersonalBestDataBase) -> list[tuple]:
    """Serialize personal best highscore and distance information into rows for database insertion."""
    rows = []
    for key in pb_info:
        pb_dict = pb_info[key]
        rom_id = id_from_description(key, cursor)
        highscore = pb_dict['hs']
        other_fields = pb_dict['other_fields']
        other_fields = json.dumps(other_fields)
        row = (None, highscore, other_fields, rom_id)
        rows.append(row)
    return rows


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


def get_split_pk(cursor: sqlite3.Cursor, rom_description: str, split_label: str) -> list[tuple]:
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


def serialize_rom_info(cursor: sqlite3.Cursor):
    rom_info = {}
    results = get_rom_info(cursor)
    for row in results:
        rom_info[row[2]] = {'name': row[1], 'manufacturer': row[3], 'year': row[4], 'parent': row[5],
                            'video_info': f'{row[6]}x{row[7]}@{row[9]} - Rotate {row[8]}°', 'video_driver': row[10],
                            'sound_driver': row[11]}
    return rom_info

def get_games_with_hs() -> dict[str: list[Path]]:
    games_with_hi: dict[str: list[Path]] = {}
    for raw_string in raw_mame_paths:
        path = Path(raw_string)
        hi_path = path / 'hiscore'
        hi_file_paths = list(hi_path.glob('*.hi'))
        # hi_file_names = [x for x in hi_file_paths]
        games_with_hi[str(path)] = hi_file_paths

    zip_path = r'C:\Users\kazac\Downloads\hi2txt\hi2txt.zip'
    with zipfile.ZipFile(zip_path, 'r') as zip_obj:
        xml_strings = zip_obj.namelist()
        xml_paths = [Path(x) for x in xml_strings]
        xml_names = [x.stem for x in xml_paths]

    for path in games_with_hi:
        hi = games_with_hi[path]
        hi_with_xml = [x for x in hi if x.stem in xml_names]
        games_with_hi[path] = hi_with_xml

    return games_with_hi

def get_hs_tables(games_with_hi: dict[str: [Path]]) -> dict[str:dict[str:str]]:
    hi_text_output: dict[str:dict[str:str]] = {}
    for path in games_with_hi:
        hi_text_output[path] = {}
        scores = games_with_hi[path]
        for score in scores:
            print(f'Score is: {score}')
            try:
                results = subprocess.run([r'C:\Users\kazac\Downloads\hi2txt\hi2txt.exe', '-r', f'{score}'],
                                         cwd=r'C:\Users\kazac\Downloads\hi2txt', capture_output=True, text=True,
                                         check=True, encoding='utf-8')
                hi_text_output[path][f'{score.stem}'] = results.stdout
            except FileNotFoundError:
                print('whoops')
    return hi_text_output

def get_new_pbs(hi_text_output: dict[str:dict[str:str]]):
    defaults_xml = Path(r'C:\Users\kazac\Downloads\hi2txt\hi2txt_doc\hi2txt_defaults')
    new_pbs = {}
    # pprint.pp(hi_text_output)
    for path in hi_text_output:
        pb_dict = hi_text_output[path]
        # print(pb_dict)

        for game in pb_dict:
            leaderboards = pb_dict[game].split('\n#')
            for leaderboard in leaderboards:
                # pprint.pp(leaderboard.splitlines())
                leaderboard = leaderboard.splitlines()
                if leaderboard[0].startswith('#') or leaderboard[0].startswith(' '):
                    leaderboard_name = leaderboard.pop(0).strip('# ')
                    columns = leaderboard.pop(0)
                    with open(defaults_xml / f'{game}.xml', 'r') as xml_file:
                        xml_data = xml_file.read()
                        data_dict = xmltodict.parse(xml_data)
                        tables = data_dict['hi2txt']['table']
                        for table in tables:
                            if table['@id'] == leaderboard_name:
                                default_table = table
                                leaderboard = [x for x in leaderboard if x]
                                for index, line in enumerate(leaderboard):
                                    if line.split('|') != default_table['row'][index]['cell']:
                                        print(f'New PB detected - {game} - {leaderboard_name}')
                                        print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
                                        some_dic = {}
                                        for i, section in enumerate(line.split('|')):
                                            some_dic[columns.split('|')[i]] = section

                                        new_pbs[game] = some_dic
                                        pprint.pp(some_dic)
                                        break
                else:
                    columns = leaderboard.pop(0)
                    with open(defaults_xml / f'{game}.xml', 'r') as xml_file:
                        xml_data = xml_file.read()
                        data_dict = xmltodict.parse(xml_data)
                        default_table = data_dict['hi2txt']['table']
                        leaderboard = [x for x in leaderboard if x]
                        for index, line in enumerate(leaderboard):
                            if isinstance(default_table['row'], list) is True:
                                if line.split('|') != default_table['row'][index]['cell']:
                                    print(f'New PB detected - {game}')
                                    print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
                                    some_dic = {}
                                    for i, section in enumerate(line.split('|')):
                                        some_dic[columns.split('|')[i]] = section

                                    pprint.pp(some_dic)
                                    new_pbs[game] = some_dic
                                    break
                            else:
                                if line.split('|') != default_table['row']['cell']:
                                    print(f'New PB detected - {game}')
                                    print(f'{default_table['row']['cell']} --> \n{columns}\n{line}')
                                    some_dic = {}
                                    for i, section in enumerate(line.split('|')):
                                        some_dic[columns.split('|')[i]] = section

                                    new_pbs[game] = some_dic
                                    pprint.pp(some_dic)
                                    break
    return new_pbs

def save_pbs(new_pbs: dict[str:dict[str:str]], connection,  cursor):
    for game in new_pbs:
        pb = new_pbs[game]
        pb.pop('RANK', None)
        pb.pop('NAME', None)

        score = pb.pop('SCORE')
        if not pb:
            other_fields = None
        else:
            other_fields = json.dumps(pb)
        row = (None, score, other_fields, id_from_rom_name(game, cursor))
        sql = "INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = excluded.highscore, other_fields = excluded.other_fields WHERE excluded.highscore > highscore"
        cursor.execute(sql, row)
    connection.commit()

def scan_for_pb(connection, cursor):
    hi_scores = get_games_with_hs()
    hi2txt_output = get_hs_tables(hi_scores)
    new_pbs = get_new_pbs(hi2txt_output)
    save_pbs(new_pbs, connection, cursor)

if __name__ == '__main__':
    hi_scores = get_games_with_hs()
    hi2txt_output = get_hs_tables(hi_scores)
    new_pbs = get_new_pbs(hi2txt_output)
    # save_pbs(new_pbs)
    # pprint.pp(new_pbs)
    # with sqlite3.connect(r'C:\Users\kazac\AppData\Roaming\JetBrains\PyCharmCE2024.3\scratches\test_mame_states.db') as con:
    #     cursor = con.cursor()
    #     r = new_load_personal_bests_from_database(cursor)
    #     pprint.pp(r)
    #  -------------------------------------------------------------------
    # Get games with hs {mame_path: [hi_score_paths], ...}
    # games_with_hi = {}
    # for raw_string in raw_mame_paths:
    #     path = Path(raw_string)
    #     hi_path = path / 'hiscore'
    #     hi_file_paths = list(hi_path.glob('*.hi'))
    #     # hi_file_names = [x for x in hi_file_paths]
    #     games_with_hi[str(path)] = hi_file_paths
    #
    # zip_path = r'C:\Users\kazac\Downloads\hi2txt\hi2txt.zip'
    # with zipfile.ZipFile(zip_path, 'r') as zip_obj:
    #     xml_strings = zip_obj.namelist()
    #     xml_paths = [Path(x) for x in xml_strings]
    #     xml_names = [x.stem for x in xml_paths]
    #
    # for path in games_with_hi:
    #     hi = games_with_hi[path]
    #     hi_with_xml = [x for x in hi if x.stem in xml_names]
    #     games_with_hi[path] = hi_with_xml

    # pprint.pp(games_with_hi)

    # --------------------------------------------
    # Use hi2txt to retrieve hi score tables.
    # hi_text_output = {}
    # for path in games_with_hi:
    #     hi_text_output[path] = {}
    #     scores = games_with_hi[path]
    #     for score in scores:
    #         print(f'Score is: {score}')
    #         try:
    #             results = subprocess.run([r'C:\Users\kazac\Downloads\hi2txt\hi2txt.exe', '-r', f'{score}'],
    #                                      cwd=r'C:\Users\kazac\Downloads\hi2txt', capture_output=True, text=True,
    #                                      check=True, encoding='utf-8')
    #             hi_text_output[path][f'{score.stem}'] = results.stdout
    #         except FileNotFoundError:
    #             print('whoops')
    #
    # pprint.pp(hi_text_output)
    # ----------------------------------------------------------------------------------------
    # Create dictionary of all possible new PBs. Uses hi score tables to compare against default tables.
    # defaults_xml = Path(r'C:\Users\kazac\Downloads\hi2txt\hi2txt_doc\hi2txt_defaults')
    # new_pbs = {}
    # # pprint.pp(hi_text_output)
    # for path in hi_text_output:
    #     pb_dict = hi_text_output[path]
    #     print(pb_dict)
    #
    #     for game in pb_dict:
    #         leaderboards = pb_dict[game].split('\n#')
    #         for leaderboard in leaderboards:
    #             # pprint.pp(leaderboard.splitlines())
    #             leaderboard = leaderboard.splitlines()
    #             if leaderboard[0].startswith('#') or leaderboard[0].startswith(' '):
    #                 leaderboard_name = leaderboard.pop(0).strip('# ')
    #                 columns = leaderboard.pop(0)
    #                 with open(defaults_xml / f'{game}.xml', 'r') as xml_file:
    #                     xml_data = xml_file.read()
    #                     data_dict = xmltodict.parse(xml_data)
    #                     tables = data_dict['hi2txt']['table']
    #                     for table in tables:
    #                         if table['@id'] == leaderboard_name:
    #                             default_table = table
    #                             leaderboard = [x for x in leaderboard if x]
    #                             for index, line in enumerate(leaderboard):
    #                                 if line.split('|') != default_table['row'][index]['cell']:
    #                                     print(f'New PB detected - {game} - {leaderboard_name}')
    #                                     print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
    #                                     some_dic = {}
    #                                     for i, section in enumerate(line.split('|')):
    #                                         some_dic[columns.split('|')[i]] = section
    #
    #                                     new_pbs[game] = some_dic
    #                                     pprint.pp(some_dic)
    #                                     break
    #             else:
    #                 columns = leaderboard.pop(0)
    #                 with open(defaults_xml / f'{game}.xml', 'r') as xml_file:
    #                     xml_data = xml_file.read()
    #                     data_dict = xmltodict.parse(xml_data)
    #                     default_table = data_dict['hi2txt']['table']
    #                     leaderboard = [x for x in leaderboard if x]
    #                     for index, line in enumerate(leaderboard):
    #                         if isinstance(default_table['row'], list) is True:
    #                             if line.split('|') != default_table['row'][index]['cell']:
    #                                 print(f'New PB detected - {game}')
    #                                 print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
    #                                 some_dic = {}
    #                                 for i, section in enumerate(line.split('|')):
    #                                     some_dic[columns.split('|')[i]] = section
    #
    #                                 pprint.pp(some_dic)
    #                                 new_pbs[game] = some_dic
    #                                 break
    #                         else:
    #                             if line.split('|') != default_table['row']['cell']:
    #                                 print(f'New PB detected - {game}')
    #                                 print(f'{default_table['row']['cell']} --> \n{columns}\n{line}')
    #                                 some_dic = {}
    #                                 for i, section in enumerate(line.split('|')):
    #                                     some_dic[columns.split('|')[i]] = section
    #
    #                                 new_pbs[game] = some_dic
    #                                 pprint.pp(some_dic)
    #                                 break
    #
    # pprint.pp(new_pbs)
    # -------------------------------------------------------------------------------------------------------------
    # Insert or update new pbs, where score is higher.
    # for game in new_pbs:
    #     pb = new_pbs[game]
    #     pb.pop('RANK', None)
    #     pb.pop('NAME', None)
    #
    #     with sqlite3.connect(r'C:\Users\kazac\AppData\Roaming\JetBrains\PyCharmCE2024.3\scratches\mame_states.db') as connection:
    #         cursor = connection.cursor()
    #         score = pb.pop('SCORE')
    #         if not pb:
    #             other_fields = None
    #         else:
    #             other_fields = json.dumps(pb)
    #         row = (None, score, other_fields, id_from_rom_name(game, cursor))
    #         sql = "INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = excluded.highscore, other_fields = excluded.other_fields WHERE excluded.highscore > highscore"
    #         cursor.execute(sql, row)
    #         connection.commit()
    # pprint.pp(new_pbs)