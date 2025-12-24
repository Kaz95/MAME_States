"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Disallow spaces in save state names. Maybe replace space with hyphen before saving?
        Do I need to disallow any other characters? Should I limit length(file name length limit)?
    * Comment/Code Review/Refactor
    * Decide on new features to add.
"""

import os.path

from PyQt6.QtCore import Qt, QSize, QRegularExpression, QObject, QEvent
from PyQt6.QtGui import QAction, QFont, QRegularExpressionValidator, QIntValidator, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, \
    QStyledItemDelegate, QLineEdit

from logic.main import change_mame_path, build_description_db
from logic.main import get_roms_with_saves, get_save_names, get_real_name, rename, create_rom_list
class EditorKeyFilter(QObject):
    def eventFilter(self, widget, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                print('Enter pressed')
                # TODO DO shit here
                # self.parent().commitData.emit(widget)
                # return True
        return super().eventFilter(widget, event)


class InputValidator(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent ,option ,index)
        editor_filter = EditorKeyFilter(self)
        editor.installEventFilter(editor_filter)
        if isinstance(editor, QLineEdit):
            match index.column():
                case 0:
                    editor.setMaxLength(10)
                    # TODO Fully understand this regex.
                    pattern = QRegularExpression(r'^[^<>:"/\|?*]*$')
                    validator = QRegularExpressionValidator(pattern, editor)
                    editor.setValidator(validator)
                case 1:
                    editor.setMaxLength(10)
                    validator = QIntValidator(editor)
                    editor.setValidator(validator)
                case 2:
                    editor.setMaxLength(20)

        return editor

class TreeWidget(QTreeWidget):
    """Subclasses and extends the QTreeWidget class of the PyQt6.QtWidgets Module

    This class extends the keyPressEvent method for the purposes of capturing a custom key press
    """

    def __init__(self, mame_folder: str, description_db: dict[str, str]):
        """Initialize the TreeWidget Subclass

        The TreeWidget subclass inherits most of its behavior from its parent class QTreeWidget.
        TreeWidget initializes with all the data needed by its single extended method
        """
        super().__init__()

        self.mame_folder = mame_folder
        """Path to base MAME folder."""

        self.description_db = description_db
        """Maps a roms long name to its short name in the format: \n{'description': 'rom'}"""

    # def keyPressEvent(self, event):
    #     """Extended key press event handler
    #
    #     Extends key press event handler to capture 'enter' and 'return'. If the key press event is triggered,
    #     the currently selected QTreeWidgetItem will have its editor closed, the corresponding save file will be
    #     renamed, and the event will be marked as handled. If the key press is not triggered, the event will be handled
    #     by the parent method.
    #     """
    #     # Capturing both return and enter is important for compatibility
    #     if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
    #         selected_items = self.selectedItems()
    #         if selected_items:
    #             for item in selected_items:
    #                 if self.isPersistentEditorOpen(item):
    #                     rom_item = item.parent()
    #                     rom_name = self.description_db[rom_item.text(0)]
    #                     old_text = item.text(0)
    #                     self.closePersistentEditor(item)
    #                     # TODO add user input validation here. If invalid input, rollback. Use message box.
    #                     rename(self.mame_folder, rom_name, old_text, item.text(0))
    #
    #         # Mark event as handled if the given keys were pressed.
    #         # Only do this if you want to override existing behavior of a given keybind.
    #         event.accept()
    #     # Pass to normal event handler if the given keys were not pressed.
    #     else:
    #         super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """Subclasses and extends the QQMainWindow class of the PyQt6.QtWidgets Module

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Houses all GUI elements of the MAMEStates application.
    """

    def __init__(self):
        """Initialize the MainWindow subclass

        The MainWindow subclass inherits most of its behavior from, and extends, its parent class QMainWindow. The
        initialization process setups the GUI elements present on program launch, as well as connecting signals to
        slots. In addition, the initialization process also creates persistent files required by the MAMEStates
        application.
        """
        super().__init__()

        self.mame_folder = None
        """Path to base MAME folder."""

        self.tree_widget = None

        self.text_before_editing: str | None = None
        """Text of a TreeWidget item, before a persistent editor was opened."""

        self.prev: QTreeWidgetItem | None = None
        """The previously selected TreeWidget item."""

        self.description_db: dict[str, str] = {}
        """Maps a roms long name to its short name in the format: \n{'description': 'rom'}"""

        self.real_names: list[str] = []
        """Long-form rom names."""

        # Need these references to assign sub items later.
        self.game_items: list[QTreeWidgetItem] = []
        """Top level TreeWidget items, representing games with save states."""

        self.saves: dict[str, list[str]] | None = None
        """Names of games that have a save folder, and their respective save states"""


        self.mame_folder = self.get_mame_path()

        if self.mame_folder is not None:
            self.fill_data_structures()

            # Widget customization
            self.setWindowTitle('MAME States')
            self.top_level_item_font = QFont()
            self.top_level_item_font.setPointSize(26)
            self.sub_item_font = QFont()
            self.sub_item_font.setPointSize(20)
            self.tree_widget = TreeWidget(self.mame_folder, self.description_db)
            self.tree_widget.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
            self.tree_widget.setHeaderLabels(['Games', 'High Score', 'Distance PB'])
            self.tree_widget.setColumnWidth(0, 1000)
            self.tree_widget.setItemDelegate(InputValidator(self))
            # All widgets without parents are top level and invisible. Requires .show() or assigning parent.
            self.setCentralWidget(self.tree_widget)  # Assigns MainWindow as parent, thus showing tree_widget.

            # Fill TreeWidget
            self.add_top_level_items()
            self.add_sub_items()

            # Signals
            self.tree_widget.itemDoubleClicked.connect(self.item_double_clicked)
            # self.tree_widget.currentItemChanged.connect(self.selection_changed)

        # Add file menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('&File')

        self.button_action = QAction('Add MAME Path', self)
        self.button_action.triggered.connect(self.menu_button_clicked)

        self.file_menu.addAction(self.button_action)

    # Methods
    def sizeHint(self):
        return QSize(1920, 1080)

    def valid_path(self, mame_folder):
        mame_exe = mame_folder + '\\mame.exe'
        if not os.path.exists(mame_exe):
            message_response = QMessageBox.critical(self,
                                                    'Path Invalid',
                                                    'Please choose a valid MAME folder.',
                                                    QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel)
            if message_response == QMessageBox.StandardButton.Retry:
                return False
            if message_response == QMessageBox.StandardButton.Cancel:
                return None
        else:
            return True

    def get_mame_path(self):
        if os.path.isfile('logic/romlist.txt'):
            with open('logic/romlist.txt', 'r') as romlist:
                first_line = romlist.readline()
                mame_folder = first_line.strip()
                return mame_folder
        else:
            mame_folder = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                                options=QFileDialog.Option.ShowDirsOnly)
            res = self.valid_path(mame_folder)
            if res is True:
                create_rom_list(mame_folder)
                change_mame_path(mame_folder)
                return mame_folder
            if res is False:
                self.get_mame_path()

            return res

    def fill_data_structures(self) -> None:
        """Reset and refill data structures used to derive TreeWidget items.

        Reset the data structures used to fill the tree widget. Then, fill them again. Used for both initial filling of
        TreeWidget, and the reloading of the TreeWidget when a new MAME path is chosen.
        """
        # reset data structs
        self.real_names = []
        self.description_db = build_description_db('logic/romlist.txt')
        self.game_items = []

        #  Fill out data structures for later use.
        roms_with_saves = get_roms_with_saves(self.mame_folder)

        for rom in roms_with_saves:
            real_name = get_real_name(self.description_db, rom)
            self.real_names.append(real_name)

        self.saves = get_save_names(roms_with_saves, self.mame_folder)

    def add_sub_items(self) -> None:
        """Add a sub items to a top level items of the TreeWidget.

        Use pre-filled data structures to create a sub item referencing each save state's name as text, with the top
        level tree item representing its corresponding rom as a parent item.
        """
        for game in self.game_items:
            if game.text(0) in self.description_db:
                rom_name = self.description_db[game.text(0)]
                if rom_name in self.saves:
                    for state in self.saves[rom_name]:
                        item = QTreeWidgetItem(game, [state])
                        item.setFirstColumnSpanned(True)
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                        item.setFont(0, self.sub_item_font)

    def add_top_level_items(self) -> None:
        """Create, and capture a reference to, top level items in the TreeWidget.

        Each top level item represents a rom. The text of each top level item is the long form name of a rom. The items
        created are captured in a list as references for later use. Primarily the addition of sub items(save states) at
        a later time.
        """
        for game in self.real_names:
            game_item = QTreeWidgetItem(self.tree_widget, [game])
            # game_item.setFlags(game_item.flags() | Qt.ItemFlag.ItemIsEditable)
            game_item.setFont(0, self.top_level_item_font)
            self.game_items.append(game_item)

    def update_treewidget(self) -> None:
        """Update the data structures the TreeWidget derives its items from."""
        self.tree_widget.description_db = self.description_db
        self.tree_widget.mame_folder = self.mame_folder

    # Slots
    def menu_button_clicked(self) -> None:
        """Change active MAME directory and reload TreeWidget.

        Open a full file dialog window and have user choose a MAME base directory. Only directories may be chosen. Then,
        the TreeWidget is cleared and reloaded with data from the new MAME directory.
        """
        mame_path = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                     options=QFileDialog.Option.ShowDirsOnly)
        res = self.valid_path(mame_path)
        if res is True:
            self.mame_folder = mame_path

            create_rom_list(self.mame_folder)
            change_mame_path(mame_path)
            self.fill_data_structures()
            if self.tree_widget:
                self.tree_widget.clear()
            else:
                self.tree_widget = TreeWidget(self.mame_folder, self.description_db)
                self.tree_widget.setHeaderLabels(['Games'])
                self.setCentralWidget(self.tree_widget)
                self.tree_widget.itemDoubleClicked.connect(self.item_double_clicked)
                self.tree_widget.currentItemChanged.connect(self.selection_changed)

            self.update_treewidget()
            self.add_top_level_items()
            self.add_sub_items()

            print('clicked', mame_path)
        if res is False:
            self.menu_button_clicked()

    def item_double_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        """Open text editor on a subitem of TreeWidget.

        Capture the previous text of the given sub item before opening the editor. This allows the items text to be
        reverted. All top level items have their sub items collapsed, except for the top level item that is the parent
        of the currently selected item.
        """
        if item.parent() is not None:
            self.text_before_editing = item.text(0)
            self.tree_widget.editItem(item, col)
        else:
            if col in (1, 2):
                self.tree_widget.editItem(item, col)

        # close all expanded child items except for the parent of the current selected item.
        for item in self.game_items:
            if item.isExpanded() and not item.isSelected() and self.tree_widget.selectedItems()[0].parent() != item:
                self.tree_widget.collapseItem(item)

    # # On program load, prev is always None, and cur is first item.
    # def selection_changed(self, cur: QTreeWidgetItem, prev: QTreeWidgetItem) -> None:
    #     """Revert text change on previously selected subitem of TreeWidget."""
    #     if prev and cur:
    #         if prev.parent():
    #             if self.text_before_editing:
    #                 prev.setText(0, self.text_before_editing)
    #         self.tree_widget.closePersistentEditor(prev)


if __name__ == '__main__':
    # The order the objects are initialized in matters.
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
