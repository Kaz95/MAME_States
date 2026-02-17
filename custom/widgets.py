import sqlite3
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QEvent, QRegularExpression, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIntValidator, QRegularExpressionValidator, QCloseEvent
from PyQt6.QtWidgets import QLabel, QLineEdit, QListWidget, QHBoxLayout, QWidget, QStyledItemDelegate, QTextEdit, \
    QVBoxLayout, QPushButton, QDialog, QProgressBar, QMessageBox

from logic.main import save_pb_to_database, scan_for_pb


######################
#   Save State Page  #
######################
class MAMEThread(QThread):
    done: pyqtSignal = pyqtSignal(dict)
    def __init__(self, mame_exe, rom_name, mame_path):
        super().__init__()

        self.mame_exe = mame_exe
        self.rom_name = rom_name
        self.mame_path = mame_path
    def run(self):
        process = subprocess.Popen([self.mame_exe, self.rom_name], cwd=rf'{self.mame_path}')
        output, err = process.communicate()
        return_code = process.returncode
        print(return_code)
        results = {'output': output, 'err': err, 'return_code': return_code, 'rom': self.rom_name}
        self.done.emit(results)

class PBScannerThread(QThread):
    def __init__(self):
        super().__init__()
        # finished = pyqtSignal()


    def run(self):
        with sqlite3.connect(r'C:\Users\kazac\PycharmProjects\MAME_States\mame_states.db') as connection:
            db_cursor = connection.cursor()
            scan_for_pb(connection, db_cursor)
            self.finished.emit()


class ProgressBarWidget(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        # self.progress.setMinimumWidth(400)
        self.label = QLabel('Scanning for new PBs...')
        # self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        # l_layout = QHBoxLayout()
        # l_layout.addStretch()
        # l_layout.addWidget(self.label)
        # l_layout.addStretch()
        p_layout = QHBoxLayout()
        p_layout.addStretch()
        p_layout.addWidget(self.progress)
        p_layout.addStretch()
        layout.addWidget(self.label)
        layout.addLayout(p_layout)
        self.setLayout(layout)

    # def sizeHint(self):
    #     return QSize(250, 20)

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
    def __init__(self, widget, original_tab_widget, add_game_button, cancel_button):
        super().__init__()
        self.add_game_button: QPushButton = add_game_button
        self.cancel_button: QPushButton = cancel_button
        self.original_tab_widget = original_tab_widget
        self.widget = widget
        self.add_game_button.show()
        self.cancel_button.show()
        # self.widget.setWindowFlags(Qt.WindowType.Window)
        self.widget.show()
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)
        self.resize(800, 500)

    def closeEvent(self, event):
        # Reattach to tab when closed
        self.original_tab_widget.addTab(self.widget, 'Rom Search')
        self.add_game_button.hide()
        self.cancel_button.hide()
        main_window = self.original_tab_widget.parent()
        main_window.setEnabled(True)
        event.accept()


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
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        self.current_game = None
        """Name of game that corresponds to this instance of NotesWindow."""

    def closeEvent(self, event: QCloseEvent):
        """Extend closeEvent to save text edit data to notes.txt corresponding to this NotesWindow."""
        with open(Path('./notes') / self.current_game, 'w') as notes:
            notes.write(self.text_edit.toPlainText())
        # Do I need to call super? What does close usually do?
        # super().closeEvent(event)

class NewToggleableLabel(QWidget):
    """Subclass and extend the QLabel class of the PyQt6.QyWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    A normal QLabel instance is tied to a QlineEdit instance on initialization.
    Double-clicking the label toggles the editor. Pressing enter or changing focus will toggle back to the label.
    The current text is persisted when toggled.
    """

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setMouseTracking(True)
        self.label = QLabel(text)
        self.editor: QLineEdit = QLineEdit(text)

        self.editor.hide()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)
        self.editor.setMinimumHeight(self.sizeHint().height())
        """The editor associated with this label"""
        self.editor.editingFinished.connect(self.toggle_labels)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_editors()
        super().mouseDoubleClickEvent(event)

    def toggle_editors(self) -> None:
        """Show associated editor, hide label."""
        self.label.hide()
        self.editor.show()
        self.editor.setFocus()


    def toggle_labels(self) -> None:
        """Show associated label, hide editor."""
        new_text = self.editor.text()

        if new_text != self.label.text():
            # Create confirmation box
            reply = QMessageBox.question(self, 'Confirm Change',
                                         f"Change text to '{new_text}'?",
                                         QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.label.setText(new_text)
            else:
                self.editor.setText(self.label.text())  # Revert

        self.editor.hide()
        self.label.show()


class ToggleableLabel(QLabel):
    """Subclass and extend the QLabel class of the PyQt6.QyWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    A normal QLabel instance is tied to a QlineEdit instance on initialization.
    Double-clicking the label toggles the editor. Pressing enter or changing focus will toggle back to the label.
    The current text is persisted when toggled.
    """

    def __init__(self, editor: QLineEdit, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.editor: QLineEdit = editor
        """The editor associated with this label"""
        self.editor.editingFinished.connect(self.toggle_labels)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_editors()
        super().mouseDoubleClickEvent(event)

    def toggle_editors(self) -> None:
        """Show associated editor, hide label."""
        self.hide()
        self.editor.setText(self.text())
        self.editor.show()
        self.editor.setFocus()

    def toggle_labels(self) -> None:
        """Show associated label, hide editor."""
        self.editor.hide()
        text = self.editor.text()
        self.setText(text)

        self.show()


class StageSplitItem(QWidget):
    """Subclass and extend the QWidget class of the PyQt6.QtWidgets module

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used as a customer item widget on a QListWidget instance."""

    def __init__(self, split: list[str | int], game_db: dict, game_name: str,
                 parent_list: 'StageSplitListWidget', connection: sqlite3.Connection, cursor: sqlite3.Cursor) -> None:
        """ Initialize the StageSplitItem subclass

        The StageSplitItem subclass inherits most of its behavior from, and extends, its parent class QWidget.
        The initialization process creates the widgets and layouts that will make up the custom item widget.
        """
        super().__init__()
        self.text_before_editing = None
        self.db_connection: sqlite3.Connection = connection
        """Connection object that points to database connection."""

        self.db_cursor: sqlite3.Cursor = cursor
        """Cursor object used to navigate database."""

        self.split = split
        """The data that comprises a split. \n[index, stage, score]"""

        self.parent_list: StageSplitListWidget = parent_list
        """The list widget that contains this item."""

        self.game_db = game_db
        """In-memory representation of DB schema."""

        self.game_name: str = game_name
        """The name of the game which the split belongs to."""

        self.stage: str = split[0]
        self.score: int = split[1]

        self.name_label: QLabel = QLabel(f'{self.stage}')
        """Name of the stage, area, or boss that the split represents."""

        self.score_label: QLabel = QLabel(f'{self.score}')
        """The Score of this particular split."""

        self.name_editor: QLineEdit = QLineEdit()
        self.score_editor: QLineEdit = QLineEdit()

        self.name_editor.setPlaceholderText('Stage-69')
        self.score_editor.setPlaceholderText('696969')

        self.name_editor.setText(self.stage)
        self.score_editor.setText(str(self.score))

        self.name_editor.hide()
        self.score_editor.hide()

        self.name_editor.editingFinished.connect(self._update_split_db)
        self.score_editor.editingFinished.connect(self._update_split_db)

        self.name_editor.returnPressed.connect(self._update_split_db)
        self.score_editor.returnPressed.connect(self._update_split_db)
        self.name_editor.returnPressed.connect(self.toggle_labels)
        self.score_editor.returnPressed.connect(self.toggle_labels)

        self.score_editor.setValidator(QIntValidator())

        layout = QHBoxLayout()
        layout.addWidget(self.name_label)
        layout.addWidget(self.score_label)
        layout.addWidget(self.name_editor)
        layout.addWidget(self.score_editor)

        self.setLayout(layout)

    def toggle_editors(self) -> None:
        """Show editors, hide labels. Text is persisted."""

        self.name_label.hide()
        self.score_label.hide()

        name_text = self.name_label.text()
        self.text_before_editing = name_text
        name_text = name_text.strip(':')


        score_text = self.score_label.text()

        # Check for presence of diff text, strip if there.
        if '(' in score_text:
            end = score_text.index('(')
            score_text = score_text[:end]

        self.name_editor.setText(name_text)
        self.score_editor.setText(score_text)

        self.name_editor.show()
        self.score_editor.show()

        self.score_editor.setFocus()

    def toggle_labels(self) -> None:
        """Show labels, hide editors. Text is persisted."""
        self.name_editor.hide()
        self.score_editor.hide()

        name_text = self.name_editor.text()
        self.name_label.setText(name_text)

        score_text = self.score_editor.text()
        self.score_label.setText(score_text)

        self.parent_list.add_diffs(self.game_db[self.game_name]['splits'])

        self.name_label.show()
        self.score_label.show()

    def _update_split_db(self) -> None:
        """Update the 'in-memory' copy of the database and save to JSON

        Split order is preserved by the position of the in-memory representation of this item in the game's splits list.
        Grabbing the index of the list that represents this item in memory allows you to act on the correct list.
        """
        item_index = self.game_db[self.game_name]['splits'].index(self.split)
        print(self.game_db[self.game_name]['splits'])
        for x in self.game_db[self.game_name]['splits']:
            if self.name_editor.text() == x[0]:
                self.blockSignals(True)
                self.name_editor.setText(self.text_before_editing)
                self.blockSignals(False)
                return
        self.game_db[self.game_name]['splits'][item_index][1] = int(self.score_editor.text())
        self.game_db[self.game_name]['splits'][item_index][0] = self.name_editor.text()

        if self.name_editor.text():
            # save_pb_to_database(self.db_connection, self.db_cursor, self.game_db)
            save_pb_to_database(self.db_connection, self.db_cursor, self.game_db)

class StageSplitListWidget(QListWidget):
    """Subclass and extend the QListWidget class of the PyQt6.QtWidgets module.

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Internal movement is active. The order of splits is preserved.
    The difference between splits is calculated and displayed.
    """

    def __init__(self, game_db, connection: sqlite3.Connection, cursor: sqlite3.Cursor):
        """ The StageSplitListWidget subclass inherits most of its behavior from, and extends,
        its parent class QListWidget.

        The initialization process customizes the widget.
        """
        super().__init__()
        self.db_connection: sqlite3.Connection = connection
        self.db_cursor: sqlite3.Cursor = cursor

        self.game_db = game_db
        """In-memory representation of DB schema."""

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
        if event.type() == QEvent.Type.ChildRemoved:
            moved = self.selectedItems()
            if moved:
                moved = moved[0]
                game_name = self.itemWidget(moved).game_name
                self.update_db(game_name, self.last_row, self.row(moved))
                splits = self.game_db[game_name]['splits']
                self.add_diffs(splits)
                # print(f'{moved.text()} was moved to row {self.row(moved) + 1} from row {self.last_row + 1}')
                self.last_row = self.row(moved)
        return super().eventFilter(sender, event)

    def selection_changed(self, cur, prev) -> None:
        """Used internally to preserve split order."""
        if cur:
            self.last_row = self.row(cur)

    def update_db(self, game_name: str, old_index: int, new_index: int) -> None:
        """Mirror internal list changes to the in-memory representation. Save to JSON."""
        splits = self.game_db[game_name]['splits']
        split = splits.pop(old_index)
        splits.insert(new_index, split)
        # save_pb_to_database(self.db_connection, self.db_cursor, self.game_db)
        save_pb_to_database(self.db_connection, self.db_cursor, self.game_db)
    def add_diffs(self, splits: list) -> None:
        """Calculate and display the difference between a splits score, and the previous splits score."""
        for index, split in enumerate(splits):
            if index > 0:
                diff = split[1] - splits[index - 1][1]
                list_item = self.item(index)
                widget_item = self.itemWidget(list_item)
                widget_item.score_label.setText(str(split[1]) + f'({diff:+d})')
            else:
                list_item = self.item(index)
                widget_item = self.itemWidget(list_item)
                widget_item.score_label.setText(str(split[1]))
