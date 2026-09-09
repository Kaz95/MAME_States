"""MAMEStates Core unit tests."""
import sqlite3
from unittest.mock import MagicMock, patch
import subprocess

import pytest

from mamestates.core import get_mame_version, MAMEStatesCore, RomInfo


def test_get_mame_version_returns_none_when_no_mame_exe(tmp_path):
    result = get_mame_version(tmp_path)
    assert result is None


def test_get_mame_version_returns_stdout_when_mame_exe(tmp_path):
    with patch('mamestates.core.subprocess.run') as mock_run:
        # Arrange: create a fake mame.exe so is_file() is True
        mame_exe = tmp_path / 'mame.exe'
        mame_exe.touch()

        mock_run.return_value = MagicMock(stdout='mame 0.260\n', stderr='')

        result = get_mame_version(tmp_path)

        assert result == 'mame 0.260\n'


def test_get_mame_version_calls_subprocess_with_correct_arguments(tmp_path):
    with patch('mamestates.core.subprocess.run') as mock_run:
        mame_exe = tmp_path / "mame.exe"
        mame_exe.touch()
        mock_run.return_value = MagicMock(stdout="", stderr="")

        get_mame_version(tmp_path)

        mock_run.assert_called_once_with(
            [mame_exe, "-version"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


@pytest.fixture
def sqlite_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_init_sets_connection_and_row_factory(sqlite_conn):
    conn = sqlite_conn
    with patch.object(MAMEStatesCore, "_get_mame_dirs", return_value=["dir1"]), \
            patch.object(MAMEStatesCore, "get_input_files", return_value={"a": ["x"]}), \
            patch.object(MAMEStatesCore, "get_save_states", return_value={"a": {"b": []}}), \
            patch.object(MAMEStatesCore, "_get_descriptions_and_names", return_value={"desc": "name"}), \
            patch.object(MAMEStatesCore, "_get_formatted_rom_info", return_value={"desc": "rom"}), \
            patch.object(MAMEStatesCore, "get_personal_bests", return_value={"desc": "pb"}):
        core = MAMEStatesCore(conn)

    assert core.connection is conn
    assert core.cursor.row_factory is sqlite3.Row
    assert core.mame_dirs == ["dir1"]
    assert core.input_files == {"a": ["x"]}
    assert core.save_states == {"a": {"b": []}}
    assert core.descriptions_and_names == {"desc": "name"}
    assert core.rom_info == {"desc": "rom"}
    assert core.pb_info == {"desc": "pb"}


@pytest.fixture
def core_with_roms():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("CREATE TABLE roms (name TEXT, description TEXT)")
    cur.executemany(
        "INSERT INTO roms (name, description) VALUES (?, ?)",
        [
            ("pacman", "Pac-Man"),
            ("galaga", "Galaga"),
        ],
    )
    conn.commit()

    core = MAMEStatesCore.__new__(MAMEStatesCore)
    core.connection = conn
    core.cursor = conn.cursor()
    core.cursor.row_factory = sqlite3.Row
    return core


def test_get_descriptions_and_names_returns_expected_mapping(core_with_roms):
    result = core_with_roms._get_descriptions_and_names()

    assert result == {
        "Pac-Man": "pacman",
        "Galaga": "galaga",
    }


def test_get_descriptions_and_names_empty_db_returns_empty_dict():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("CREATE TABLE roms (name TEXT, description TEXT)")
    conn.commit()

    core = MAMEStatesCore.__new__(MAMEStatesCore)
    core.connection = conn
    core.cursor = conn.cursor()
    core.cursor.row_factory = sqlite3.Row

    assert core._get_descriptions_and_names() == {}


def test_rom_description_from_name_returns_matching_description():
    core = MAMEStatesCore.__new__(MAMEStatesCore)
    core.descriptions_and_names = {
        "Pac-Man": "pacman",
        "Galaga": "galaga",
    }

    result = core.rom_description_from_name("galaga")

    assert result == "Galaga"


def test_rom_description_from_name_returns_none_when_missing():
    core = MAMEStatesCore.__new__(MAMEStatesCore)
    core.descriptions_and_names = {
        "Pac-Man": "pacman",
    }

    result = core.rom_description_from_name("mario")

    assert result is None


def test_serialize_rom_info_with_single_row():
    rows = [
        {
            "name": "pacman",
            "description": "Pac-Man",
            "manufacturer": "Namco",
            "year": "1980",
            "parent": "",
            "hres": 224,
            "vres": 288,
            "rotate": 0,
            "refresh": 60.0,
            "video": "Raster",
            "sound": "Mono",
        }
    ]

    result = MAMEStatesCore._serialize_rom_info(rows)

    assert result == {
        "Pac-Man": RomInfo(
            name="pacman",
            description="Pac-Man",
            manufacturer="Namco",
            year="1980",
            parent="",
            hres=224,
            vres=288,
            rotate=0,
            refresh=60.0,
            video="Raster",
            sound="Mono",
        )
    }


def test_serialize_rom_info_with_empty_list():
    result = MAMEStatesCore._serialize_rom_info([])

    assert result == {}


def test_serialize_rom_info_with_multiple_rows():
    rows = [
        {
            "name": "pacman",
            "description": "Pac-Man",
            "manufacturer": "Namco",
            "year": "1980",
            "parent": "",
            "hres": 224,
            "vres": 288,
            "rotate": 0,
            "refresh": 60.0,
            "video": "Raster",
            "sound": "Mono",
        },
        {
            "name": "galaga",
            "description": "Galaga",
            "manufacturer": "Namco",
            "year": "1981",
            "parent": "",
            "hres": 224,
            "vres": 256,
            "rotate": 0,
            "refresh": 60.0,
            "video": "Raster",
            "sound": "Mono",
        },
    ]

    result = MAMEStatesCore._serialize_rom_info(rows)

    assert set(result.keys()) == {"Pac-Man", "Galaga"}
    assert result["Pac-Man"].name == "pacman"
    assert result["Galaga"].manufacturer == "Namco"

