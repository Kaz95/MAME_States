"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Validate input fields
    * Consider sizing policies and size hints
    * Add Scrollable area to stage splits layout
    * Make High Score page work off user inputted data including:
        - Add games
        - Remove split
        - ect
    * Try to implement the editor options available on treewidget persistent editors.
    * Event filter for handling user input on high score page?
    * Consider 'add new mame folder' functionality.
    * Comment/Code Review/Refactor
    * Decide on new features to add.
"""

from PyQt6.QtCore import Qt, QSize, QRegularExpression, QEvent
from PyQt6.QtGui import QAction, QFont, QRegularExpressionValidator
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QStyledItemDelegate, QLineEdit, \
    QTabWidget, QHBoxLayout, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, \
    QSizePolicy, QInputDialog

from logic.main import build_description_db, mame_paths, get_all_roms_with_saves
from logic.main import get_real_name

class StageSplitItem(QWidget):
    def __init__(self, split):
        super().__init__()

        self.item_index = split[0]
        stage = split[1]
        score = split[2]

        layout = QHBoxLayout()
        self.label = QLabel(f'Stage-{stage}:')
        self.input = QLineEdit(str(score))
        layout.addWidget(self.label)
        layout.addWidget(self.input)

        self.setLayout(layout)



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
        self.split_list = QListWidget()
        # split_list_ploicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # split_list_ploicy.setVerticalPolicy(QSizePolicy.Policy.MinimumExpanding)
        # self.split_list.setSizePolicy(split_list_ploicy)

        self.distance_label = None
        self.high_score_label = None
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

        self.tree_widget = QTreeWidget()
        self.tree_widget.setEditTriggers(QTreeWidget.EditTrigger.AnyKeyPressed)
        self.tree_widget.setHeaderLabels(['MAME Folders'])
        self.tree_widget.setColumnWidth(0, 1000)
        self.tree_widget.setItemDelegate(InputValidator(self))
        self.tree_widget.setTabKeyNavigation(True)
        self.add_mame_path_items()

        self.save_state_page_layout.addWidget(self.tree_widget)

        # High Score Page
        # Parent layout
        self.high_score_page_layout = QHBoxLayout()
        # Contains game list and buttons
        self.game_list_container = QVBoxLayout()
        # Contains PB and Stage splits
        self.info_layout = QVBoxLayout()
        # Contains PB
        self.personal_best_layout = QGridLayout()
        # Contains stage split list and buttons
        self.stage_splits_layout = QGridLayout()
        # contains stage split buttons
        self.splits_tree_button_container = QHBoxLayout()





        self.high_score_edit: QLineEdit | None = None
        self.distance_edit: QLineEdit | None = None

        self.add_split_button = QPushButton('Add Split')
        self.add_split_button.clicked.connect(self.new_split)
        self.delete_split_button = QPushButton('Delete Split')

        self.add_game_button = QPushButton('Add Game')
        self.add_game_button.clicked.connect(self.add_game)

        self.test_game_info = {'DonPachi': {'hs': 900,
                 'distance': 'Stage 6',
                 'splits': [(0, 1, 110), (1, 2, 200), (2, 3, 340), (3, 4, 420), (4, 5, 670), (5, 6, 900)]},

         'Galaga': {'hs': 2000,
                 'distance': 'Stage 3',
                 'splits': [(0, 1, 550), (1, 2, 1620), (2, 3, 2000)]},

         'Libble Rabble': {'hs': 50069,
                 'distance': 'Stage 5',
                 'splits': [(0, 1, 10000), (1, 2, 15069), (2, 3, 25069), (3, 4, 38069), (4, 5, 50069)]}}

        self.high_score_game_tree = QTreeWidget()
        self.high_score_game_tree.setHeaderLabels(['Games'])
        self.high_score_game_tree.itemSelectionChanged.connect(self.high_score_tree_selection_changed)

        for key in self.test_game_info:
            QTreeWidgetItem(self.high_score_game_tree, [key])


        self.game_list_container.addWidget(self.high_score_game_tree)
        self.game_list_container.addWidget(self.add_game_button)

        self.add_pb_panel()
        self.splits_tree_button_container.addWidget(self.add_split_button)
        self.splits_tree_button_container.addWidget(self.delete_split_button)

        # self.high_score_page_layout.addWidget(self.high_score_tree)
        self.high_score_page_layout.addLayout(self.game_list_container)
        self.info_layout.addLayout(self.personal_best_layout)
        self.info_layout.addStretch()
        # self.info_layout.addLayout(self.stage_splits_layout)
        # TODO look into stretch factors
        self.info_layout.addWidget(self.split_list, 1)
        self.info_layout.addStretch()
        self.info_layout.addLayout(self.splits_tree_button_container)
        self.high_score_page_layout.addLayout(self.info_layout)

        self.high_score_page.setLayout(self.high_score_page_layout)
        self.high_score_page.setFont(self.top_level_item_font)

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
    def high_score_tree_selection_changed(self):
        self.split_list.clear()
        # self.clear_splits()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            info = self.test_game_info[game_name]

            hs = info['hs']
            distance = info['distance']

            splits = info['splits']

            self.update_pbs(hs, distance)

            for split in splits:
                self.add_split(split)

    def add_pb_panel(self):
        self.high_score_edit = QLineEdit()
        self.distance_edit = QLineEdit()
        self.high_score_label = QLabel('High Score:')
        self.distance_label = QLabel('Distance PB:')


        self.personal_best_layout.addWidget(self.high_score_label, 0, 0)
        self.personal_best_layout.addWidget(self.high_score_edit, 0, 1)

        self.personal_best_layout.addWidget(self.distance_label, 1, 0)
        self.personal_best_layout.addWidget(self.distance_edit, 1, 1)

    def update_pbs(self, high_score, distance):
        self.high_score_edit.setText(str(high_score))
        self.distance_edit.setText(distance)


    def add_split(self, split):
        split_item = StageSplitItem(split)
        list_item = QListWidgetItem(self.split_list)
        # list_item.setSizeHint(split_item.sizeHint())

        self.split_list.setItemWidget(list_item, split_item)

        # item_index = split[0]
        # stage = split[1]
        # score = split[2]
    #
    #     self.stage_splits_layout.addWidget(QLabel(f'Stage-{stage}:'), item_index, 0)
    #     self.stage_splits_layout.addWidget(QLineEdit(str(score)), item_index, 1)
    #
    # def clear_splits(self):
    #     while self.stage_splits_layout.count():
    #         item = self.stage_splits_layout.takeAt(0)
    #         if item.widget() is not None:
    #             item.widget().deleteLater()
    #
    #
    def new_split(self):
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            game_splits = self.test_game_info[game_name]['splits']
            split_count = len(game_splits)
            new_split = (split_count, split_count + 1, 696969)
            game_splits.append(new_split)
            self.add_split(new_split)

    # TODO add to db or else breaks on selection.
    def add_game(self):
        game_name, ok = QInputDialog.getText(self, 'New Game', 'Please enter new game name.')
        if game_name and ok:
            QTreeWidgetItem(self.high_score_game_tree, [game_name])

        self.test_game_info[game_name] = {'hs': '',
                                          'distance': '',
                                          'splits': []}

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
