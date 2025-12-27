"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Comment/Code Review/Refactor
    * Decide on new features to add.
"""

from PyQt6.QtCore import Qt, QSize, QRegularExpression, QEvent
from PyQt6.QtGui import QAction, QFont, QRegularExpressionValidator
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QStyledItemDelegate, QLineEdit, \
    QTabWidget, QHBoxLayout, QWidget

from logic.main import build_description_db, mame_paths, get_all_roms_with_saves
from logic.main import get_real_name


class InputValidator(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent ,option ,index)
        if isinstance(editor, QLineEdit):
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

        self.description_db: dict[str, str] = {}
        """Maps a roms long name to its short name in the format: \n{'description': 'rom'}"""

        self.all_save_states: dict[str:dict[str:list[str]]] | None = None
        """Names of games that have a save folder, and their respective save states"""

        self.mame_paths:list[str] = mame_paths


        self.fill_data_structures()

        # Widget customization
        self.setWindowTitle('MAME States')
        self.top_level_item_font = QFont()
        self.top_level_item_font.setPointSize(26)
        self.sub_item_font = QFont()
        self.sub_item_font.setPointSize(20)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.save_state_page = QWidget()
        self.high_score_page = QWidget()

        self.tabs.setMovable(True)

        self.save_state_page_layout = QHBoxLayout()
        self.save_state_page_layout.setContentsMargins(0, 0, 0, 0)
        self.save_state_page.setLayout(self.save_state_page_layout)

        high_score_page_layout = QHBoxLayout()
        self.high_score_page.setLayout(high_score_page_layout)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setEditTriggers(QTreeWidget.EditTrigger.AnyKeyPressed)
        self.tree_widget.setHeaderLabels(['Games'])
        self.tree_widget.setColumnWidth(0, 1000)
        self.tree_widget.setItemDelegate(InputValidator(self))
        self.tree_widget.setTabKeyNavigation(True)
        self.add_mame_path_items()

        self.save_state_page_layout.addWidget(self.tree_widget)
        self.tabs.addTab(self.save_state_page, 'Save States')

        self.tabs.addTab(self.high_score_page, 'High Scores')

        self.setCentralWidget(self.tabs)

        # Add file menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('&File')

        self.button_1_action = QAction('button 1', self)
        self.button_1_action.triggered.connect(self.menu_button_1_clicked)

        self.button_2_action = QAction('button 2', self)
        self.button_2_action.triggered.connect(self.menu_button_2_clicked)

        self.file_menu.addAction(self.button_1_action)
        self.file_menu.addAction(self.button_2_action)

    # Methods

    def sizeHint(self):
        return QSize(1920, 1080)

    # def valid_path(self, mame_folder):
    #     mame_exe = mame_folder + '\\mame.exe'
    #     if not os.path.exists(mame_exe):
    #         message_response = QMessageBox.critical(self,
    #                                                 'Path Invalid',
    #                                                 'Please choose a valid MAME folder.',
    #                                                 QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel)
    #         if message_response == QMessageBox.StandardButton.Retry:
    #             return False
    #         if message_response == QMessageBox.StandardButton.Cancel:
    #             return None
    #     else:
    #         return True

    # def get_mame_path(self):
    #     if os.path.isfile('logic/romlist.txt'):
    #         with open('logic/romlist.txt', 'r') as romlist:
    #             first_line = romlist.readline()
    #             mame_folder = first_line.strip()
    #             return mame_folder
    #     else:
    #         mame_folder = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
    #                                                             options=QFileDialog.Option.ShowDirsOnly)
    #         res = self.valid_path(mame_folder)
    #         if res is True:
    #             create_rom_list(mame_folder)
    #             change_mame_path(mame_folder)
    #             return mame_folder
    #         if res is False:
    #             self.get_mame_path()
    #
    #         return res

    def fill_data_structures(self) -> None:
        """Reset and refill data structures used to derive TreeWidget items.

        Reset the data structures used to fill the tree widget. Then, fill them again. Used for both initial filling of
        TreeWidget, and the reloading of the TreeWidget when a new MAME path is chosen.
        """
        # reset data structs

        self.description_db = build_description_db('logic/rom_list.txt')
        self.all_save_states = get_all_roms_with_saves(mame_paths)

    def add_mame_path_items(self):
        for path in mame_paths:
            path_item = QTreeWidgetItem(self.tree_widget, [path])
            path_item.setFont(0, self.top_level_item_font)
            for key in self.all_save_states[path]:
                game_name = get_real_name(self.description_db, key)
                game_item = QTreeWidgetItem(path_item, [game_name])
                game_item.setFont(0, self.top_level_item_font)
                for save_state in self.all_save_states[path][key]:
                    save_state_item = QTreeWidgetItem(game_item, [save_state])
                    save_state_item.setFlags(save_state_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    save_state_item.setFont(0, self.sub_item_font)

    # # Slots
    def menu_button_1_clicked(self) -> None:
        self.tree_widget.hide()
        print('button 1 triggered')

    def menu_button_2_clicked(self):
        self.tree_widget.show()
        print('button 2 triggered')


if __name__ == '__main__':
    # The order the objects are initialized in matters.
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
