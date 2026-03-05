"""MAMEStates core logic

This module encompasses the static functions used by the MAMEStates application.
"""
import json
import os
import pprint
import sqlite3
import subprocess
import sys

from dataclasses import dataclass, asdict, field
from pathlib import Path

import zipfile
import xmltodict


@dataclass(frozen=True)
class MAMEDir:
    path: Path
    version: str


@dataclass(frozen=True)
class RomInfo:
    name: str
    description: str
    manufacturer: str
    year: str
    parent: str
    hres: int
    vres: int
    rotate: int
    refresh: float
    video: str
    sound: str


@dataclass
class Split:
    label: str
    score: int


@dataclass
class PersonalBest:
    score: int
    other_fields: dict[str, str | int] = field(default_factory=dict)
    splits: list = field(default_factory=list)


PersonalBests = dict[str, PersonalBest]
"""In-memory representation of the 'personal_bests' table of the database."""


def resource_path(relative_path: str | Path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    # Get the bundle directory; fallback to the script's parent directory
    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))

    return base_path / relative_path

class MAMEStatesCore:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.cursor.row_factory = sqlite3.Row
        self.mame_dirs = self.get_mame_dirs()
        self.input_files = self.get_all_input_files()
        self.roms_with_saves = self.get_all_roms_with_saves()

    def get_mame_dirs(self) -> list[MAMEDir]:
        """Load paths as strings from database. Convert to Path objects before returning them."""
        sql_query = """SELECT * FROM paths"""
        self.cursor.execute(sql_query)
        raw_results = self.cursor.fetchall()
        mame_dirs = []
        for entry in raw_results:
            mame_path = Path(entry['path'])
            mame_version = entry['version']
            mame_dir = MAMEDir(mame_path, mame_version)
            mame_dirs.append(mame_dir)
        return mame_dirs

    def get_all_input_files(self) -> dict[MAMEDir, list[str]]:
        """Retrieve and return input file names, for each path in the given list. File extensions are stripped."""
        all_input_files = {}
        for mame_dir in self.mame_dirs:
            input_file_dir = mame_dir.path / 'inp'
            if input_file_dir.is_dir():
                all_input_files[mame_dir] = [input_file.stem for input_file in input_file_dir.iterdir()]
        return all_input_files

    def get_all_roms_with_saves(self) -> dict[MAMEDir, dict[str, list[str]]]:
        """Retrieve and return save state file names, for each path in the given list. File extensions are stripped."""
        all_save_state_names = {}
        for mame_dir in self.mame_dirs:
            roms_with_saves = get_roms_with_saves(mame_dir.path)
            save_state_names = get_save_names(roms_with_saves, mame_dir.path)
            all_save_state_names[mame_dir] = save_state_names

        return all_save_state_names

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
        save_state_file_names = os.listdir(mame_dir / 'sta' / rom)

        for name in save_state_file_names:
            save_index = save_state_file_names.index(name)
            name, _ = os.path.splitext(name)
            save_state_file_names[save_index] = name

        save_states[rom] = save_state_file_names
    return save_states


def get_all_roms_with_saves(mame_dirs: list[MAMEDir]) -> dict[MAMEDir, dict[str, list[str]]]:
    """Retrieve and return save state file names, for each path in the given list. File extensions are stripped."""
    all_save_state_names = {}
    for mame_dir in mame_dirs:
        roms_with_saves = get_roms_with_saves(mame_dir.path)
        save_state_names = get_save_names(roms_with_saves, mame_dir.path)
        all_save_state_names[mame_dir] = save_state_names

    return all_save_state_names


# TODO Consider generator
def rom_description_from_name(description_db: dict[str, str], rom_name: str) -> str:
    """Return the full name of a given rom"""
    for key, value in description_db.items():
        if value == rom_name:
            rom_description = key
            return rom_description


#########
# Paths #
#########

# TODO This wipes out manually added version #s until I sort that out.
def save_mame_dirs(connection: sqlite3.Connection, cursor: sqlite3.Cursor, mame_dirs: list[MAMEDir],
                   version=None) -> None:
    """Format list of paths as rows. Insert them into database. """
    sql_statement = """INSERT OR IGNORE INTO paths (path, version) VALUES (:path, :version);"""
    rows = []
    for mame_dir in mame_dirs:
        row = asdict(mame_dir)
        # Change Path to str before inserting.
        row['path'] = str(row['path'])
        print(row)
        rows.append(row)

    cursor.executemany(sql_statement, rows)
    connection.commit()


##################
# Personal Bests #
##################
def get_personal_bests(cursor: sqlite3.Cursor) -> PersonalBests:
    """Load and format all personal best information from the database. Keyed to rom description."""
    pb_info = {}

    pb_query = """SELECT roms.description, personal_bests.highscore, personal_bests.other_fields 
    FROM 'roms' JOIN 'personal_bests' ON roms.id = personal_bests.rom_id"""

    splits_query = """SELECT splits.label, splits.score, splits.'index', roms.description
        FROM 'splits' JOIN 'roms' ON splits.rom_id = roms.id 
        ORDER BY roms.description, splits.'index'"""

    cursor.execute(pb_query)
    personal_bests = cursor.fetchall()

    for pb in personal_bests:
        if pb['other_fields']:
            other_fields = json.loads(pb[2])
            pb_info[pb['description']] = PersonalBest(pb['highscore'], other_fields)
        else:
            pb_info[pb['description']] = PersonalBest(pb['highscore'])

    cursor.execute(splits_query)
    splits = cursor.fetchall()
    for row in splits:
        some_split = Split(row['label'], row['score'])
        pb_info[row['description']].splits.append(some_split)

    return pb_info


def save_pb_to_database(connection: sqlite3.Connection, cursor: sqlite3.Cursor, pb_info: PersonalBests) -> None:
    """Update database with provided personal best and split information.

       Rows are added if they do not exist, and updated otherwise.
       """
    pb_insert = ("INSERT INTO personal_bests VALUES (?, ?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = "
                 "excluded.highscore, other_fields = excluded.other_fields")
    splits_insert = (
        "INSERT INTO splits (label, score, 'index', rom_id) VALUES (:label, :score, :index, :rom_id) ON CONFLICT(label, rom_id) DO UPDATE SET label = excluded.label, "
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


def get_raw_rom_info(cursor: sqlite3.Cursor) -> list[sqlite3.Row]:
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
    for mame_dir in pb_info:
        pb = pb_info[mame_dir]
        rom_id = id_from_description(mame_dir, cursor)
        highscore = pb.score
        other_fields = pb.other_fields
        other_fields = json.dumps(other_fields)
        row = (None, highscore, other_fields, rom_id)
        rows.append(row)
    return rows


def collate_split_rows(cursor: sqlite3.Cursor, pb_info: PersonalBests) -> list:
    """Serialize splits information into rows for database insertion.

    Split order is preserved by using the splits current position in its perspective splits list.
    """
    rows = []
    for pb in pb_info:
        pb_dict = pb_info[pb]
        splits = pb_dict.splits
        for split in splits:
            index = splits.index(split)
            split = asdict(split)
            split['index'] = index
            split['rom_id'] = id_from_description(pb, cursor)
            rows.append(split)

    return rows


def get_descriptions_and_names(cursor: sqlite3.Cursor) -> dict[str, str]:
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

def serialize_rom_info(raw_rom_info: list[sqlite3.Row]) -> dict[str, RomInfo]:
    """Format raw rom info, from database, into in-memory representation."""
    formatted_rom_info = {}

    for row in raw_rom_info:
        rom_info = RomInfo(row['name'],
                           row['description'],
                           row['manufacturer'],
                           row['year'],
                           row['parent'],
                           row['hres'],
                           row['vres'],
                           row['rotate'],
                           row['refresh'],
                           row['video'],
                           row['sound'])
        formatted_rom_info[rom_info.description] = rom_info

    return formatted_rom_info

def get_formatted_rom_info(cursor: sqlite3.Cursor) -> dict[str, RomInfo]:
    """Retrieve and format raw rom info, from the database."""
    raw_rom_info = get_raw_rom_info(cursor)
    formatted_rom_info = serialize_rom_info(raw_rom_info)
    return formatted_rom_info


def has_xml(rom_name: str) -> bool:
    """Check if a given rom has an XML file, and is therefore compatible with 'hi2txt'."""
    zip_path = resource_path(r'.\hi2txt\hi2txt.zip')
    with zipfile.ZipFile(zip_path, 'r') as zip_obj:
        xml_strings = zip_obj.namelist()
        xml_paths = [Path(file_name) for file_name in xml_strings]
        xml_names = [file_name.stem for file_name in xml_paths]
        if rom_name in xml_names:
            return True
        else:
            return False


# TODO Maybe consider how this will be used. Might want to make this method to access self.mame_paths.
def get_games_with_hs(mame_dirs: list[MAMEDir]) -> dict[str, list[Path]]:
    hi2txt_compatible_hi_scores: dict[str, list[Path]] = {}
    for mame_dir in mame_dirs:
        hiscore_dir = mame_dir.path / 'hiscore'
        hiscore_files = list(hiscore_dir.glob('*.hi'))
        hi2txt_compatible_hi_scores[str(mame_dir)] = hiscore_files

    zip_path = resource_path(r'.\hi2txt\hi2txt.zip')
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
            try:
                results = subprocess.run([resource_path(r'.\hi2txt\hi2txt.exe'), '-r', f'{file}'],
                                         cwd=resource_path(r'.\hi2txt'), capture_output=True, text=True,
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
def get_new_pbs(hi2txt_tables: dict[str, dict[str, str]]) -> PersonalBests:
    """Scan for new, possible, personal bests. Compares current Hi Score tables to game defaults."""
    defaults_xml = Path(resource_path(r'.\hi2txt\hi2txt_doc\hi2txt_defaults'))
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
                                        pb = PersonalBest(int(some_dic.pop('SCORE')), some_dic)
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
                                    pb = PersonalBest(int(some_dic.pop('SCORE')), some_dic)
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
                                    pb = PersonalBest(int(some_dic.pop('SCORE')), some_dic)
                                    new_pbs[rom_name] = pb

                                    pprint.pp(some_dic)
                                    break
    return new_pbs


def prepare_pb_for_db(new_pb: dict[str, str], rom_name: str) -> PersonalBests:
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
    new_pb = PersonalBest(int(pb.pop('SCORE')), pb)
    pprint.pp(pb)
    all_pbs[rom_name] = new_pb
    return all_pbs


def save_pbs(new_pbs: PersonalBests, connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
    """Insert or update new PB entries into database, if new PB has a higher score."""
    for rom_name in new_pbs:
        pb = new_pbs[rom_name]
        score = pb.score
        other_fields = json.dumps(pb.other_fields)
        print(f'here: {rom_name}')
        rom_id = id_from_rom_name(rom_name, cursor)

        row = (score, other_fields, rom_id)
        sql_statement = (
            "INSERT INTO personal_bests (highscore, other_fields, rom_id) VALUES (?, ?, ?) ON CONFLICT(rom_id) DO UPDATE SET highscore = "
            "excluded.highscore, other_fields = excluded.other_fields WHERE excluded.highscore > highscore")
        cursor.execute(sql_statement, row)
    connection.commit()


def scan_for_pb(connection: sqlite3.Connection, cursor: sqlite3.Cursor, mame_dirs: list[MAMEDir]) -> None:
    """Scan hi score tables, parse for possible PB entries and insert or update PB table in database."""
    hi_scores = get_games_with_hs(mame_dirs)
    hi2txt_tables = get_hs_tables(hi_scores)
    new_pbs = get_new_pbs(hi2txt_tables)
    save_pbs(new_pbs, connection, cursor)


# TODO Temp fix after I realized inps need version in name.
def get_mame_version(mame_dir: Path):
    mame_exe = mame_dir / 'mame.exe'
    if mame_exe.is_file():
        results = subprocess.run([mame_exe, '-version'], cwd=mame_dir, capture_output=True, text=True)
        return results.stdout
