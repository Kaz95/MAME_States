"""MAMEStates core mamestates

This module encompasses the static functions used by the MAMEStates application.
"""
import csv
import json
import logging
import os
import pprint
import sqlite3
import subprocess
import sys

from dataclasses import dataclass, asdict, field
from pathlib import Path


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
class StageSplit:
    label: str
    score: int
    rom_id: int


@dataclass
class PersonalBest:
    hiscore: int
    rom_id: int
    other_fields: dict[str, str | int] = field(default_factory=dict)
    splits: list = field(default_factory=list)


PersonalBests = dict[str, PersonalBest]
"""In-memory representation of the 'personal_bests' table of the database."""



# 1. Setup the basic logging destination
logging.basicConfig(
    filename='app.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# 2. Define the stream router and redirect stdout/stderr
class LogStreamRouter:
    def __init__(self, logger_level):
        self.logger_level = logger_level
    def write(self, message):
        if message.strip():
            logging.log(self.logger_level, message.strip())
    def flush(self):
        pass


# 3. Define and register the global exception hook
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

def turn_on_logging():
    sys.excepthook = handle_exception
    sys.stdout = LogStreamRouter(logging.INFO)
    sys.stderr = LogStreamRouter(logging.ERROR)


def get_abs_path(relative_path: str | Path) -> Path:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    # Get the bundle directory; fallback to the script's parent directory
    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    return base_path / relative_path


def get_mame_version(mame_dir: Path) -> str | None:
    """Retrieve the version for the given path's MAME.exe file."""
    mame_exe = mame_dir / 'mame.exe'
    if mame_exe.is_file():
        results = subprocess.run([mame_exe, '-version'], cwd=mame_dir, capture_output=True, text=True)
        return results.stdout


# TODO Consider if some of these typehints are complex enough to warrant a dataclass or type alias...something.
class MAMEStatesCore:
    """Encapsulates the internal state and logic of the MAMEStates Application."""
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.cursor.row_factory = sqlite3.Row
        self.mame_dirs: list[MAMEDir] = self._get_mame_dirs()
        self.input_files: dict[str, list[str]] = self.get_input_files()
        self.save_states: dict[str, dict[str, list[Path]]] = self.new_get_save_states()
        self.descriptions_and_names: dict[str, str] = self._get_descriptions_and_names()
        self.rom_info: dict[str, RomInfo] = self._get_formatted_rom_info()
        self.pb_info: dict[str, PersonalBest] = self.get_personal_bests()

    ########################
    # Descriptions & Names #
    ########################
    def _get_descriptions_and_names(self) -> dict[str, str]:
        """Construct {rom_description:rom_name} dictionary.

        This dictionary is used as a quick in-memory reference that binds a roms description, to its name.
        The alternative would be querying them as needed.
        """
        sql_statement = """SELECT name, description FROM roms;"""
        self.cursor.execute(sql_statement)
        rows = self.cursor.fetchall()
        descriptions_and_names = {}
        for row in rows:
            descriptions_and_names[row['description']] = row['name']

        return descriptions_and_names

    def rom_description_from_name(self, rom_name: str) -> str:
        """Return the rom description of a given rom name."""
        for rom_description, value in self.descriptions_and_names.items():
            if value == rom_name:
                return rom_description

    ############
    # Rom Info #
    ############
    def _get_formatted_rom_info(self) -> dict[str, RomInfo]:
        """Retrieve and format raw rom info, from the database."""
        raw_rom_info = self._get_raw_rom_info()
        formatted_rom_info = self._serialize_rom_info(raw_rom_info)
        return formatted_rom_info

    @staticmethod
    def _serialize_rom_info(raw_rom_info: list[sqlite3.Row]) -> dict[str, RomInfo]:
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

    def _get_raw_rom_info(self) -> list[sqlite3.Row]:
        """Retrieve all rom information from database and return it raw."""
        sql_statement = "SELECT * FROM roms"
        self.cursor.execute(sql_statement)
        rows = self.cursor.fetchall()
        return rows

    def id_from_description(self, description: str) -> int:
        """Retrieve the corresponding rom_id, for a given rom description, from the database."""
        sql_statement = "SELECT id FROM roms WHERE description = ?"
        self.cursor.execute(sql_statement, (description,))
        row = self.cursor.fetchone()
        rom_id = row['id']
        return rom_id

    #########
    # Paths #
    #########
    def _get_mame_dirs(self) -> list[MAMEDir]:
        """Load paths as strings from database. Convert to Path objects before returning them.

        Prune invalid MAME directories from the database.
        """
        sql_query = """SELECT * FROM paths"""
        self.cursor.execute(sql_query)
        rows = self.cursor.fetchall()
        mame_dirs = []
        for row in rows:
            mame_path = Path(row['path'])
            if not mame_path.is_dir():
                self._delete_mame_dir(row['path'])
                continue
            mame_version = row['version']
            mame_dir = MAMEDir(mame_path, mame_version)
            mame_dirs.append(mame_dir)
        return mame_dirs

    def save_mame_dirs(self) -> None:
        """Format list of MAMEDirs as rows. Insert them into database."""
        sql_statement = """INSERT OR IGNORE INTO paths (path, version) VALUES (:path, :version);"""
        rows = []
        for mame_dir in self.mame_dirs:
            row = asdict(mame_dir)
            # Change Path to str before inserting.
            row['path'] = str(row['path'])
            rows.append(row)

        self.cursor.executemany(sql_statement, rows)
        self.connection.commit()

    def _delete_mame_dir(self, mame_path: str) -> None:
        """Remove a given mame directory from the database."""
        sql_statement = "DELETE FROM paths WHERE path = ?"
        self.cursor.execute(sql_statement, (mame_path,))
        self.connection.commit()

    def get_input_files(self) -> dict[str, list[str]]:
        """Retrieve and return input file names, for each path in the mame_dirs list. File extensions are stripped."""
        all_input_files = {}
        for mame_dir in self.mame_dirs:
            input_file_dir = mame_dir.path / 'inp'
            if input_file_dir.is_dir():
                all_input_files[str(mame_dir.path)] = [input_file.stem for input_file in input_file_dir.iterdir()]
        return all_input_files

    ###############
    # Save States #
    ###############
    @staticmethod
    def _get_roms_with_saves(mame_dir: Path) -> list[str]:
        """Create and return a list of roms that have a save folder in the given MAME file path"""
        rom_names = os.listdir(mame_dir / 'sta')
        return rom_names


    @staticmethod
    def _new_get_save_state_names(roms_with_saves: list[str], mame_dir: Path) -> dict[str, list[Path]]:
        """Return all save files, and their respective roms."""
        save_states = {}
        for rom_name in roms_with_saves:
            if not rom_name:
                continue
            save_state_paths = (mame_dir / 'sta' / rom_name).iterdir()
            save_state_file_paths = [x for x in save_state_paths]
            save_state_file_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            save_states[rom_name] = save_state_file_paths
        return save_states

    def new_get_save_states(self) -> dict[str, dict[str, list[Path]]]:
        """Retrieve and return save state file names, for each path in the mame_dirs list. File extensions are stripped."""
        all_save_state_paths = {}
        for mame_dir in self.mame_dirs:
            roms_with_saves = self._get_roms_with_saves(mame_dir.path)
            save_state_names = self._new_get_save_state_names(roms_with_saves, mame_dir.path)
            all_save_state_paths[str(mame_dir.path)] = save_state_names

        return all_save_state_paths

    ##################
    # Personal Bests #
    ##################
    def get_personal_bests(self) -> PersonalBests:
        """Load, and format, all personal best information from the database. Keyed to rom description."""
        pb_info = {}

        pb_query = """SELECT roms.description, personal_bests.hiscore, personal_bests.other_fields, 
        personal_bests.rom_id FROM 'roms' JOIN 'personal_bests' ON roms.id = personal_bests.rom_id"""

        splits_query = """SELECT splits.label, splits.score, splits.'index', roms.description, splits.rom_id
            FROM 'splits' JOIN 'roms' ON splits.rom_id = roms.id 
            ORDER BY roms.description, splits.'index'"""

        self.cursor.execute(pb_query)
        personal_bests = self.cursor.fetchall()

        for pb in personal_bests:
            if pb['other_fields']:
                other_fields = json.loads(pb['other_fields'])
                pb_info[pb['description']] = PersonalBest(pb['hiscore'], pb['rom_id'], other_fields)
            else:
                pb_info[pb['description']] = PersonalBest(pb['hiscore'], pb['rom_id'])

        self.cursor.execute(splits_query)
        splits = self.cursor.fetchall()
        for row in splits:
            some_split = StageSplit(row['label'], row['score'], row['rom_id'])
            pb_info[row['description']].splits.append(some_split)

        return pb_info

    def save_pb_to_database(self) -> None:
        """Update database with provided personal best and split information.

        Rows are added if they do not exist, and updated otherwise.
        """
        pb_insert = ("INSERT INTO personal_bests VALUES (:id, :hiscore, :other_fields, :rom_id) "
                     "ON CONFLICT(rom_id) "
                     "DO UPDATE SET hiscore = excluded.hiscore, other_fields = excluded.other_fields")

        splits_insert = ("INSERT INTO splits (label, score, 'index', rom_id) VALUES (:label, :score, :index, :rom_id) "
                         "ON CONFLICT(label, rom_id) "
                         "DO UPDATE SET label = excluded.label, score = excluded.score, 'index' = excluded.'index'")

        pb_rows = self._collate_pb_rows()
        split_rows = self._collate_split_rows()

        self.cursor.executemany(pb_insert, pb_rows)
        self.cursor.executemany(splits_insert, split_rows)

        self.connection.commit()

    def delete_personal_best(self, rom_description: str) -> None:
        """Delete personal best data from database, for a given rom."""
        sql_statement = "DELETE FROM personal_bests WHERE rom_id = ?"
        rom_id = self.id_from_description(rom_description)
        self.cursor.execute(sql_statement, (rom_id,))
        self.connection.commit()

    def delete_splits(self, rom_description: str) -> None:
        """Delete all 'splits' data from database, for a given rom."""
        sql_statement = "DELETE FROM splits WHERE rom_id = ?"
        rom_id = self.id_from_description(rom_description)
        self.cursor.execute(sql_statement, (rom_id,))
        self.connection.commit()

    def delete_split(self, rom_description: str, split_label: str) -> None:
        """Delete a single split from the database. Rom id and split label text are used as unique identifier."""
        sql_statement = "DELETE FROM splits WHERE rom_id = ? AND label = ?"
        rom_id = self.id_from_description(rom_description)
        self.cursor.execute(sql_statement, (rom_id, split_label))
        self.connection.commit()


    def _collate_pb_rows(self) -> list[dict]:
        """Serialize personal best hiscore and related information into rows for database insertion."""
        rows = []
        for rom_description in self.pb_info:
            pb = self.pb_info[rom_description]
            other_fields = pb.other_fields
            other_fields = json.dumps(other_fields)
            row = {'id': None, 'hiscore': pb.hiscore, 'other_fields': other_fields, 'rom_id': pb.rom_id}
            rows.append(row)
        return rows

    def _collate_split_rows(self) -> list:
        """Serialize splits information into rows for database insertion.

        Split order is preserved by using the splits current position in its perspective splits list.
        """
        rows = []
        for rom_description in self.pb_info:
            pb = self.pb_info[rom_description]

            for split in pb.splits:
                index = pb.splits.index(split)
                split = asdict(split)
                split['index'] = index
                rows.append(split)

        return rows

    def export_sqlite_to_csv(self, table_name, output_file):
        # Execute a query to select all data from the table
        self.cursor.execute(f"SELECT * FROM {table_name}")

        # Extract column names (headers) from cursor.description
        headers = [description[0] for description in self.cursor.description]

        # Write the headers and data to the CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)  # Write header row
            writer.writerows(self.cursor)  # Write data rows directly from cursor



    def new_remove_invalid_mame_dir(self, mame_path: str) -> None:
        """Remove MAME directory and all related info(saves, inps, ect) from in-memory datastructures and DB"""
        for mame_dir in self.mame_dirs:
            if mame_path == str(mame_dir.path):
                self.mame_dirs.remove(mame_dir)
        del self.save_states[mame_path]
        del self.input_files[mame_path]
        self._delete_mame_dir(mame_path)
