import json
import pprint
import sqlite3
import subprocess
from pathlib import Path
from enum import Enum

import zipfile
import xmltodict

import core


class Hi2TxtError(Enum):
    INCOMPATIBLE_TABLE_SCHEMA = 1


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


def _get_games_with_hs(mame_dirs: list[core.MAMEDir]) -> dict[str, list[Path]]:
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


def _get_hs_tables(hi2txt_compatible_hi_scores: dict[str, list[Path]]) -> dict[str, dict[str, str]]:
    """Retrieve raw hi2txt leaderboard table output for compatible games with .hi file."""
    hi2txt_tables: dict[str, dict[str, str]] = {}
    for mame_dir in hi2txt_compatible_hi_scores:
        hi2txt_tables[mame_dir] = {}
        hiscore_files = hi2txt_compatible_hi_scores[mame_dir]
        for file in hiscore_files:
            print(f'Score is: {file}')
            results = subprocess.run([core.get_abs_path(r'.\hi2txt\hi2txt.exe'), '-r', f'{file}'],
                                     cwd=core.get_abs_path(r'.\hi2txt'), capture_output=True, text=True,
                                     check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
            hi2txt_tables[mame_dir][f'{file.stem}'] = results.stdout
    return hi2txt_tables


def _format_table(raw_hi2txt_table: str) -> dict[str, list | str]:
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
            table['row'] = leaderboard_lines
            return table
        else:
            columns = leaderboard_lines.pop(0)
            table['col'] = columns
            table['row'] = leaderboard_lines
            return table


def get_new_pb(old_raw_table: str, new_raw_table: str) -> dict[str, str] | Hi2TxtError | None:
    """Compare two raw hi2txt tables to look for new, possible, personal best."""
    old_table = _format_table(old_raw_table)
    new_table = _format_table(new_raw_table)
    pprint.pp(old_table)
    pprint.pp(new_table)
    old_columns = old_table['col']
    new_columns = new_table['col']
    old_leaderboard = old_table.get('name')
    new_leaderboard = new_table.get('name')
    old_rows = old_table['row']
    new_rows = new_table['row']
    new_pb = {}

    if old_columns != new_columns or old_leaderboard != new_leaderboard:
        return Hi2TxtError.INCOMPATIBLE_TABLE_SCHEMA

    for index, line in enumerate(new_rows):
        if line != old_rows[index]:
            new_pb['col'] = new_columns
            new_pb['row'] = line
            if new_leaderboard:
                new_pb['name'] = new_leaderboard
            return new_pb


def _get_default_tables(rom_name: str) -> dict:
    """Retrieve the default hiscore table for a particular rom. Convert to python dict and return."""
    defaults_xml = Path(core.get_abs_path(r'.\hi2txt\hi2txt_doc\hi2txt_defaults'))
    with open(defaults_xml / f'{rom_name}.xml', 'r') as xml_file:
        xml_data = xml_file.read()
        data_dict = xmltodict.parse(xml_data)
        default_tables = data_dict['hi2txt']['table']
        return default_tables


def _serialize_hi2txt_to_pb(line: str, columns: str, rom_name: str, cursor: sqlite3.Cursor) -> core.PersonalBest:
    """Serialize a single hi2txt line into a PersonalBest object."""
    temp_pb = {}
    for index, section in enumerate(line.split('|')):
        temp_pb[columns.split('|')[index]] = section
    temp_pb.pop('NAME', None)
    temp_pb.pop('RANK', None)
    rom_id = _id_from_rom_name(rom_name, cursor)
    pb = core.PersonalBest(int(temp_pb.pop('SCORE')), rom_id, temp_pb)
    return pb


def _parse_leaderboard_lines(leaderboard_lines: list, default_table: dict, columns: str, rom_name: str,
                             cursor: sqlite3.Cursor):
    """Parse a set of hi2txt lines and compare them against the default state of a roms hiscore table.

    If a discrepancy is found, it is serialized into a PersonalBest object and returned.
    """
    for index, line in enumerate(leaderboard_lines):
        if isinstance(default_table['row'], list) is True:
            if line.split('|') != default_table['row'][index]['cell']:
                pb = _serialize_hi2txt_to_pb(line, columns, rom_name, cursor)
                return pb
        else:
            if line.split('|') != default_table['row']['cell']:
                pb = _serialize_hi2txt_to_pb(line, columns, rom_name, cursor)
                return pb


def _get_new_pbs(hi2txt_tables: dict[str, dict[str, str]], cursor: sqlite3.Cursor) -> core.PersonalBests:
    """Scan for new, possible, personal bests. Compares current Hi Score tables to game defaults."""
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
                    default_tables = _get_default_tables(rom_name)

                    for table in default_tables:
                        if table['@id'] == leaderboard_name:
                            default_table = table
                            leaderboard_lines = [line for line in leaderboard_lines if line]
                            new_pb = _parse_leaderboard_lines(leaderboard_lines, default_table, columns, rom_name,
                                                              cursor)
                            if new_pb:
                                new_pbs[rom_name] = new_pb

                else:
                    columns = leaderboard_lines.pop(0)
                    default_table = _get_default_tables(rom_name)

                    leaderboard_lines = [line for line in leaderboard_lines if line]
                    new_pb = _parse_leaderboard_lines(leaderboard_lines, default_table, columns, rom_name, cursor)
                    if new_pb:
                        new_pbs[rom_name] = new_pb

    return new_pbs


def _id_from_rom_name(name: str, cursor) -> int:
    """Retrieve the corresponding rom_id, for a given rom name, from the database."""
    sql_statement = "SELECT id FROM roms WHERE name = ?"
    cursor.execute(sql_statement, (name,))
    row = cursor.fetchone()
    rom_id = row['id']
    return rom_id


def save_pb(new_pb: dict[str, str], rom_name: str, connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Insert or update new PB entry into database, if new PB has a higher score."""
    new_pb = _serialize_hi2txt_to_pb(new_pb['row'], new_pb['col'], rom_name, cursor)
    other_fields = json.dumps(new_pb.other_fields)
    rom_id = _id_from_rom_name(rom_name, cursor)

    row = (new_pb.hiscore, other_fields, rom_id)
    sql_statement = (
        "INSERT INTO personal_bests (hiscore, other_fields, rom_id) VALUES (?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET hiscore = "
        "excluded.hiscore, other_fields = excluded.other_fields WHERE excluded.hiscore > hiscore")
    cursor.execute(sql_statement, row)
    connection.commit()


def _save_pbs(new_pbs: core.PersonalBests, connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Insert or update new PB entries into database, if new PB has a higher score."""
    for rom_name in new_pbs:
        pb = new_pbs[rom_name]
        other_fields = json.dumps(pb.other_fields)
        rom_id = _id_from_rom_name(rom_name, cursor)

        row = (pb.hiscore, other_fields, rom_id)
        sql_statement = (
            "INSERT INTO personal_bests (hiscore, other_fields, rom_id) VALUES (?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET hiscore = "
            "excluded.hiscore, other_fields = excluded.other_fields WHERE excluded.hiscore > hiscore")
        cursor.execute(sql_statement, row)
    connection.commit()


def scan_for_pb(connection: sqlite3.Connection, cursor: sqlite3.Cursor, mame_dirs: list[core.MAMEDir]) -> None:
    """Scan hi score tables, parse for possible PB entries and insert or update PB table in database."""
    hi_scores = _get_games_with_hs(mame_dirs)
    hi2txt_tables = _get_hs_tables(hi_scores)
    new_pbs = _get_new_pbs(hi2txt_tables, cursor)
    _save_pbs(new_pbs, connection, cursor)
