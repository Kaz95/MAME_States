import os
import pprint

import pytest

from logic.main import resource_path, get_roms_with_saves, get_all_input_files, MAMEDir, get_all_roms_with_saves
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
    mame_dirs = ['mame', 'wolfmame', 'groovymame']
    sub_dirs = ['inp', 'sta']
    for mame_dir in mame_dirs:
        (base_dir / mame_dir).mkdir()
        for sub_dir in sub_dirs:
            (base_dir / mame_dir / sub_dir).mkdir()
            for _ in range(3):
                (base_dir / mame_dir / sub_dir / f'{mame_dir}_{sub_dir + str(_)}.{sub_dir}').touch()
    return base_dir


def test_get_all_input_files(mock_file_system):
    mame_dirs = [MAMEDir(p, '.069') for p in mock_file_system.iterdir()]
    all_input_files = get_all_input_files(mame_dirs)
    pprint.pp(all_input_files)
    assert mame_dirs == list(all_input_files.keys())
    for mame_dir in mame_dirs:
        for _ in range(3):
            assert all_input_files[mame_dir][_] == f'{mame_dir.path.name}_{'inp' + str(_)}'
