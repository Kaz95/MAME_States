"""MAMEStates custom Pyqt6 widgets

This module houses all pyqt6 widgets that have been subclassed and extended.
"""
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QRegularExpression, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIntValidator, QRegularExpressionValidator, QCloseEvent
from PyQt6.QtWidgets import QLabel, QLineEdit, QListWidget, QHBoxLayout, QWidget, QStyledItemDelegate, QTextEdit, \
    QVBoxLayout, QPushButton, QDialog, QProgressBar, QMessageBox, QTabWidget, QListWidgetItem, QDialogButtonBox, \
    QTreeWidget

import hi2txt_wrapper, core


######################
#   Save State Page  #
######################
class MAMEThread(QThread):
    """Subclass and extend the QThread class of the PyQt6.QtCore module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used to spawn a MAME subprocess on a new thread. A new thread is needed to avoid blocking while waiting for return.
    Subprocess output, errors, and return code are captured and emitted before thread dies.
    """
    mame_exited: pyqtSignal = pyqtSignal(dict)
    """Custom 'finished' signal. Emitted when 'run' method finishes."""

    def __init__(self, mame_exe: Path, rom_name: str, mame_dir: Path, record_input=False, playback_input=False,
                 input_file_name=None) -> None:
        super().__init__()
        self.playback_input = playback_input
        self.record_input = record_input
        self.input_file_name = input_file_name
        self.mame_exe: Path = mame_exe
        """Path object pointing to MAME.exe file."""

        self.rom_name: str = rom_name
        """Name of the rom being run."""

        self.mame_dir: Path = mame_dir
        """MAME directory containing the MAME.exe that will be used to launch rom"""

    def run(self) -> None:
        """Override and extend run function to run a rom and capture/emit its stdout, stderr, and return code."""
        date_object = datetime.now()
        formatted_date = date_object.strftime("%Y-%m-%d %H:%M")
        formatted_date = formatted_date.replace(' ', '_')
        formatted_date = formatted_date.replace(':', '-')
        full_mame_version = core.get_mame_version(self.mame_dir)
        short_mame_version = full_mame_version.split()[0]

        print(f'{self.rom_name}_{formatted_date}.inp')
        if self.record_input:
            commands = [self.mame_exe, self.rom_name, '-record',
                        f'{self.rom_name}_{formatted_date}_{short_mame_version}.inp']
        elif self.playback_input:
            if self.input_file_name:
                commands = [self.mame_exe, self.rom_name, '-playback', f'{self.input_file_name}.inp']
            else:
                print('a warning or something.')
                return
        else:
            commands = [self.mame_exe, self.rom_name]

        process = subprocess.Popen(commands,
                                   cwd=rf'{self.mame_dir}',
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True)
        output, err = process.communicate()
        return_code = process.returncode
        results = {'output': output, 'err': err, 'return_code': return_code, 'rom': self.rom_name}
        self.mame_exited.emit(results)


class PBScannerThread(QThread):
    """Subclass and extend the QThread class of the PyQt6.QtCore module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used to scan for personal bests, on a separate thread from the GUI. Avoids blocking GUI. Finished signal emitted.
    """

    def __init__(self, mame_dirs: list[core.MAMEDir]) -> None:
        super().__init__()
        self.mame_dirs = mame_dirs
        print(self.mame_dirs)

    def run(self) -> None:
        """Override and extend run function to scan for new personal bests. Emit signal when finished."""
        with sqlite3.connect(core.get_abs_path('mame_states.db')) as connection:
            db_cursor = connection.cursor()
            db_cursor.row_factory = sqlite3.Row
            hi2txt_wrapper.scan_for_pb(connection, db_cursor, self.mame_dirs)
            self.finished.emit()


class ProgressBarWidget(QDialog):
    """Subclass and extend the QDialog class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used to display an indeterminate progress bar within a popup dialog.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self.progress_bar = QProgressBar()
        """An indeterminate progress bar. Pulses."""

        self.progress_bar.setRange(0, 0)
        # self.progress.setMinimumWidth(400)

        self.label = QLabel('Scanning for new PBs...')
        """Dialog label."""
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        """Top level layout."""

        p_layout = QHBoxLayout()
        """Progress bar container widget."""

        p_layout.addStretch()
        p_layout.addWidget(self.progress_bar)
        p_layout.addStretch()

        layout.addWidget(self.label)
        layout.addLayout(p_layout)
        self.setLayout(layout)


class SaveStateNameInputValidator(QStyledItemDelegate):
    """Subclass and extend the QStyledItemDelegate class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    When a QLineEdit is created, a custom validator is automatically set. The validator disallows forbidden file names.
    The event filter is also extended to replace all instances of the 'space' key with a hyphen.
    """

    def createEditor(self, parent, option, index):
        """Automatically apply a custom validator on the created editor, if it is a QLineEdit.

        Custom validator disallows characters that are not valid in a Windows file path.
        """
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setMaxLength(20)
            pattern = QRegularExpression(r'^[^<>:"/\|?* ]*$')
            validator = QRegularExpressionValidator(pattern, editor)
            editor.setValidator(validator)

        return editor

    def eventFilter(self, watched, event):
        """Extend the eventFilter to replace 'space' key presses with hyphens."""
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                watched.insert('-')
                return True

        return super().eventFilter(watched, event)


#####################
#   Highscore Page  #
#####################
class RomSearchWindow(QWidget):
    """Subclass and extend the QWidget class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used to detach and display the Rom Search Page tab for use as a popup search dialog.
    Buttons are made visible during initialization. Buttons are hidden when window closes and tab reattaches.
    TODO I could probably move references to the buttons to the page widget and forgo the need to pass as args.
            I probably don't need to pass the page widget either, as it can be derived from tabs widget.
    """

    def __init__(self, rom_search_page: QWidget, tabs_container: QTabWidget, add_game_button: QPushButton | None = None,
                 cancel_button: QPushButton | None = None):
        super().__init__()
        self.add_game_button: QPushButton = add_game_button
        self.cancel_button: QPushButton = cancel_button
        self.tab_container: QTabWidget = tabs_container
        self.rom_search_page: QWidget = rom_search_page
        if self.add_game_button and self.cancel_button:
            self.add_game_button.show()
            self.cancel_button.show()
        self.rom_search_page.show()
        self.layout: QVBoxLayout = QVBoxLayout()
        self.layout.addWidget(self.rom_search_page)
        self.setLayout(self.layout)
        self.resize(800, 500)

    def closeEvent(self, event):
        # Reattach to tab when closed
        self.tab_container.addTab(self.rom_search_page, 'Rom Search')
        if self.add_game_button and self.cancel_button:
            self.add_game_button.hide()
            self.cancel_button.hide()
        main_window = self.tab_container.parent()
        main_window.setEnabled(True)
        event.accept()


class RomSearchDialog(QDialog):
    def __init__(self, rom_search_popup: RomSearchWindow, rom_search_tree: QTreeWidget, parent=None):
        super().__init__(parent)
        self.rom_search_tree = rom_search_tree
        self.rom_search_popup = rom_search_popup
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.select_rom)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addWidget(self.rom_search_popup)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        self.rom_description_for_inp = None

    def select_rom(self):
        selected = self.rom_search_tree.selectedItems()
        if selected:
            rom_item = selected[0]
            rom_description = rom_item.text(0)
            self.rom_description_for_inp = rom_description

    def sizeHint(self):
        return QSize(800, 800)


class NotesWindow(QWidget):
    """Subclass and extend QWidget class of the PyQt6.QyWidgets module.

    This class inherits most of its behavior from its parent class , while extending its functionality.
    A QWidget is initialized to create a detached window via flags. A single text edit is the only widget added.
    This window allows users to view and update notes a persistent set of notes, ona  per-game basis.
    When the window is closed, all text in the notes widget replaces previous text in corresponding notes.txt file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("New Text Edit Window")
        self.resize(400, 300)
        self.text_edit = QTextEdit()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)

        notes_dir = Path(core.get_abs_path(r'../notes'))
        notes_dir.mkdir(exist_ok=True)

        self.current_game = None
        """Name of game that corresponds to this instance of NotesWindow."""

    def closeEvent(self, event: QCloseEvent):
        """Extend closeEvent to save text edit data to notes.txt corresponding to this NotesWindow."""
        with open(Path(core.get_abs_path(r'../notes')) / (self.current_game + '.txt'), 'w') as notes:
            notes.write(self.text_edit.toPlainText())
        # TODO Do I need to call super? What does close usually do?
        # super().closeEvent(event)


class ToggleableLabel(QWidget):
    """Subclass and extend the QWidget class of the PyQt6.QyWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    A normal QLabel instance is tied to a QlineEdit instance on initialization.
    Double-clicking the label toggles the editor. Pressing enter or changing focus will toggle back to the label.
    The current text persists when toggled. Changes are confirmed via dialog before actually changing.
    The text reverts if the changes are not confirmed.
    """

    def __init__(self, text: str | int, parent=None):
        super().__init__(parent)
        self.layout: QHBoxLayout = QHBoxLayout(self)
        # self.setMouseTracking(True)
        if isinstance(text, int):
            text = f'{text:,}'
        self.label: QLabel = QLabel(text)
        self.editor: QLineEdit = QLineEdit(text.replace(',', ''))

        self.editor.hide()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)
        self.editor.setMinimumHeight(self.sizeHint().height())
        self.editor.editingFinished.connect(self.toggle_label)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_editor()
        super().mouseDoubleClickEvent(event)

    def toggle_editor(self) -> None:
        """Show editor, hide label."""
        self.label.hide()
        self.editor.show()
        self.editor.setFocus()

    def toggle_label(self) -> None:
        """Show label, hide editor.

        Confirms any changes made. If changes are not confirmed, text is reverted.
        """
        new_text = self.editor.text()
        if new_text.isdigit():
            new_text = f'{int(new_text):,}'
        old_text = self.label.text()
        stripped_label = old_text.split('(+')[0]
        stripped_label = stripped_label.split('(-')[0]
        print(stripped_label)

        if new_text != stripped_label:
            # Create confirmation box
            reply = QMessageBox.question(self, 'Confirm Change',
                                         f"Change text to '{new_text}' from {stripped_label}?",
                                         QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.label.setText(new_text)
                if isinstance(self.parent(), StageSplitItem):
                    widget = self.parent()
                    widget._update_split_db()
                    widget.parent_list.add_diffs(widget.core.pb_info[widget.rom_description].splits)
            else:
                self.editor.setText(self.label.text().replace(',', ''))  # Revert

        self.editor.hide()
        self.label.show()


class PBField(QWidget):
    def __init__(self, field_name: str, field_value: str | int):
        super().__init__()
        field_name = (field_name + ':')
        if isinstance(field_value, int):
            field_value = f'{field_value:,}'
        self.field_name = QLabel(field_name)
        self.field_value = ToggleableLabel(field_value)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.field_name)
        self.layout.addWidget(self.field_value)


class StageSplitItem(QWidget):
    """Subclass and extend the QWidget class of the PyQt6.QtWidgets module

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used as a customer item widget on a QListWidget instance."""

    def __init__(self, split: core.Split, rom_description: str,
                 parent_list: 'StageSplitListWidget', mcore: core.MAMEStatesCore) -> None:
        """ Initialize the StageSplitItem subclass

        The StageSplitItem subclass inherits most of its behavior from, and extends, its parent class QWidget.
        The initialization process creates the widgets and layouts that will make up the custom item widget.
        """
        super().__init__()
        self.core = mcore

        self.split = split
        """The data that comprises a split. \n[index, stage, score]"""

        self.parent_list: StageSplitListWidget = parent_list
        """The list widget that contains this item."""

        # self.pb_info = pb_info
        # """In-memory representation of DB schema."""

        self.rom_description: str = rom_description
        """The name of the game which the split belongs to."""

        self.stage: str = split.label
        self.score: int = split.score

        self.name_label: ToggleableLabel = ToggleableLabel(self.stage)
        self.score_label: ToggleableLabel = ToggleableLabel(self.score)

        self.name_label.editor.setPlaceholderText('Stage-69')
        self.score_label.editor.setPlaceholderText('696969')

        self.name_label.editor.hide()
        self.score_label.editor.hide()
        self.name_label.editor.editingFinished.connect(self._update_split_db)
        # self.score_label.editor.editingFinished.connect(self._update_split_db)
        self.name_label.editor.returnPressed.connect(self.toggle_labels)
        self.score_label.editor.returnPressed.connect(self.toggle_labels)
        self.score_label.editor.setValidator(QIntValidator())

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.score_label)

        self.setLayout(self.layout)

    def toggle_editors(self) -> None:
        """Show editors, hide labels. Text is persisted."""
        self.name_label.toggle_editor()
        self.score_label.toggle_editor()

    def toggle_labels(self):
        """Show labels, hide editors. Text is persisted."""
        self.name_label.toggle_label()
        self.score_label.toggle_label()

    def _update_split_db(self) -> None:
        """Update the 'in-memory' copy of the database and save to database.

        Split order is preserved by the position of the in-memory representation of this item in the game's splits list.
        Grabbing the index of the list that represents this item in memory allows you to act on the correct list.
        Will no save empty pb label.
        """
        item_index = self.core.pb_info[self.rom_description].splits.index(self.split)
        old_label = self.core.pb_info[self.rom_description].splits[item_index].label
        self.core.pb_info[self.rom_description].splits[item_index].score = int(self.score_label.editor.text())
        self.core.pb_info[self.rom_description].splits[item_index].label = self.name_label.editor.text()
        print(f'here: {old_label}')

        if self.name_label.editor.text():
            self.core.delete_split(self.rom_description, old_label)
            self.core.save_pb_to_database()


class StageSplitListWidget(QListWidget):
    """Subclass and extend the QListWidget class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Internal movement is active. The order of splits is preserved.
    The difference between splits is calculated and displayed.
    """

    def __init__(self, mcore: core.MAMEStatesCore):
        """ The StageSplitListWidget subclass inherits most of its behavior from, and extends,
        its parent class QListWidget.

        The initialization process customizes the widget.
        """
        super().__init__()
        self.core = mcore
        self.last_row: int | None = None
        """The previously selected row. Used internally to track split movement."""

        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.installEventFilter(self)
        self.currentItemChanged.connect(self.selection_changed)

    def itemWidget(self, item) -> QWidget | StageSplitItem | None:
        """Overloaded to extend typehint."""
        return super().itemWidget(item)

    def eventFilter(self, sender, event):
        """Event filter that listens for an item being moved in the list.

        When an item is moved, the new order is preserved and the split differences are recalculated.
        """
        if event.type() == QEvent.Type.ChildRemoved:  # Child removed includes item deletion as well as movement.
            items_that_moved = self.selectedItems()
            if items_that_moved:
                item_that_moved = items_that_moved[0]
                rom_description = self.itemWidget(item_that_moved).rom_description
                self.update_db(rom_description, self.last_row, self.row(item_that_moved))
                splits = self.core.pb_info[rom_description].splits
                self.add_diffs(splits)
                # print(f'{moved.text()} was moved to row {self.row(moved) + 1} from row {self.last_row + 1}')
                self.last_row = self.row(item_that_moved)
        return super().eventFilter(sender, event)

    def selection_changed(self, current_item: QListWidgetItem, previous_item: QListWidgetItem) -> None:
        """Used internally to preserve split order."""
        if current_item:
            self.last_row = self.row(current_item)

    def update_db(self, rom_description: str, old_index: int, new_index: int) -> None:
        """Mirror internal list changes to the in-memory representation. Save to database."""
        splits = self.core.pb_info[rom_description].splits
        if not (len(splits) - 1) < old_index:
            split = splits.pop(old_index)
            splits.insert(new_index, split)
        self.core.save_pb_to_database()

    def add_diffs(self, splits: list[core.Split]) -> None:
        """Calculate and display the difference between a splits score, and the previous splits score."""
        for index, split in enumerate(splits):
            if index > 0:
                diff = split.score - splits[index - 1].score
                list_item = self.item(index)
                widget_item = self.itemWidget(list_item)
                widget_item.score_label.label.setText(f'{split.score:,}' + f'({diff:+d})')
            else:
                list_item = self.item(index)
                widget_item = self.itemWidget(list_item)
                widget_item.score_label.label.setText(f'{split.score:,}')
