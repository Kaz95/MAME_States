"""MAMEStates custom Pyqt6 widgets

This module houses all pyqt6 widgets that have been subclassed and extended.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QRegularExpression, QThread, QSize, QProcess, QModelIndex, QLocale, QSignalBlocker
from PyQt6.QtGui import QRegularExpressionValidator, QCloseEvent, QColor, QIntValidator, QAction
from PyQt6.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QWidget, QStyledItemDelegate, QTextEdit, \
    QVBoxLayout, QPushButton, QDialog, QProgressBar, QTabWidget, QDialogButtonBox, \
    QTreeWidget, QMenu, QInputDialog, QTreeWidgetItem, QStyleOptionViewItem, QMessageBox

import core
import hi2txt_wrapper


# TODO Not sure if use Paths or str within function. Whatever I choose needs to be consistent across entire app.
class MAMEProcess(QProcess):
    """Subclass and extend the QProcess class of the PyQt6.QtCore module.


    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used when launching any type of MAME process. Stdout and stderr are piped to the main process in real time.
    """
    def __init__(self, mame_dir: Path, text_box: QTextEdit, rom_name: str | None = None, *, record_input: bool = False,
                 playback_input: bool = False, input_file_name: str | None = None):
        """If no flags are 'True' during init, the default action is to run the mame.exe file in the given mame_dir."""
        super().__init__()

        self.text_box: QTextEdit = text_box
        """Acts as read-only terminal viewer within app."""

        self.mame_dir: Path = mame_dir
        self.mame_exe: Path = self.mame_dir / 'mame.exe'
        self.rom_name: str | None = rom_name
        self.record_input: bool = record_input
        self.playback_input: bool = playback_input
        self.input_file_name: str | None = input_file_name

        self.setWorkingDirectory(str(self.mame_dir))

        self.readyReadStandardOutput.connect(self.handle_stdout)
        self.readyReadStandardError.connect(self.handle_stderr)
        self.finished.connect(self.process_finished)


        if self.playback_input is True and self.record_input is True:
            raise ValueError('Record/Playback are mutually exclusive.')

        if self.playback_input is True:
            if not self.input_file_name:
                raise ValueError("Input File Name is required when using 'playback_input' flag.")
            self.run_mame_with_inp_playback()

        elif self.record_input is True:
            if self.input_file_name:
                # TODO Not sure if ignore silently, or inform why it isn't working.
                raise ValueError('This class is not currently setup to allow custom input file names.')
            self.run_mame_with_inp_recording()

        elif rom_name:
            if self.input_file_name:
                # TODO Not sure if ignore silently, or inform why it isn't working.
                raise ValueError(
                    "This class does not make use of 'input_file_name' unless 'playback_input' flag is True.")
            self.run_mame_with_rom()

        else:
            self.run_mame()

    def run_mame(self) -> None:
        """Run mame.exe file."""
        self.start(str(self.mame_exe))

    def run_mame_with_rom(self) -> None:
        """Open a given rom file, with a given mame.exe file."""
        self.start(str(self.mame_exe), [self.rom_name])

    def run_mame_with_inp_recording(self) -> None:
        """Open a given rom file with input file recording, with a given mame.exe file.

        The input file is named in the following format: [rom_name]_Y-m-d_H-M-[mame_version].inp
        """
        date_object = datetime.now()
        formatted_date = date_object.strftime("%Y-%m-%d %H:%M")
        formatted_date = formatted_date.replace(' ', '_')
        formatted_date = formatted_date.replace(':', '-')
        full_mame_version = core.get_mame_version(Path(self.mame_dir))
        short_mame_version = full_mame_version.split()[0]

        self.start(str(self.mame_exe),
                   [self.rom_name, '-record', f'{self.rom_name}_{formatted_date}_{short_mame_version}.inp'])

    def run_mame_with_inp_playback(self) -> None:
        """Playback a given rom file, for a particular game, using a particular mame.exe."""
        self.start(str(self.mame_exe), [self.rom_name, '-playback', f'{self.input_file_name}.inp'])

    def handle_stdout(self) -> None:
        """Decode stdout and append to apps 'terminal'."""
        data = self.readAllStandardOutput()
        stdout = data.data().decode()
        self.text_box.append(stdout)

    def handle_stderr(self) -> None:
        """Decode stderr and append to apps 'terminal'."""
        data = self.readAllStandardError()
        stderr = data.data().decode()
        self.text_box.append(f"Error: {stderr}")

    def process_finished(self) -> None:
        """Alert user when process closes. Not strictly needed."""
        self.text_box.append("Process finished.")


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


######################
#   Save State Page  #
######################
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
#   Hiscore Page  #
#####################
class RomSearchWindow(QWidget):
    """Subclass and extend the QWidget class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used to detach and display the Rom Search Page tab for use as a popup search dialog.
    Buttons are made visible during initialization. Buttons are hidden when window closes and tab reattaches.
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
    """Subclass and extend QDialog class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class , while extending its functionality.
    The 'rom search' tab is passed in and inserted into a custom dialog, along with a standard dialog button box.
    """

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

    def select_rom(self) -> None:
        """Select a rom and set class attribute to roms description. Will be retrieved after dialog closes."""
        selected_item = self.rom_search_tree.currentItem()
        if selected_item:
            rom_description = selected_item.text(0)
            self.rom_description_for_inp = rom_description

    def sizeHint(self):
        return QSize(800, 800)


class NotesWindow(QWidget):
    """Subclass and extend QWidget class of the PyQt6.QtWidgets module.

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

        notes_dir = Path(core.get_abs_path(r'./notes'))
        notes_dir.mkdir(exist_ok=True)

        self.current_game = None
        """Name of game that corresponds to this instance of NotesWindow."""

    def closeEvent(self, event: QCloseEvent):
        """Extend closeEvent to save text edit data to notes.txt corresponding to this NotesWindow."""
        with open(Path(core.get_abs_path(r'./notes')) / (self.current_game + '.txt'), 'w') as notes:
            notes.write(self.text_edit.toPlainText())
        event.accept()


class PBSplitTreeDelegate(QStyledItemDelegate):
    """Subclass and extend the QStyledItemDelegate class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Dictate which columns are editable based on flags set in parent tree. Add separators to numerals.
    Color positive and negative numbers respectively in the 'diff' column. Cast values to and fro strings/ints as
    needed.
    """
    # def __init__(self, parent=None):
    #     super().__init__(parent)


    def createEditor(self, parent, option, index):
        if self.parent().usage == 'pb':
            if index.column() == 1:
                return QLineEdit(parent)
            # Return None for other columns to prevent editing
            return None
        else:
            if index.column() == 0 or index.column() == 1:
                editor = QLineEdit(parent)
                editor.setValidator(QIntValidator())
                return editor
            return None

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        value = index.data(Qt.ItemDataRole.DisplayRole)

        if isinstance(value, int):
            option.text = QLocale().toString(value)
        else:
            if value.startswith('-'):
                red = QColor("red")
                option.palette.setColor(option.palette.ColorRole.Text, red)
                option.palette.setColor(option.palette.ColorRole.HighlightedText, red)
            if value.startswith('+'):
                green = QColor("green")
                option.palette.setColor(option.palette.ColorRole.Text, green)
                option.palette.setColor(option.palette.ColorRole.HighlightedText, green)
            option.text = value

    def setEditorData(self, editor, index):
        # Retrieve the raw integer data
        value = index.data(Qt.ItemDataRole.EditRole)
        # Convert to string for the QLineEdit
        editor.setText(str(value))

    def setModelData(self, editor, model, index):
        # Get the string from the editor
        text = editor.text()
        # Convert back to integer
        try:
            value = int(text)
            model.setData(index, value, Qt.ItemDataRole.EditRole)
        except ValueError:
            model.setData(index, text, Qt.ItemDataRole.EditRole)


class PBSplitTreeWidget(QTreeWidget):
    """Subclass and extend the QTreeWidget class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    When used for splits, internal movement is active, the order of splits is preserved, and
    the difference between splits is calculated and displayed.

    When used for PBs, internal movement is not active, list order is static.
    """

    def __init__(self, mcore: core.MAMEStatesCore, hs_game_tree: QTreeWidget, usage):
        """ The StageSplitListWidget subclass inherits most of its behavior from, and extends,
        its parent class QListWidget.

        The initialization process customizes the widget.
        """
        super().__init__()
        # pass
        self.usage = usage
        self.core = mcore
        self.hs_game_tree: QTreeWidget = hs_game_tree
        self.last_row: int | None = None
        """The previously selected row. Used internally to track split movement."""


        self.add_pb_field = QAction('Add Field')
        self.delete_pb_field = QAction('Delete Field')


        # TODO Use enum
        # TODO Delegate should be used across entire tree. Should be fine as its behavior is customized internally.
        if usage == 'splits':
            self.setColumnCount(3)
            self.setHeaderLabels(['Stage', 'Score', 'Difference'])
            self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
            self.setItemDelegateForColumn(1, PBSplitTreeDelegate(self))
            self.setItemDelegateForColumn(2, PBSplitTreeDelegate(self))

        elif usage == 'pb':
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_body_menu)
            self.add_pb_field.triggered.connect(self.add_pb_field_triggered)
            self.delete_pb_field.triggered.connect(self.delete_pb_field_triggered)
            self.setColumnCount(2)
            self.setHeaderLabels(['Field', 'Value'])
            self.setItemDelegateForColumn(0, PBSplitTreeDelegate(self))
            self.setItemDelegateForColumn(1, PBSplitTreeDelegate(self))

        else:
            raise ValueError('"usage", must be "pb" or "splits"')

        header = self.header()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_menu)



        self.itemPressed.connect(self.item_pressed)

        # QueuedConnection allows editor to be reopened after the close event finishes.
        self.itemChanged.connect(self.item_changed, Qt.ConnectionType.QueuedConnection)


    def add_pb_field_triggered(self) -> None:
        rom_description = self.hs_game_tree.currentItem().text(0)
        field_name, ok = QInputDialog.getText(self, 'User Input', 'Field Name', text='Placeholder')
        if field_name and ok:
            other_fields = self.core.pb_info[rom_description].other_fields
            if field_name in other_fields.keys() or field_name == 'High Score':
                QMessageBox.critical(self, 'Error', 'Name already in use for this rom. Try again.')
                self.add_pb_field_triggered()
            else:
                other_fields[field_name] = None
                new_item = self.add_editable_item(field_name, '')
                self.editItem(new_item, 1)

    def delete_pb_field_triggered(self) -> None:
        rom_description = self.hs_game_tree.currentItem().text(0)
        item_to_be_deleted = self.currentItem()
        item_above = self.itemAbove(item_to_be_deleted)
        item_below = self.itemBelow(item_to_be_deleted)
        pb_field_name = item_to_be_deleted.text(0)
        item_to_be_deleted_index = self.indexOfTopLevelItem(item_to_be_deleted)
        self.takeTopLevelItem(item_to_be_deleted_index)
        del self.core.pb_info[rom_description].other_fields[pb_field_name]
        self.core.save_pb_to_database()

        if item_above:
            self.setCurrentItem(item_above)
        elif item_below:
            self.setCurrentItem(item_below)


    def show_header_menu(self, pos):
        column_index = self.header().logicalIndexAt(pos)
        menu = QMenu(self)
        rename_action = menu.addAction(f"Rename '{self.headerItem().text(column_index)}' Column ")

        if menu.exec(self.header().mapToGlobal(pos)) == rename_action:
            current_text = self.headerItem().text(column_index)
            new_text, ok = QInputDialog.getText(self, "Rename Header", "New name:", text=current_text)
            if ok and new_text:
                self.headerItem().setText(column_index, new_text)

    def show_body_menu(self, pos):
        tree_item = self.itemAt(pos)
        menu = QMenu(self)
        menu.addAction(self.add_pb_field)
        if tree_item:
            menu.addAction(self.delete_pb_field)

        menu.exec(self.viewport().mapToGlobal(pos))




    # TODO Consider checking for empty string on col 1. Maybe raise value error. Blank item saved to DB == Bad.
    def add_editable_item(self, col1, col2):
        item = QTreeWidgetItem(self)
        item.setData(0, Qt.ItemDataRole.DisplayRole, col1)
        item.setData(1, Qt.ItemDataRole.DisplayRole, col2)

        # Allow editing for all columns in this row
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable)
        self.addTopLevelItem(item)
        return item

    def dropEvent(self, event):
        item_that_moved = self.currentItem()  # Get items before drop completes
        super().dropEvent(event)
        hs_game_item = self.hs_game_tree.currentItem()
        rom_description = hs_game_item.text(0)
        if item_that_moved:
            self.update_split_order(rom_description, self.last_row, self.indexOfTopLevelItem(item_that_moved))
            splits = self.core.pb_info[rom_description].splits
            self.add_diffs(splits)
            self.last_row = self.indexOfTopLevelItem(item_that_moved)

    def item_pressed(self, item: QTreeWidgetItem, column: int) -> None:
        """Used internally to preserve split order."""
        self.last_row = self.indexOfTopLevelItem(item)

    def item_changed(self, item: QTreeWidgetItem, column: int):
        if self.usage == 'pb':
            rom_description = self.hs_game_tree.currentItem().text(0)
            field_name = item.text(0)
            if field_name == 'High Score':
                self.core.pb_info[rom_description].hiscore = int(item.text(column))
            else:
                self.core.pb_info[rom_description].other_fields[field_name] = item.text(column)
            self.core.save_pb_to_database()
            return

        else:
            item_index = self.indexOfTopLevelItem(item)
            rom_description = self.hs_game_tree.currentItem().text(0)
            old_label = self.core.pb_info[rom_description].splits[item_index].label
            if column == 0:
                split_names = [split.label for split in self.core.pb_info[rom_description].splits]
                if item.text(column) in split_names:
                    QMessageBox.critical(self, 'Error', 'Name already in use. Try Again.')
                    with QSignalBlocker(self):
                        item.setText(column, old_label)
                        return

                if not item.text(column):
                    QMessageBox.critical(self, 'Error', 'Blank split names are not allowed. try Again.')
                    with QSignalBlocker(self):
                        item.setText(column, old_label)
                        self.editItem(item, column)
                        return

                self.core.pb_info[rom_description].splits[item_index].label = item.text(column)
                self.core.delete_split(rom_description, old_label)
                self.core.save_pb_to_database()
                # update label

            elif column == 1:
                self.core.pb_info[rom_description].splits[item_index].score = int(item.text(column))
                self.core.delete_split(rom_description, old_label)
                self.core.save_pb_to_database()
                splits = self.core.pb_info[rom_description].splits
                self.add_diffs(splits)
                # Update score

            else:
                # Out of range
                pass

    def update_split_order(self, rom_description: str, old_index: int, new_index: int) -> None:
        """Mirror internal list changes to the in-memory representation. Save to database."""
        splits = self.core.pb_info[rom_description].splits
        if not (len(splits) - 1) < old_index:
            split = splits.pop(old_index)
            splits.insert(new_index, split)
        self.core.save_pb_to_database()

    def add_diffs(self, splits: list[core.StageSplit]) -> None:
        """Calculate and display the difference between a splits score, and the previous splits score."""
        for index, split in enumerate(splits):
            if index > 0:
                diff = split.score - splits[index - 1].score
                tree_item = self.topLevelItem(index)
                tree_item.setText(2, f'{diff:+,}')
            else:
                tree_item = self.topLevelItem(index)
                tree_item.setText(2, f'')
