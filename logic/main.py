"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.
"""
import json
import os
import pprint
import sqlite3
import subprocess

from pathlib import Path
import zipfile

import xmltodict

raw_mame_paths = [r'C:\Users\kazac\Downloads\wolfmame-0273',
                  r'C:\Users\kazac\Downloads\groovymame_0273.221d_win-7-8-10',
                  r'C:\Users\kazac\Downloads\mame']

PersonalBests = dict[str, dict[str, int | dict[str, str] | list]]
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
def get_roms_with_saves(mame_dir: Path) -> list[str]:
    """Create and return a list of roms that have a save folder in the given MAME file path"""
    rom_names = os.listdir(mame_dir / 'sta')
    return rom_names


# TODO Consider using pathlib instead of os.
#   Also, I think I'm modifying the list in place? Why though? Consider how this scales. Is a new list ok?
def get_save_names(roms_with_saves: list[str], mame_dir: Path) -> dict[str, list[str]]:
    """Return all save files, and their respective roms."""
    save_states = {}
    for rom in roms_with_saves:
        save_state_file_names = os.listdir(mame_dir / "sta" / rom)

        for name in save_state_file_names:
            save_index = save_state_file_names.index(name)
            name, _ = os.path.splitext(name)
            save_state_file_names[save_index] = name

        save_states[rom] = save_state_file_names
    return save_states


def get_all_input_files(mame_dirs: list[Path]) -> dict[str,list[str]]:
    """Retrieve and return input file names, for each path in the given list. File extensions are stripped."""
    all_input_files = {}
    for mame_dir in mame_dirs:
        input_file_dir = mame_dir / 'inp'
        if input_file_dir.is_dir():
            all_input_files[mame_dir] = [input_file.stem for input_file in input_file_dir.iterdir()]
    return all_input_files


def get_all_roms_with_saves(mame_dirs: list[Path]) -> dict[str,dict[str,list[str]]]:
    """Retrieve and return save state file names, for each path in the given list. File extensions are stripped."""
    all_save_state_names = {}
    for mame_dir in mame_dirs:
        roms_with_saves = get_roms_with_saves(mame_dir)
        save_state_names = get_save_names(roms_with_saves, mame_dir)
        all_save_state_names[mame_dir] = save_state_names
    return all_save_state_names


# TODO Consider generator
def get_real_name(description_db: dict[str, str], rom_name: str) -> str:
    """Return the full name of a given rom"""
    for key, value in description_db.items():
        if value == rom_name:
            real_name = key
            return real_name


#########
# Paths #
#########
def get_mame_dirs(cursor: sqlite3.Cursor) -> list[Path]:
    """Load paths as strings from database. Convert to Path objects before returning them."""
    sql_query = """SELECT * FROM paths"""
    cursor.execute(sql_query)
    raw_results = cursor.fetchall()
    mame_dirs = []
    for entry in raw_results:
        mame_dir = Path(entry[1])
        mame_dirs.append(mame_dir)
    return mame_dirs


# TODO This wipes out manually added version #s until I sort that out.
def save_mame_dirs(connection: sqlite3.Connection, cursor: sqlite3.Cursor, mame_dirs: list[Path]) -> None:
    """Format list of paths as rows. Insert them into database. """
    sql_statement = """INSERT OR IGNORE INTO paths VALUES (?, ?, ?, ?, ?);"""
    rows = []
    for mame_dir in mame_dirs:
        row = (None, str(mame_dir), mame_dir.name, None, None)
        rows.append(row)

    cursor.executemany(sql_statement, rows)
    connection.commit()


##################
# Personal Bests #
##################
def get_personal_bests(cursor: sqlite3.Cursor) -> PersonalBests:
    """Load and format all personal best information from the database."""
    pb_info = {}

    pb_query = """SELECT roms.description, personal_bests.highscore, personal_bests.other_fields 
    FROM 'roms' JOIN 'personal_bests' ON roms.id = personal_bests.rom_id"""

    splits_query = """SELECT splits.label, splits.score, splits.'index', roms.description, splits.id
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
        pb_info[split[3]]['splits'].append([split[0], split[1], split[4]])

    return pb_info


def save_pb_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, pb_info: PersonalBests) -> None:
    """Update database with provided personal best and split information.

       Rows are added if they do not exist, and updated otherwise.
       """
    pb_insert = ("INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = "
                 "excluded.highscore, other_fields = excluded.other_fields")
    splits_insert = ("INSERT INTO splits VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET label = excluded.label, "
                     "score = excluded.score, 'index' = excluded.'index'")

    pb_rows = collate_pb_rows(cursor, pb_info)
    split_rows = collate_split_rows(cursor, pb_info)

    cursor.executemany(pb_insert, pb_rows)
    cursor.executemany(splits_insert, split_rows)

    connection.commit()


def delete_personal_best(connection: sqlite3.Connection, cursor: sqlite3.Cursor, rom_description: str) -> None:
    """Delete personal best data from database, for a given rom."""
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


def get_raw_rom_info(cursor: sqlite3.Cursor) -> list[tuple]:
    """Retrieve all rom information from database and return it raw."""
    sql_statement = "SELECT * FROM roms"
    cursor.execute(sql_statement)
    results = cursor.fetchall()
    return results


##########
# Helper #
##########
def id_from_description(description: str, cursor: sqlite3.Cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom description, from the database."""
    sql_statement = "SELECT id FROM roms WHERE description = ?"
    cursor.execute(sql_statement, (description,))
    results = cursor.fetchall()
    rom_id = results[0][0]
    return rom_id


def id_from_rom_name(name: str, cursor: sqlite3.Cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom name, from the database."""
    sql_statement = "SELECT id FROM roms WHERE name = ?"
    cursor.execute(sql_statement, (name,))
    results = cursor.fetchall()
    rom_id = results[0][0]
    return rom_id


def collate_pb_rows(cursor: sqlite3.Cursor, pb_info: PersonalBests) -> list[tuple]:
    """Serialize personal best highscore and related information into rows for database insertion."""
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


# TODO Not used.
# def get_split_pk(cursor: sqlite3.Cursor, rom_description: str, split_label: str) -> list[tuple]:
#     """Retrieve a primary key from database. Rom id and split label are used as unique identifier."""
#     sql_statement = "SELECT id FROM splits WHERE rom_id = ? AND label = ?"
#     rom_id = id_from_description(rom_description, cursor)
#     cursor.execute(sql_statement, (rom_id, split_label))
#     results = cursor.fetchall()
#     return results


def collate_split_rows(cursor: sqlite3.Cursor, pb_info: PersonalBests) -> list[tuple]:
    """Serialize splits information into rows for database insertion.

    Split order is preserved by using the splits current position in its perspective splits list.
    """
    rows = []
    for pb in pb_info:
        pb_dict = pb_info[pb]
        splits = pb_dict['splits']
        for split in splits:
            # Results are returned raw and may be empty.
            # split_primary_key = get_split_pk(cursor, pb, item[0])
            # if split_primary_key:
            #     split_primary_key = split_primary_key[0][0]
            # else:
            #     split_primary_key = None

            if len(split) < 3:   # If no pk, must be new split. Give None to auto gen pk.
                split.append(None)
            row = (split[2], split[0], split[1], splits.index(split), id_from_description(pb, cursor))
            rows.append(row)
    return rows


def get_descriptions_and_names(cursor: sqlite3.Cursor) -> dict[str,str]:
    """Construct {rom_description:rom_name} dictionary.

    This dictionary is used as a quick in-memory reference that binds a roms description, to its name.
    The alternative would be querying them as needed.
    """
    sql_statement = """SELECT name, description FROM roms;"""
    cursor.execute(sql_statement)
    results = cursor.fetchall()
    descriptions_and_names = {}
    for entry in results:
        descriptions_and_names[entry[1]] = entry[0]

    return descriptions_and_names


def serialize_rom_info(raw_rom_info: list[tuple]) -> dict[str, dict[str, str]]:
    """Format raw rom info, from database, into in-memory representation."""
    formatted_rom_info = {}

    for row in raw_rom_info:
        formatted_rom_info[row[2]] = {'name': row[1], 'manufacturer': row[3], 'year': row[4], 'parent': row[5],
                            'video_info': f'{row[6]}x{row[7]}@{row[9]} - Rotate {row[8]}°', 'video_driver': row[10],
                            'sound_driver': row[11]}
    return formatted_rom_info


def get_formatted_rom_info(cursor: sqlite3.Cursor) -> dict[str, dict[str, str]]:
    """Retrieve and format raw rom info, from the database."""
    raw_rom_info = get_raw_rom_info(cursor)
    formatted_rom_info = serialize_rom_info(raw_rom_info)
    return formatted_rom_info


def has_xml(rom_name: str) -> bool:
    """Check if a given rom has an XML file, and is therefore compatible with 'hi2txt'."""
    zip_path = r'C:\Users\kazac\Downloads\hi2txt\hi2txt.zip'
    with zipfile.ZipFile(zip_path, 'r') as zip_obj:
        xml_strings = zip_obj.namelist()
        xml_paths = [Path(file_name) for file_name in xml_strings]
        xml_names = [file_name.stem for file_name in xml_paths]
        if rom_name in xml_names:
            return True
        else:
            return False

# TODO This is using global var for mame paths. Update to use DB mame paths.
#   Maybe consider how this will be used. Might want to make this method to access self.mame_paths.
def get_games_with_hs() -> dict[str, list[Path]]:
    hi2txt_compatible_hi_scores: dict[str, list[Path]] = {}
    for raw_string in raw_mame_paths:
        mame_dir = Path(raw_string)
        hiscore_dir = mame_dir / 'hiscore'
        hiscore_files = list(hiscore_dir.glob('*.hi'))
        hi2txt_compatible_hi_scores[str(mame_dir)] = hiscore_files

    zip_path = r'C:\Users\kazac\Downloads\hi2txt\hi2txt.zip'
    with zipfile.ZipFile(zip_path, 'r') as zip_obj:
        xml_strings = zip_obj.namelist()
        xml_paths = [Path(file_name) for file_name in xml_strings]
        xml_names = [file.stem for file in xml_paths]

    for mame_directory in hi2txt_compatible_hi_scores:
        hiscore_files = hi2txt_compatible_hi_scores[mame_directory]
        hi2txt_compatible_hiscore_files = [file for file in hiscore_files if file.stem in xml_names]
        hi2txt_compatible_hi_scores[mame_directory] = hi2txt_compatible_hiscore_files

    return hi2txt_compatible_hi_scores


def get_hs_tables(hi2txt_compatible_hi_scores: dict[str, list[Path]]) -> dict[str,dict[str,str]]:
    """Retrieve raw hi2txt leaderboard table output for compatible games with .hi file."""
    hi2txt_tables: dict[str,dict[str,str]] = {}
    for mame_dir in hi2txt_compatible_hi_scores:
        hi2txt_tables[mame_dir] = {}
        hiscore_files = hi2txt_compatible_hi_scores[mame_dir]
        for file in hiscore_files:
            print(f'Score is: {file}')
            try:
                results = subprocess.run([r'C:\Users\kazac\Downloads\hi2txt\hi2txt.exe', '-r', f'{file}'],
                                         cwd=r'C:\Users\kazac\Downloads\hi2txt', capture_output=True, text=True,
                                         check=True, encoding='utf-8')
                hi2txt_tables[mame_dir][f'{file.stem}'] = results.stdout
            except FileNotFoundError:
                print('whoops')
    return hi2txt_tables


def format_table(raw_hi2txt_table: str) -> dict[str, list | str]:
    """Split raw hi2txt leaderboard tables into usable python representations."""
    table = {}
    leaderboards = raw_hi2txt_table.split('\n#')
    for leaderboard in leaderboards:
        # pprint.pp(leaderboard.splitlines())
        leaderboard_lines = leaderboard.splitlines()
        leaderboard_lines = [line for line in leaderboard_lines if line]
        if leaderboard_lines[0].startswith('#') or leaderboard_lines[0].startswith(' '):
            leaderboard_name = leaderboard_lines.pop(0).strip('# ')
            columns = leaderboard_lines.pop(0)
            table['col'] = columns
            table['name'] = leaderboard_name
            table['rows'] = leaderboard_lines
            return table
        else:
            columns = leaderboard_lines.pop(0)
            table['col'] = columns
            table['rows'] = leaderboard_lines
            return table


def get_new_pb(old_raw_table: str, new_raw_table: str) -> dict[str, str] | None:
    """Compare two raw hi2txt tables to look for new, possible, personal best."""
    old_table = format_table(old_raw_table)
    new_table = format_table(new_raw_table)
    old_columns = old_table['col']
    new_columns = new_table['col']
    old_leaderboard = old_table.get('name')
    new_leaderboard = new_table.get('name')
    old_rows = old_table['rows']
    new_rows = new_table['rows']
    new_pb = {}

    # TODO Move print downstream at usage and make messagebox.
    if old_columns != new_columns or old_leaderboard != new_leaderboard:
        print('Incompatible table schemas.')
        return

    for index, line in enumerate(new_rows):
        if line != old_rows[index]:
            new_pb['col'] = new_columns
            new_pb['row'] = line
            if new_leaderboard:
                new_pb['name'] = new_leaderboard
            return new_pb


def get_new_pbs(hi2txt_tables: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Scan for new, possible, personal bests. Compares current Hi Score tables to game defaults."""
    defaults_xml = Path(r'C:\Users\kazac\Downloads\hi2txt\hi2txt_doc\hi2txt_defaults')
    new_pbs = {}
    # pprint.pp(hi_text_output)
    for mame_dir in hi2txt_tables:
        pb_dict = hi2txt_tables[mame_dir]
        # print(pb_dict)

        for rom_name in pb_dict:
            leaderboards = pb_dict[rom_name].split('\n#')
            for leaderboard in leaderboards:
                # pprint.pp(leaderboard.splitlines())
                leaderboard_lines = leaderboard.splitlines()
                if leaderboard_lines[0].startswith('#') or leaderboard_lines[0].startswith(' '):
                    leaderboard_name = leaderboard_lines.pop(0).strip('# ')
                    columns = leaderboard_lines.pop(0)
                    with open(defaults_xml / f'{rom_name}.xml', 'r') as xml_file:
                        xml_data = xml_file.read()
                        data_dict = xmltodict.parse(xml_data)
                        tables = data_dict['hi2txt']['table']
                        for table in tables:
                            if table['@id'] == leaderboard_name:
                                default_table = table
                                leaderboard_lines = [line for line in leaderboard_lines if line]
                                for index, line in enumerate(leaderboard_lines):
                                    if line.split('|') != default_table['row'][index]['cell']:
                                        print(f'New PB detected - {rom_name} - {leaderboard_name}')
                                        print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
                                        some_dic = {}
                                        for i, section in enumerate(line.split('|')):
                                            some_dic[columns.split('|')[i]] = section

                                        new_pbs[rom_name] = some_dic
                                        pprint.pp(some_dic)
                                        break
                else:
                    columns = leaderboard_lines.pop(0)
                    with open(defaults_xml / f'{rom_name}.xml', 'r') as xml_file:
                        xml_data = xml_file.read()
                        data_dict = xmltodict.parse(xml_data)
                        default_table = data_dict['hi2txt']['table']
                        leaderboard_lines = [line for line in leaderboard_lines if line]
                        for index, line in enumerate(leaderboard_lines):
                            if isinstance(default_table['row'], list) is True:
                                if line.split('|') != default_table['row'][index]['cell']:
                                    print(f'New PB detected - {rom_name}')
                                    print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
                                    some_dic = {}
                                    for i, section in enumerate(line.split('|')):
                                        some_dic[columns.split('|')[i]] = section

                                    pprint.pp(some_dic)
                                    new_pbs[rom_name] = some_dic
                                    break
                            else:
                                if line.split('|') != default_table['row']['cell']:
                                    print(f'New PB detected - {rom_name}')
                                    print(f'{default_table['row']['cell']} --> \n{columns}\n{line}')
                                    some_dic = {}
                                    for i, section in enumerate(line.split('|')):
                                        some_dic[columns.split('|')[i]] = section

                                    new_pbs[rom_name] = some_dic
                                    pprint.pp(some_dic)
                                    break
    return new_pbs


def prepare_pb_for_db(new_pb: dict[str, str], rom_name: str) -> dict[str, dict[str, str]]:
    """Convert a single new PB entry, into the format used by multiple PB insertion function.

    TODO This is lazy af.
    """
    all_pbs = {}
    pb = {}
    columns = new_pb['col'].split('|')
    row = new_pb['row'].split('|')
    for index, section in enumerate(row):
        pb[columns[index]] = section

    all_pbs[rom_name] = pb
    return all_pbs


def save_pbs(new_pbs: dict[str:dict[str:str]], connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Insert or update new PB entries into database, if new PB has a higher score."""
    for rom_name in new_pbs:
        pb = new_pbs[rom_name]
        pb.pop('RANK', None)
        pb.pop('NAME', None)

        score = pb.pop('SCORE')
        if not pb:
            other_fields = None
        else:
            other_fields = json.dumps(pb)
        row = (None, score, other_fields, id_from_rom_name(rom_name, cursor))
        sql_statement = ("INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = "
               "excluded.highscore, other_fields = excluded.other_fields WHERE excluded.highscore > highscore")
        cursor.execute(sql_statement, row)
    connection.commit()


def scan_for_pb(connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Scan hi score tables, parse for possible PB entries and insert or update PB table in database."""
    hi_scores = get_games_with_hs()
    hi2txt_tables = get_hs_tables(hi_scores)
    new_pbs = get_new_pbs(hi2txt_tables)
    save_pbs(new_pbs, connection, cursor)

# TODO Temp fix after I realized inps need version in name.
def get_mame_version(mame_dir: Path):
    mame_exe = mame_dir / 'mame.exe'
    if mame_exe.is_file():
        results = subprocess.run([mame_exe, '-version'], cwd=mame_dir, capture_output=True, text=True)
        return results.stdout

# if __name__ == '__main__':
#     for path in raw_mame_paths:
#         results = subprocess.run([(path + r'\mame.exe'), '-version'], cwd=path, capture_output=True, text=True)
#         print(results.stdout)