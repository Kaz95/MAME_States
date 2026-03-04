import os
import pprint
import sqlite3

import pytest

from logic.main import resource_path, get_roms_with_saves, get_all_input_files, MAMEDir, get_all_roms_with_saves, \
    rom_description_from_name, get_mame_dirs
from pathlib import Path
import sys
from logic import main


def test_resource_path_parent_dir_with_str_input():
    assert resource_path('abc') == Path(f'{Path(__file__).parent.parent}/abc')


def test_resource_path_parent_dir_with_path_input():
    assert resource_path(Path('abc')) == Path(f'{Path(__file__).parent.parent}/abc')


def test_resource_path_pyinstaller_archive_with_str_input(monkeypatch):
    monkeypatch.setattr(sys, '_MEIPASS', 'S:/ome/base/path', raising=False)
    assert resource_path('abc') == Path('S:/ome/base/path/abc')


def test_resource_path_pyinstaller_archive_with_path_input(monkeypatch):
    monkeypatch.setattr(sys, '_MEIPASS', 'S:/ome/base/path', raising=False)
    assert resource_path('abc') == Path('S:/ome/base/path/abc')


def test_get_roms_with_saves(mocker):
    mock_files = ['file1.sta', 'file2.sta', 'file3.sta']
    mocker.patch('logic.main.os.listdir', return_value=mock_files)
    some_dir = Path('abc')

    assert get_roms_with_saves(some_dir) == mock_files
    main.os.listdir.assert_called_once_with(some_dir / 'sta')


# FIXME Need to add rom subdirs, before adding .sta files to mirror actual file system.
@pytest.fixture(scope="session")
def mock_file_system(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp('file_system')
    mame_dir_names = ['mame', 'wolfmame', 'groovymame']
    sub_dir_names = ['inp', 'sta']
    for mame_dir_name in mame_dir_names:
        mame_dir = (base_dir / mame_dir_name)
        mame_dir.mkdir()
        for sub_dir_name in sub_dir_names:
            sub_dir = (base_dir / mame_dir / sub_dir_name)
            sub_dir.mkdir()
            if sub_dir_name == 'sta':
                for _ in range(3):
                    rom_dir = sub_dir / f'rom{_}'
                    rom_dir.mkdir()
                    (rom_dir / f'{mame_dir_name}_{sub_dir_name + str(_)}.{sub_dir_name}').touch()
            else:
                for _ in range(3):
                    (sub_dir / f'{mame_dir_name}_{sub_dir_name + str(_)}.{sub_dir_name}').touch()
    return base_dir


def test_get_all_input_files(mock_file_system):
    mame_dirs = [MAMEDir(p, '.069') for p in mock_file_system.iterdir()]
    all_input_files = get_all_input_files(mame_dirs)

    assert mame_dirs == list(all_input_files.keys())
    for mame_dir in mame_dirs:
        for _ in range(3):
            assert all_input_files[mame_dir][_] == f'{mame_dir.path.name}_{'inp' + str(_)}'

def test_get_all_roms_with_saves(mock_file_system):
    mame_dirs = [MAMEDir(p, '.069') for p in mock_file_system.iterdir()]
    all_save_states = get_all_roms_with_saves(mame_dirs)

    assert mame_dirs == list(all_save_states.keys())
    for mame_dir in mame_dirs:
        for _ in range(3):
            assert all_save_states[mame_dir][f'rom{_}'][0] == f'{mame_dir.path.name}_{'sta' + str(_)}'

def test_rom_description_from_name():
    description_db = {'DoDonPachi II - Bee Storm': 'ddp2', 'Libble Rabble': 'liblrabl', 'Final Fight': 'ffight'}
    assert rom_description_from_name(description_db, 'ddp2') == 'DoDonPachi II - Bee Storm'
    assert rom_description_from_name(description_db, 'DDP2') != 'DoDonPachi II - Bee Storm'

def test_get_mame_dirs(mocker):

    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchall.return_value = [{'path': r'P:\ath\to\a\mame\dir', 'version': '0.69'},
                                         {'path': r'A:\nother\path\to\a\dir', 'version': '0.42'}]


    assert get_mame_dirs(mock_cursor) == [MAMEDir(Path(r'P:\ath\to\a\mame\dir'), '0.69'),
                                          MAMEDir(Path(r'A:\nother\path\to\a\dir'), '0.42')]

    mock_cursor.execute.assert_called_once_with("""SELECT * FROM paths""")