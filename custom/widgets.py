from PyQt6.QtCore import Qt, QEvent, QRegularExpression
from PyQt6.QtGui import QIntValidator, QRegularExpressionValidator
from PyQt6.QtWidgets import QLabel, QLineEdit, QListWidget, QHBoxLayout, QWidget, QStyledItemDelegate

from logic.main import save_pb_to_json


class ToggleableLabel(QLabel):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.editor: QLineEdit = editor
        self.editor.editingFinished.connect(self.toggle_labels)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_editors()
        super().mouseDoubleClickEvent(event)

    def toggle_editors(self):
        self.hide()
        if self.text():
            self.editor.setText(self.text())
        self.editor.show()
        self.editor.setFocus()

    def toggle_labels(self):
        self.editor.hide()
        text = self.editor.text()
        if text:
            self.setText(text)

        self.show()

class StageSplitListWidget(QListWidget):
    def __init__(self, game_db):
        super().__init__()
        self.game_db = game_db
        self.last_row = None
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.installEventFilter(self)
        self.currentItemChanged.connect(self.selection_changed)


    def eventFilter(self, sender, event):
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

    def selection_changed(self, cur, prev):
        if cur:
            self.last_row = self.row(cur)

    def update_db(self, game_name, old_index, new_index):
        splits = self.game_db[game_name]['splits']
        split = splits.pop(old_index)
        splits.insert(new_index, split)
        save_pb_to_json(self.game_db)

    def add_diffs(self, splits):
        for index, split in enumerate(splits):
            if index > 0:
                diff = split[2] - splits[index - 1][2]
                print(diff)
                list_item = self.item(index)
                widget_item = self.itemWidget(list_item)
                widget_item.score_label.setText(str(split[2]) + f'({diff:+d})')
            else:
                list_item = self.item(index)
                widget_item = self.itemWidget(list_item)
                widget_item.score_label.setText(str(split[2]))

class StageSplitItem(QWidget):
    """Subclass and extend the QWidget class of the PyQt6.QtWidgets module

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Used as a customer item widget on a QListWidget instance."""

    def __init__(self, split: list[int], game_db: dict, game_name: str) -> None:
        """ Initialize the StageSplitItem subclass

        The StageSplitItem subclass inherits most of its behavior from, and extends, its parent class QWidget.
        The initialization process creates the widgets and layouts that will make up the custom item widget.
        """
        super().__init__()
        self.split = split
        self.game_db = game_db
        """In-memory representation of DB schema."""

        self.game_name = game_name
        """The name of the game which the split belongs to."""

        self.item_index = split[0]
        """The index of the split, used for maintaining correct order."""

        self.stage = split[1]
        self.score = split[2]

        self.name_label: QLabel = QLabel(f'{self.stage}')
        self.score_label: QLabel = QLabel(f'{self.score}')

        self.name_editor: QLineEdit = QLineEdit()
        self.score_editor: QLineEdit = QLineEdit()

        self.name_editor.setPlaceholderText('Stage-69')
        self.score_editor.setPlaceholderText('696969')

        self.name_editor.hide()
        self.score_editor.hide()

        self.name_editor.editingFinished.connect(self.update_split_db)
        self.score_editor.editingFinished.connect(self.update_split_db)

        self.name_editor.returnPressed.connect(self.update_split_db)
        self.score_editor.returnPressed.connect(self.update_split_db)
        self.name_editor.returnPressed.connect(self.toggle_labels)
        self.score_editor.returnPressed.connect(self.toggle_labels)

        self.score_editor.setValidator(QIntValidator())

        layout = QHBoxLayout()
        layout.addWidget(self.name_label)
        layout.addWidget(self.score_label)
        layout.addWidget(self.name_editor)
        layout.addWidget(self.score_editor)

        self.setLayout(layout)

    def toggle_editors(self):
        self.name_label.hide()
        self.score_label.hide()

        name_text = self.name_label.text()
        name_text = name_text.strip(':')

        score_text = self.score_label.text()
        try:
            end = score_text.index('(')
            score_text = score_text[:end]
        except ValueError:
            print('no parenthesis found')
        self.name_editor.setText(name_text)
        self.score_editor.setText(score_text)

        self.name_editor.show()
        self.score_editor.show()

        self.score_editor.setFocus()

    # TODO This is a bit of a slop job. Is there a better way to determine if editor text should be copied?
    #   The problem is sometimes name and editor text is none and will blank out other items.
    def toggle_labels(self):
        parent = self.parent().parent()

        self.name_editor.hide()
        self.score_editor.hide()

        name_text = self.name_editor.text()
        if name_text:
            self.name_label.setText(name_text + ':')

        score_text = self.score_editor.text()
        if score_text:
            self.score_label.setText(score_text)

        self.add_diffs(self.game_db[self.game_name]['splits'], parent)

        self.name_label.show()
        self.score_label.show()

    def update_split_db(self):
        """Update the 'in-memory' copy of the database and save to JSON"""
        # pass
        item_index = self.game_db[self.game_name]['splits'].index(self.split)
        self.game_db[self.game_name]['splits'][item_index][2] = int(self.score_editor.text())
        self.game_db[self.game_name]['splits'][item_index][1] = self.name_editor.text()

        save_pb_to_json(self.game_db)

    def add_diffs(self, splits, parent):
        for index, split in enumerate(splits):
            if index > 0:
                diff = split[2] - splits[index - 1][2]
                list_item = parent.item(index)
                widget_item = parent.itemWidget(list_item)
                widget_item.score_label.setText(str(split[2]) + f'({diff:+d})')
            else:
                list_item = parent.item(index)
                widget_item = parent.itemWidget(list_item)
                widget_item.score_label.setText(str(split[2]))

class SaveStateNameInputValidator(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            # TODO Get rid of match case, there is only one case now.
            match index.column():
                case 0:
                    editor.setMaxLength(10)
                    # TODO Fully understand this regex.
                    pattern = QRegularExpression(r'^[^<>:"/\|?* ]*$')
                    validator = QRegularExpressionValidator(pattern, editor)
                    editor.setValidator(validator)
        return editor

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                watched.insert('-')
                return True

        return super().eventFilter(watched, event)