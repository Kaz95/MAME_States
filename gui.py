"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * What happens if JSON file doesn't already exist on program load? Fix.
    * Validate input fields
    * Consider sizing policies and size hints
    * Consider 'add new mame folder' functionality.
    * Comment/Code Review/Refactor
    * Decide on new features to add.
"""
import json
import os.path
import pprint

from PyQt6.QtCore import Qt, QSize, QRegularExpression, QEvent
from PyQt6.QtGui import QAction, QFont, QRegularExpressionValidator, QIntValidator
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QStyledItemDelegate, QLineEdit, \
    QTabWidget, QHBoxLayout, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, \
    QSizePolicy, QInputDialog

from logic.main import build_description_db, mame_paths, get_all_roms_with_saves, save_game_info
from logic.main import get_real_name, rename, get_roms_from_paths, new_create_rom_list, mame_paths, test_game_info



class StageSplitItem(QWidget):
    def __init__(self, split, game_db, game_name):
        super().__init__()
        self.game_db = game_db
        self.game_name = game_name
        self.item_index = split[0]
        stage = split[1]
        score = split[2]

        layout = QHBoxLayout()
        self.label = QLabel(f'Stage-{stage}:')
        self.input = QLineEdit(str(score))

        self.input.editingFinished.connect(self.update_split_db)

        self.input.setValidator(QIntValidator())
        layout.addWidget(self.label)
        layout.addWidget(self.input)

        self.setLayout(layout)

    def update_split_db(self):
        print(self.input.text())
        self.game_db[self.game_name]['splits'][self.item_index][2] = int(self.input.text())
        save_game_info(self.game_db)
        print(self.game_db[self.game_name]['splits'][self.item_index][2])

class SaveStateNameInputValidator(QStyledItemDelegate):
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

        self.text_before_editing = None
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

        # Create romlist if it doesnt already exist.
        if not os.path.isfile('logic/rom_list.txt'):
            roms = get_roms_from_paths(mame_paths)
            new_create_rom_list(roms)

        if not os.path.isfile('game_db.json'):
            with open('game_db.json', 'w') as game_db:
                json.dump(test_game_info, game_db, indent=4)

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
        self.tree_widget.setItemDelegate(SaveStateNameInputValidator(self))
        self.tree_widget.setTabKeyNavigation(True)



        self.add_mame_path_items()

        self.save_state_page_layout.addWidget(self.tree_widget)

        # TODO If these aren't connected after filling treewidget, everything's fucked. Look into it.
        self.tree_widget.currentItemChanged.connect(self.save_state_tree_selection_changed)
        self.tree_widget.itemChanged.connect(self.save_state_tree_item_changed)


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
        self.delete_split_button.clicked.connect(self.delete_split)

        self.add_game_button = QPushButton('Add Game')
        self.add_game_button.clicked.connect(self.add_game)

        with open('game_db.json', 'r') as game_info:
            game_dict = json.load(game_info)
            self.test_game_info = game_dict

        # pprint.pprint(self.test_game_info)

        # self.test_game_info = {'DonPachi': {'hs': 900,
        #          'distance': 'Stage 6',
        #          'splits': [[0, 1, 110], [1, 2, 200], [2, 3, 340], [3, 4, 420], [4, 5, 670], [5, 6, 900]]},
        #
        #  'Galaga': {'hs': 2000,
        #          'distance': 'Stage 3',
        #          'splits': [[0, 1, 550], [1, 2, 1620], [2, 3, 2000]]},
        #
        #  'Libble Rabble': {'hs': 50069,
        #          'distance': 'Stage 5',
        #          'splits': [[0, 1, 10000], [1, 2, 15069], [2, 3, 25069], [3, 4, 38069], [4, 5, 50069]]}}

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
                self.add_split(split, game_name)

    def add_pb_panel(self):
        self.high_score_edit = QLineEdit()
        # TODO persist this with an update_distance_pb() function
        self.distance_edit = QLineEdit()

        self.high_score_edit.setValidator(QIntValidator())
        self.high_score_edit.editingFinished.connect(self.update_high_score_pb)

        self.distance_edit.editingFinished.connect(self.update_distance_pb)

        self.high_score_label = QLabel('High Score:')
        self.distance_label = QLabel('Distance PB:')


        self.personal_best_layout.addWidget(self.high_score_label, 0, 0)
        self.personal_best_layout.addWidget(self.high_score_edit, 0, 1)

        self.personal_best_layout.addWidget(self.distance_label, 1, 0)
        self.personal_best_layout.addWidget(self.distance_edit, 1, 1)

    def update_pbs(self, high_score, distance):
        self.high_score_edit.setText(str(high_score))
        self.distance_edit.setText(distance)


    def add_split(self, split, game_name):
        split_item = StageSplitItem(split, self.test_game_info, game_name)
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
            self.add_split(new_split, game_name)
            save_game_info(self.test_game_info)

    # TODO add to db or else breaks on selection.
    def add_game(self):
        game_name, ok = QInputDialog.getText(self, 'New Game', 'Please enter new game name.')
        if game_name and ok:
            QTreeWidgetItem(self.high_score_game_tree, [game_name])

        self.test_game_info[game_name] = {'hs': '',
                                          'distance': '',
                                          'splits': []}
        save_game_info(self.test_game_info)


    def delete_split(self):
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            print(game_name)
            row = self.split_list.currentRow()
            print(row)
            if row != -1:
                # self.split_list.removeItemWidget(split)
                self.split_list.takeItem(row)
                splits = self.test_game_info[game_name]['splits']
                del splits[row]
                save_game_info(self.test_game_info)
                print(splits)

    def save_state_tree_selection_changed(self, cur: QTreeWidgetItem, prev: QTreeWidgetItem):
        self.text_before_editing = cur.text(0)

    # TODO re-enable file renaming after ensuring user input is properly sanitized.
    def save_state_tree_item_changed(self, save_state_item: QTreeWidgetItem):
        if save_state_item.childCount() == 0:
            save_state_name = save_state_item.text(0)

            game_item = save_state_item.parent()
            game_name = game_item.text(0)

            rom_name = self.description_db[game_name]

            mame_path_item = game_item.parent()
            mame_path = mame_path_item.text(0)

            print(f'save state: {save_state_name}')
            print(f'game name: {rom_name}')
            print(f'mame path: {mame_path}')
            # rename(mame_path, rom_name, self.text_before_editing, save_state_name)

            print(f'An item was changed from {self.text_before_editing}, to {save_state_item.text(0)}')
        # selected_items = self.tree_widget.selectedItems()
        # if selected_items:
        #     selected = selected_items[0]
        #     if selected.childCount() == 0:
        #         print(selected.text(0))
        #         game_item = selected.parent()
        #         mame_path_item = game_item.parent()
        #
        #         mame_path = mame_path_item.text(0)
        #         game_name = game_item.text(0)
        #         print(mame_path)
        #         print(game_name)


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
    def update_high_score_pb(self):
        new_pb = int(self.high_score_edit.text())
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.test_game_info[game_name]['hs'] = new_pb
            save_game_info(self.test_game_info)

    def update_distance_pb(self):
        new_pb = self.distance_edit.text()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.test_game_info[game_name]['distance'] = new_pb
            save_game_info(self.test_game_info)

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
