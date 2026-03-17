import json
import pprint
import sqlite3
import subprocess
from pathlib import Path

import zipfile
import xmltodict

import core


def has_xml(rom_name: str) -> bool:
    """Check if a given rom has an XML file, and is therefore compatible with 'hi2txt'."""
    zip_path = core.get_abs_path(r'.\hi2txt\hi2txt.zip')
    with zipfile.ZipFile(zip_path, 'r') as zip_obj:
        xml_strings = zip_obj.namelist()
        xml_paths = [Path(file_name) for file_name in xml_strings]
        xml_names = [file_name.stem for file_name in xml_paths]
        if rom_name in xml_names:
            return True
        else:
            return False

def get_games_with_hs(mame_dirs: list[core.MAMEDir]) -> dict[str, list[Path]]:
    """Retrieve and return all hiscore files with compatible hi2txt xml files, based on the given list of MAME directories."""
    hi2txt_compatible_hi_scores: dict[str, list[Path]] = {}
    for mame_dir in mame_dirs:
        hiscore_dir = mame_dir.path / 'hiscore'
        hiscore_files = list(hiscore_dir.glob('*.hi'))
        hi2txt_compatible_hi_scores[str(mame_dir)] = hiscore_files

    zip_path = core.get_abs_path(r'.\hi2txt\hi2txt.zip')
    with zipfile.ZipFile(zip_path, 'r') as zip_obj:
        xml_strings = zip_obj.namelist()
        xml_paths = [Path(file_name) for file_name in xml_strings]
        xml_names = [file.stem for file in xml_paths]

    for mame_directory in hi2txt_compatible_hi_scores:
        hiscore_files = hi2txt_compatible_hi_scores[mame_directory]
        hi2txt_compatible_hiscore_files = [file for file in hiscore_files if file.stem in xml_names]
        hi2txt_compatible_hi_scores[mame_directory] = hi2txt_compatible_hiscore_files

    return hi2txt_compatible_hi_scores


def get_hs_tables(hi2txt_compatible_hi_scores: dict[str, list[Path]]) -> dict[str, dict[str, str]]:
    """Retrieve raw hi2txt leaderboard table output for compatible games with .hi file."""
    hi2txt_tables: dict[str, dict[str, str]] = {}
    for mame_dir in hi2txt_compatible_hi_scores:
        hi2txt_tables[mame_dir] = {}
        hiscore_files = hi2txt_compatible_hi_scores[mame_dir]
        for file in hiscore_files:
            print(f'Score is: {file}')
            results = subprocess.run([core.get_abs_path(r'.\hi2txt\hi2txt.exe'), '-r', f'{file}'],
                                     cwd=core.get_abs_path(r'.\hi2txt'), capture_output=True, text=True,
                                     check=True, encoding='utf-8')
            hi2txt_tables[mame_dir][f'{file.stem}'] = results.stdout
    return hi2txt_tables


def format_table(raw_hi2txt_table: str) -> dict[str, list | str]:
    """Split raw hi2txt leaderboard tables into usable python representations."""
    table = {}
    leaderboards = raw_hi2txt_table.split('\n#')
    for leaderboard in leaderboards:
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
    pprint.pp(old_table)
    pprint.pp(new_table)
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


# FIXME Too much code reuse.
def get_new_pbs(hi2txt_tables: dict[str, dict[str, str]], cursor: sqlite3.Cursor) -> core.PersonalBests:
    """Scan for new, possible, personal bests. Compares current Hi Score tables to game defaults."""
    defaults_xml = Path(core.get_abs_path(r'.\hi2txt\hi2txt_doc\hi2txt_defaults'))
    new_pbs = {}
    for mame_dir in hi2txt_tables:
        pb_dict = hi2txt_tables[mame_dir]
        for rom_name in pb_dict:
            leaderboards = pb_dict[rom_name].split('\n#')
            for leaderboard in leaderboards:
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
                                        # print(f'New PB detected - {rom_name} - {leaderboard_name}')
                                        # print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
                                        some_dic = {}
                                        for i, section in enumerate(line.split('|')):
                                            some_dic[columns.split('|')[i]] = section
                                        some_dic.pop('NAME', None)
                                        some_dic.pop('RANK', None)
                                        rom_id = id_from_rom_name(rom_name, cursor)
                                        pb = core.PersonalBest(int(some_dic.pop('SCORE')), rom_id,some_dic)
                                        new_pbs[rom_name] = pb

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
                                    # print(f'New PB detected - {rom_name}')
                                    # print(f'{default_table['row'][index]['cell']} --> \n{columns}\n{line}')
                                    some_dic = {}
                                    for i, section in enumerate(line.split('|')):
                                        some_dic[columns.split('|')[i]] = section
                                    some_dic.pop('NAME', None)
                                    some_dic.pop('RANK', None)
                                    rom_id = id_from_rom_name(rom_name, cursor)
                                    pb = core.PersonalBest(int(some_dic.pop('SCORE')), rom_id,some_dic)
                                    new_pbs[rom_name] = pb

                                    pprint.pp(some_dic)
                                    break
                            else:
                                if line.split('|') != default_table['row']['cell']:
                                    # print(f'New PB detected - {rom_name}')
                                    # print(f'{default_table['row']['cell']} --> \n{columns}\n{line}')
                                    some_dic = {}
                                    for i, section in enumerate(line.split('|')):
                                        some_dic[columns.split('|')[i]] = section
                                    some_dic.pop('NAME', None)
                                    some_dic.pop('RANK', None)
                                    rom_id = id_from_rom_name(rom_name, cursor)
                                    pb = core.PersonalBest(int(some_dic.pop('SCORE')), rom_id,some_dic)
                                    new_pbs[rom_name] = pb

                                    pprint.pp(some_dic)
                                    break
    return new_pbs


def prepare_pb_for_db(new_pb: dict[str, str], rom_name: str, cursor:sqlite3.Cursor) -> core.PersonalBests:
    """Convert a single new PB entry, into the format used by multiple PB insertion function.

    TODO This is lazy af.
    """
    all_pbs = {}
    pb = {}
    columns = new_pb['col'].split('|')
    row = new_pb['row'].split('|')
    for index, section in enumerate(row):
        pb[columns[index]] = section
    pb.pop('NAME', None)
    pb.pop('RANK', None)
    rom_id = id_from_rom_name(rom_name, cursor)
    new_pb = core.PersonalBest(int(pb.pop('SCORE')), rom_id,pb)
    pprint.pp(pb)
    all_pbs[rom_name] = new_pb
    return all_pbs


def id_from_rom_name(name: str, cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom name, from the database."""
    sql_statement = "SELECT id FROM roms WHERE name = ?"
    cursor.execute(sql_statement, (name,))
    row = cursor.fetchone()
    rom_id = row['id']
    return rom_id


def save_pbs(new_pbs: core.PersonalBests, connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Insert or update new PB entries into database, if new PB has a higher score."""
    for rom_name in new_pbs:
        pb = new_pbs[rom_name]
        other_fields = json.dumps(pb.other_fields)
        rom_id = id_from_rom_name(rom_name, cursor)

        row = (pb.hiscore, other_fields, rom_id)
        sql_statement = (
            "INSERT INTO personal_bests (hiscore, other_fields, rom_id) VALUES (?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET hiscore = "
            "excluded.hiscore, other_fields = excluded.other_fields WHERE excluded.hiscore > hiscore")
        cursor.execute(sql_statement, row)
    connection.commit()


def scan_for_pb(connection: sqlite3.Connection, cursor: sqlite3.Cursor, mame_dirs: list[core.MAMEDir]) -> None:
    """Scan hi score tables, parse for possible PB entries and insert or update PB table in database."""
    hi_scores = get_games_with_hs(mame_dirs)
    hi2txt_tables = get_hs_tables(hi_scores)
    new_pbs = get_new_pbs(hi2txt_tables, cursor)
    save_pbs(new_pbs, connection, cursor)
