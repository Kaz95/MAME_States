import zipfile

from logic.core import resource_path
from pathlib import Path

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