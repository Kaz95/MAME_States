"""MAMEStates Core unit tests."""

from unittest.mock import MagicMock, patch
import subprocess
from mamestates.core import get_mame_version


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
