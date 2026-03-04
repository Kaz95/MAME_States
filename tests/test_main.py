
from logic.main import resource_path, get_roms_with_saves
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

def test_get_all_input_files():
    pass