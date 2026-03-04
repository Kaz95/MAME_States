
from logic.main import resource_path
from pathlib import Path
import sys




def test_resource_path_parent_dir_with_str_input():
    assert resource_path('abc') == Path(f'{Path(__file__).parent.parent}/abc')

def test_resource_path_parent_dir_with_path_input():
    assert resource_path(Path('abc')) == Path(f'{Path(__file__).parent.parent}/abc')

def test_resource_path_pyinstaller_archive_with_str_input():
    sys._MEIPASS = r'S:\ome\base\path'
    assert resource_path('abc') == Path('S:/ome/base/path/abc')

def test_resource_path_pyinstaller_archive_with_path_input():
    sys._MEIPASS = Path(r'S:\ome\base\path')
    assert resource_path('abc') == Path('S:/ome/base/path/abc')

