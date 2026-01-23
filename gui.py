"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Reactivate file renaming eventually.
    * Consider sizing policies and size hints
    * Decide on new features to add.
"""
import json
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QFont, QIntValidator
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QLineEdit, \
    QTabWidget, QHBoxLayout, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, \
    QInputDialog, QFileDialog, QMessageBox

from custom.widgets import ToggleableLabel, StageSplitListWidget, StageSplitItem, SaveStateNameInputValidator
from logic.main import build_description_db, paths_db, get_all_roms_with_saves, save_pb_to_json, \
    generate_rom_list, save_raw_paths_to_json, raw_mame_paths, get_raw_paths, load_game_info
from logic.main import get_real_name, test_pb_info, pb_db, rom_db, load_paths_from_json


# TODO Docstrings for instance variables.
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

        self.text_before_editing: str | None = None
        """Text of the previous selected save state item."""

        self.description_db: dict[str, str] = {}
        """Maps a roms long name to its short name in the format: \n{'description': 'rom'}"""

        self.all_save_states: dict[str:dict[str:list[str]]] | None = None
        """Names of games that have a save folder, and their respective save states"""

        # Build sample paths DB if it's not already there.
        if not paths_db.is_file():
            save_raw_paths_to_json(raw_mame_paths)

        self.mame_paths: list[Path] = load_paths_from_json()
        """List of all MAME directories that will be used by the application."""

        # Create rom list if it doesn't already exist.
        if not rom_db.is_file():
            if self.mame_paths:
                generate_rom_list(self.mame_paths[0])

        if not pb_db.is_file():
            with open(pb_db, 'w') as db:
                json.dump(test_pb_info, db, indent=4)

        self.test_game_info = load_game_info()

        self.fill_data_structures()

        # Widget customization
        self.setWindowTitle('MAME States')

        self.top_level_item_font: QFont = QFont()
        """Large font"""
        self.top_level_item_font.setPointSize(26)

        self.sub_item_font: QFont = QFont()
        """Small font"""
        self.sub_item_font.setPointSize(20)

        # --------- #
        # File Menu #
        # --------- #
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('&File')

        self.button_1_action: QAction = QAction('button 1', self)
        self.button_2_action: QAction = QAction('button 2', self)
        self.button_3_action: QAction = QAction('Add MAME Path', self)

        self.setup_file_menu()

        # Tabs
        self.tabs: QTabWidget = QTabWidget()
        """Tab container"""
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)

        # Pages
        self.save_state_page: QWidget = QWidget()
        self.high_score_page: QWidget = QWidget()

        # ------------------ #
        #   Save State Page  #
        # ------------------ #

        # Widgets
        self.save_state_tree: QTreeWidget = QTreeWidget()
        """Main widget of the save state tab"""
        self.save_state_tree.setEditTriggers(QTreeWidget.EditTrigger.AnyKeyPressed)
        self.save_state_tree.setHeaderLabels(['MAME Folders'])
        self.save_state_tree.setColumnWidth(0, 1000)
        self.save_state_tree.setItemDelegate(SaveStateNameInputValidator(self))
        self.save_state_tree.setTabKeyNavigation(True)
        self.add_mame_path_items()

        # Layouts
        self.save_state_page_layout: QHBoxLayout = QHBoxLayout()
        self.save_state_page_layout.setContentsMargins(0, 0, 0, 0)
        self.save_state_page.setLayout(self.save_state_page_layout)
        self.save_state_page_layout.addWidget(self.save_state_tree)

        # Signals and Slots
        # TODO If these aren't connected after filling treewidget, everything's fucked. Look into it.
        self.save_state_tree.currentItemChanged.connect(self.save_state_tree_selection_changed)
        self.save_state_tree.itemChanged.connect(self.save_state_tree_item_changed)

        # ------------------#
        #   Highscore Page  #
        # ------------------#

        # Widgets
        self.distance_label: QLabel = QLabel('Distance PB:')
        self.high_score_label: QLabel = QLabel('High Score:')

        self.high_score_edit: QLineEdit = QLineEdit()
        self.distance_edit: QLineEdit = QLineEdit()

        self.distance_value_label = ToggleableLabel(self.distance_edit)
        self.high_score_value_label = ToggleableLabel(self.high_score_edit)

        self.high_score_game_tree: QTreeWidget = QTreeWidget()
        self.add_game_button: QPushButton = QPushButton('Add Game')

        self.split_list: StageSplitListWidget = StageSplitListWidget(self.test_game_info)
        self.add_split_button: QPushButton = QPushButton('Add Split')
        self.delete_split_button: QPushButton = QPushButton('Delete Split')

        # Fill widgets
        for key in self.test_game_info:
            QTreeWidgetItem(self.high_score_game_tree, [key])

        # Layouts
        # Parent layout
        self.high_score_page_layout: QHBoxLayout = QHBoxLayout()
        # Contains game list and buttons
        self.game_list_container: QVBoxLayout = QVBoxLayout()
        # Contains PB and Stage splits
        self.info_layout: QVBoxLayout = QVBoxLayout()
        # Contains PB
        self.personal_best_layout: QGridLayout = QGridLayout()
        # Contains stage split list and buttons
        self.stage_splits_layout: QGridLayout = QGridLayout()
        # contains stage split buttons
        self.splits_tree_button_container: QHBoxLayout = QHBoxLayout()

        # Add widgets to layout. Setup signals and slots.
        self.setup_highscore_panel()
        self.setup_pb_panel()
        self.setup_split_panel()

        # TODO look into stretch factors
        self.info_layout.addLayout(self.personal_best_layout)
        self.info_layout.addStretch()

        self.info_layout.addWidget(self.split_list, 1)
        self.info_layout.addStretch()

        self.info_layout.addLayout(self.splits_tree_button_container)

        self.high_score_page_layout.addLayout(self.game_list_container)
        self.high_score_page_layout.addLayout(self.info_layout)
        self.high_score_page.setLayout(self.high_score_page_layout)
        self.high_score_page.setFont(self.top_level_item_font)

        # Add tabs to tab container
        self.tabs.addTab(self.save_state_page, 'Save States')
        self.tabs.addTab(self.high_score_page, 'High Scores')
        self.setCentralWidget(self.tabs)

    # Methods
    def sizeHint(self):
        return QSize(1920, 1080)

    def setup_file_menu(self):
        self.button_1_action.triggered.connect(self.menu_button_1_clicked)
        self.button_2_action.triggered.connect(self.menu_button_2_clicked)
        self.button_3_action.triggered.connect(self.add_path_button_clicked)

        self.file_menu.addAction(self.button_1_action)
        self.file_menu.addAction(self.button_2_action)
        self.file_menu.addAction(self.button_3_action)

    def setup_highscore_panel(self):
        self.high_score_game_tree.setHeaderLabels(['Games'])
        self.high_score_game_tree.itemSelectionChanged.connect(self.high_score_tree_selection_changed)

        self.add_game_button.clicked.connect(self.add_game)

        self.game_list_container.addWidget(self.high_score_game_tree)
        self.game_list_container.addWidget(self.add_game_button)

    def setup_pb_panel(self):
        self.high_score_edit.setValidator(QIntValidator())
        self.high_score_edit.editingFinished.connect(self.update_high_score_pb)

        self.distance_edit.editingFinished.connect(self.update_distance_pb)

        self.personal_best_layout.addWidget(self.high_score_label, 0, 0)
        self.personal_best_layout.addWidget(self.high_score_edit, 0, 1)
        self.personal_best_layout.addWidget(self.high_score_value_label, 0, 1)

        self.personal_best_layout.addWidget(self.distance_label, 1, 0)
        self.personal_best_layout.addWidget(self.distance_edit, 1, 1)
        self.personal_best_layout.addWidget(self.distance_value_label, 1, 1)

    def setup_split_panel(self):
        self.splits_tree_button_container.addWidget(self.add_split_button)
        self.splits_tree_button_container.addWidget(self.delete_split_button)

        self.split_list.itemDoubleClicked.connect(self.split_double_clicked)
        self.split_list.currentItemChanged.connect(self.split_current_item_changed)

        self.add_split_button.clicked.connect(self.new_split)
        self.delete_split_button.clicked.connect(self.delete_split)

    def update_pb_panel(self, high_score, distance):
        self.high_score_edit.setText(str(high_score))
        self.distance_edit.setText(distance)
        self.high_score_value_label.setText(str(high_score))
        self.distance_value_label.setText(distance)
        self.high_score_edit.hide()
        self.distance_edit.hide()



    def add_split(self, split, game_name):
        split_item = StageSplitItem(split, self.test_game_info, game_name, self.split_list)
        list_item = QListWidgetItem(self.split_list)
        self.split_list.setItemWidget(list_item, split_item)
        return list_item

    def add_diffs(self, splits):
        for index, split in enumerate(splits):
            if index > 0:
                diff = split[2] - splits[index - 1][2]
                print(diff)
                list_item = self.split_list.item(index)
                widget_item = self.split_list.itemWidget(list_item)
                widget_item.score_label.setText(widget_item.score_label.text() + f'(+{diff})')

    def valid_path(self, mame_folder: Path):
        mame_exe = mame_folder / 'mame.exe'
        if not mame_exe.is_file():
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
        mame_folder = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                       options=QFileDialog.Option.ShowDirsOnly)

        mame_folder = Path(mame_folder)

        res = self.valid_path(mame_folder)
        if res is True:
            return mame_folder
        if res is False:
            self.get_mame_path()

        return res

    def fill_data_structures(self) -> None:
        """Reset and refill data structures used to derive TreeWidget items.

        Reset the data structures used to fill the tree widget. Then, fill them again. Used for both initial filling of
        TreeWidget, and the reloading of the TreeWidget when a new MAME path is chosen.
        """
        self.description_db = build_description_db(rom_db)
        self.all_save_states = get_all_roms_with_saves(self.mame_paths)

    def add_mame_path_items(self):
        self.save_state_tree.clear()

        for path in self.mame_paths:
            path_item = QTreeWidgetItem(self.save_state_tree, [str(path)])
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
    def new_split(self):
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            game_splits = self.test_game_info[game_name]['splits']
            split_count = len(game_splits)
            new_split = [split_count, '', 0]
            game_splits.append(new_split)
            new_item = self.add_split(new_split, game_name)
            self.split_list.setCurrentItem(new_item)
            self.split_double_clicked(new_item)
            save_pb_to_json(self.test_game_info)

    def add_game(self):
        game_name, ok = QInputDialog.getText(self, 'New Game', 'Please enter new game name.')
        if game_name and ok:
            QTreeWidgetItem(self.high_score_game_tree, [game_name])

            self.test_game_info[game_name] = {'hs': '',
                                              'distance': '',
                                              'splits': []}
            save_pb_to_json(self.test_game_info)

    def delete_split(self):
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            row = self.split_list.currentRow()
            if row != -1:
                self.split_list.takeItem(row)
                splits = self.test_game_info[game_name]['splits']
                del splits[row]
                save_pb_to_json(self.test_game_info)

    # TODO re-enable file renaming after ensuring user input is properly sanitized.
    def save_state_tree_item_changed(self, save_state_item: QTreeWidgetItem):
        if save_state_item.childCount() == 0:
            save_state_name = save_state_item.text(0)
            print(save_state_name)
            game_item = save_state_item.parent()
            game_name = game_item.text(0)

            rom_name = self.description_db[game_name]

            mame_path_item = game_item.parent()
            mame_path = mame_path_item.text(0)

            # print(f'save state: {save_state_name}')
            # print(f'game name: {rom_name}')
            # print(f'mame path: {mame_path}')
            # rename(mame_path, rom_name, self.text_before_editing, save_state_name)

            # print(f'An item was changed from {self.text_before_editing}, to {save_state_item.text(0)}')

    def save_state_tree_selection_changed(self, current_item: QTreeWidgetItem):
        self.text_before_editing = current_item.text(0)

    def high_score_tree_selection_changed(self):
        """Clear and refill 'splits list' based on currently selected item."""
        self.split_list.clear()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            info = self.test_game_info[game_name]

            hs = info['hs']
            distance = info['distance']
            splits = info['splits']

            self.update_pb_panel(hs, distance)

            for split in splits:
                self.add_split(split, game_name)

            self.add_diffs(splits)

    def split_double_clicked(self, item: QListWidgetItem):
        widget_item = self.split_list.itemWidget(item)
        widget_item.toggle_editors()

    def split_current_item_changed(self, cur: QListWidgetItem, prev: QListWidgetItem):
        if prev:
            widget_item = self.split_list.itemWidget(prev)
            widget_item.toggle_labels()

    def update_high_score_pb(self):
        """Updates in memory DB and saves to JSON"""
        new_pb = int(self.high_score_edit.text())
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.test_game_info[game_name]['hs'] = new_pb
            save_pb_to_json(self.test_game_info)

    def update_distance_pb(self):
        """Updates in memory DB and saves to JSON"""
        new_pb = self.distance_edit.text()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.test_game_info[game_name]['distance'] = new_pb
            save_pb_to_json(self.test_game_info)

    def menu_button_1_clicked(self) -> None:
        self.save_state_tree.hide()

    def menu_button_2_clicked(self) -> None:
        self.save_state_tree.show()

    # TODO Same problem here I have to disconnect and reconnect slot to avoid breaking shit. Look into it.
    def add_path_button_clicked(self) -> None:
        path = self.get_mame_path()
        if path:
            self.mame_paths.append(path)
            raw_paths = get_raw_paths(self.mame_paths)
            save_raw_paths_to_json(raw_paths)
            self.all_save_states = get_all_roms_with_saves(self.mame_paths)
            self.save_state_tree.itemChanged.disconnect(self.save_state_tree_item_changed)
            self.add_mame_path_items()
            self.save_state_tree.itemChanged.connect(self.save_state_tree_item_changed)
            # print(f'New MAME path: {path}')
        # else:
        #     print('Cancel chosen')


if __name__ == '__main__':
    # The order the objects are initialized in matters.
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
