"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Reactivate file renaming eventually.
    * Consider sizing policies and size hints
    * Decide on new features to add.
"""
import json
import subprocess
from pathlib import Path
from time import gmtime

from PyQt6.QtCore import Qt, QSize, QStringListModel, QSortFilterProxyModel, QTimer, QPoint
from PyQt6.QtGui import QAction, QFont, QIntValidator
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QLineEdit, \
    QTabWidget, QHBoxLayout, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QListWidgetItem, \
    QInputDialog, QFileDialog, QMessageBox, QListView, QMenu

from custom.widgets import ToggleableLabel, StageSplitListWidget, StageSplitItem, SaveStateNameInputValidator, \
    NotesWindow
from logic.main import build_description_db, paths_db, get_all_roms_with_saves, save_pb_to_json, \
    generate_rom_list, save_raw_paths_to_json, raw_mame_paths, get_raw_paths, load_game_info, PersonalBestDataBase
from logic.main import get_real_name, test_pb_info, pb_db, rom_db, load_paths_from_json


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

        # --------- #
        # Load Data #
        # --------- #

        # Build sample paths DB if it's not already there.
        if not paths_db.is_file():
            save_raw_paths_to_json(raw_mame_paths, paths_db)

        self.mame_paths: list[Path] = load_paths_from_json(paths_db)
        """List of all MAME directories that will be used by the application."""

        # Create rom list if it doesn't already exist.
        if not rom_db.is_file():
            if self.mame_paths:
                generate_rom_list(self.mame_paths[0], rom_db)

        # Create Personal Best database if it doesn't already exist.
        if not pb_db.is_file():
            with open(pb_db, 'w') as db:
                json.dump(test_pb_info, db, indent=4)

        self.test_game_info: PersonalBestDataBase = load_game_info(pb_db)
        """Personal best information."""

        self.fill_data_structures()

        # -------------------- #
        # Widget customization #
        # -------------------- #
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

        # ----------------- #
        # Tab Customization #
        # ----------------- #
        self.tabs: QTabWidget = QTabWidget()
        """Tab container"""
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)

        # ----- #
        # Pages #
        # ----- #
        self.save_state_page: QWidget = QWidget()
        self.high_score_page: QWidget = QWidget()
        self.rom_search_page: QWidget = QWidget()

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
        self.notes_window = NotesWindow(self)
        self.add_game_button: QPushButton = QPushButton('Add Game')
        self.delete_game_button: QPushButton = QPushButton('Delete Game')

        self.split_list: StageSplitListWidget = StageSplitListWidget(self.test_game_info)
        self.add_split_button: QPushButton = QPushButton('Add Split')
        self.delete_split_button: QPushButton = QPushButton('Delete Split')

        # Layouts

        self.high_score_page_layout: QHBoxLayout = QHBoxLayout()
        """Top level page layout."""

        self.game_list_button_container: QHBoxLayout = QHBoxLayout()

        self.game_list_container: QVBoxLayout = QVBoxLayout()
        """Contains list of games with personal best information and related buttons."""

        self.info_layout: QVBoxLayout = QVBoxLayout()
        """Contains PB info, stage splits, and related buttons."""

        self.personal_best_layout: QGridLayout = QGridLayout()
        """Contains PB info."""

        self.splits_tree_button_container: QHBoxLayout = QHBoxLayout()
        """Contains buttons related to stage splits."""

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


        # --------------- #
        # Rom Search Page #
        # --------------- #

        # Widgets
        self.rom_search_bar: QLineEdit = QLineEdit()
        self.rom_search_bar.setPlaceholderText('Search items...')
        self.rom_search_bar.textChanged.connect(self.on_text_changed)

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.update_filter)

        self.rom_search_tree: QTreeWidget = QTreeWidget()
        self.rom_search_tree.setHeaderLabels(['Games'])
        for game_name in self.description_db.keys():
            item = QTreeWidgetItem(self.rom_search_tree, [game_name])
            item.setToolTip(0, self.description_db[game_name])


        # self.source_model = QStringListModel(self.description_db.keys())
        # self.proxy_model = QSortFilterProxyModel()
        # self.proxy_model.setSourceModel(self.source_model)
        # self.proxy_model.setFilterKeyColumn(0)
        #
        #
        #
        # self.rom_search_list: QListView = QListView()
        # self.rom_search_list.setModel(self.proxy_model)



        # Layouts
        self.rom_search_page_layout = QVBoxLayout()
        self.rom_search_page_layout.addWidget(self.rom_search_bar)
        self.rom_search_page_layout.addWidget(self.rom_search_tree)
        # self.rom_search_page_layout.addWidget(self.rom_search_list)
        self.rom_search_page.setLayout(self.rom_search_page_layout)
        self.rom_search_page.setFont(self.top_level_item_font)

        # Finalize tab setup.
        self.tabs.addTab(self.save_state_page, 'Save States')
        self.tabs.addTab(self.high_score_page, 'High Scores')
        self.tabs.addTab(self.rom_search_page, 'Rom Search')
        self.setCentralWidget(self.tabs)

    # ------- #
    # Methods #
    # ------- #
    def handle_action1(self):
        game_name = self.high_score_game_tree.selectedItems()[0].text(0)
        rom_name = self.description_db[game_name]
        if self.notes_window.isHidden():
            self.notes_window.show()
        # self.notes_window.text_edit.setText(f'{game_name} - Notes')
        note_path = Path('notes') / rom_name

        if not note_path.is_file():
            note_path.touch()
        else:
            with open(note_path, 'r') as notes:
                text = notes.read()
                self.notes_window.text_edit.setText(text)
        self.notes_window.current_game = rom_name
        self.notes_window.setWindowTitle(f'{rom_name} - Notes')
        self.notes_window.raise_()
        self.notes_window.setFocus()



    def handle_action2(self):
        rom_description = self.high_score_game_tree.selectedItems()[0].text(0)
        rom_name = self.description_db[rom_description]
        path = Path(r"C:\Users\kazac\Downloads\wolfmame-0273") / 'mame.exe'
        print(path)
        subprocess.Popen([path, f'{rom_name}'], cwd=r"C:\Users\kazac\Downloads\wolfmame-0273")

    def show_high_score_tree_context(self, position: QPoint):
        item = self.high_score_game_tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        test_action1 = QAction('Action 1')
        test_action2 = QAction('Action 2')

        test_action1.triggered.connect(self.handle_action1)
        test_action2.triggered.connect(self.handle_action2)

        menu.addAction(test_action1)
        menu.addAction(test_action2)

        sub_menu = QMenu('Open with...')

        menu.exec(self.high_score_game_tree.viewport().mapToGlobal(position))

    def on_text_changed(self, text):
        self.debounce_timer.start(300)

    # def update_filter(self):
    #     search_text = self.rom_search_bar.text()
    #     # Set the filter using a regular expression
    #     # Qt.CaseInsensitive ensures the search is case-insensitive
    #     self.proxy_model.setFilterFixedString(search_text)
    #     self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def update_filter(self):
        search_text = self.rom_search_bar.text().lower()
        self.rom_search_tree.clear()

        for game_name in self.description_db.keys():
            if search_text in game_name.lower():
                # QTreeWidgetItem(self.rom_search_tree, [game_name])
                item = QTreeWidgetItem(self.rom_search_tree, [game_name])
                item.setToolTip(0, self.description_db[game_name])


    def sizeHint(self):
        """Default window size."""
        return QSize(1920, 1080)

    def setup_file_menu(self):
        """File Menu widget customization."""
        self.button_1_action.triggered.connect(self.menu_button_1_clicked)
        self.button_2_action.triggered.connect(self.menu_button_2_clicked)
        self.button_3_action.triggered.connect(self.add_path_button_clicked)

        self.file_menu.addAction(self.button_1_action)
        self.file_menu.addAction(self.button_2_action)
        self.file_menu.addAction(self.button_3_action)

    def setup_highscore_panel(self):
        """High Score Panel widget customization"""
        self.notes_window.hide()
        # Fill Game List
        for key in self.test_game_info:
            QTreeWidgetItem(self.high_score_game_tree, [key])

        self.high_score_game_tree.setHeaderLabels(['Games'])
        self.high_score_game_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.high_score_game_tree.customContextMenuRequested.connect(self.show_high_score_tree_context)
        self.high_score_game_tree.itemSelectionChanged.connect(self.high_score_tree_selection_changed)

        self.add_game_button.clicked.connect(self.add_game)
        self.delete_game_button.clicked.connect(self.delete_game)

        self.game_list_button_container.addWidget(self.add_game_button)
        self.game_list_button_container.addWidget(self.delete_game_button)

        self.game_list_container.addWidget(self.high_score_game_tree)
        self.game_list_container.addLayout(self.game_list_button_container)

        first_item = self.high_score_game_tree.topLevelItem(0)
        self.high_score_game_tree.setCurrentItem(first_item)
        # self.game_list_container.addWidget(self.add_game_button)
        # self.game_list_container.addWidget(self.delete_game_button)

    def setup_pb_panel(self):
        """Personal Best Panel widget customization."""
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
        """Split Panel widget customization."""
        self.splits_tree_button_container.addWidget(self.add_split_button)
        self.splits_tree_button_container.addWidget(self.delete_split_button)

        self.split_list.itemDoubleClicked.connect(self.split_double_clicked)
        self.split_list.currentItemChanged.connect(self.split_current_item_changed)

        self.add_split_button.clicked.connect(self.new_split)
        self.delete_split_button.clicked.connect(self.delete_split)

    def update_pb_panel(self, high_score, distance):
        """Sets the text of the labels and editors associated with the Personal Best Panel."""
        self.high_score_edit.setText(str(high_score))
        self.distance_edit.setText(distance)
        self.high_score_value_label.setText(str(high_score))
        self.distance_value_label.setText(distance)
        self.high_score_edit.hide()
        self.distance_edit.hide()

    def add_split(self, split, game_name):
        """Create a new custom widget item and assign it to a list widget item."""
        split_item = StageSplitItem(split, self.test_game_info, game_name, self.split_list)
        list_item = QListWidgetItem(self.split_list)
        self.split_list.setItemWidget(list_item, split_item)
        return list_item

    def valid_path(self, mame_folder: Path):
        """Validate the given MAME path."""
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
        """Prompt user for a MAME directory using a file dialog."""
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
        """Fill data structures used to derive Save State Tree Widget items."""
        self.description_db = build_description_db(rom_db)
        self.all_save_states = get_all_roms_with_saves(self.mame_paths)

    def add_mame_path_items(self):
        """Clear, and then fill the Save State Tree Widget."""
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

    # ----- #
    # Slots #
    # ----- #
    def new_split(self):
        """Create a new, blank split item. Add it to the list widget, in memory db representation, and save to JSON."""
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            game_splits = self.test_game_info[game_name]['splits']
            # split_count = len(game_splits)
            new_split = ['', 0]
            game_splits.append(new_split)
            new_item = self.add_split(new_split, game_name)
            self.split_list.setCurrentItem(new_item)
            self.split_double_clicked(new_item)
            save_pb_to_json(self.test_game_info, pb_db)

    def add_game(self):
        """Add a game to PB game tree. User is prompted to enter the games name. Save new game to JSON"""
        game_name, ok = QInputDialog.getText(self, 'New Game', 'Please enter new game name.')
        if game_name and ok:
            QTreeWidgetItem(self.high_score_game_tree, [game_name])

            self.test_game_info[game_name] = {'hs': 0,
                                              'distance': '',
                                              'splits': []}
            save_pb_to_json(self.test_game_info, pb_db)

    def delete_game(self):
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            previous_item = self.high_score_game_tree.itemAbove(game_item)
            next_item = self.high_score_game_tree.itemBelow(game_item)

            if previous_item:
                self.high_score_game_tree.setCurrentItem(previous_item)
            elif next_item:
                self.high_score_game_tree.setCurrentItem(next_item)
            else:
                self.high_score_game_tree.clearSelection()

            game_name = game_item.text(0)
            del self.test_game_info[game_name]
            save_pb_to_json(self.test_game_info, pb_db)


            game_item_index = self.high_score_game_tree.indexFromItem(game_item)
            game_row = game_item_index.row()
            self.high_score_game_tree.takeTopLevelItem(game_row)

    def delete_split(self):
        """Delete a split in the split list. Also deleted from in-memory db and saved to JSON."""
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            row = self.split_list.currentRow()
            if row != -1:
                self.split_list.takeItem(row)
                splits = self.test_game_info[game_name]['splits']
                del splits[row]
                save_pb_to_json(self.test_game_info, pb_db)

    # TODO re-enable file renaming after ensuring user input is properly sanitized.
    def save_state_tree_item_changed(self, save_state_item: QTreeWidgetItem):
        """Does not currently have any effect."""
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
        """Used internally for renaming."""
        self.text_before_editing = current_item.text(0)

    def high_score_tree_selection_changed(self):
        """Clear and refill 'splits list' based on currently selected item. Split diffs are calculated and displayed."""
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

            self.split_list.add_diffs(splits)

    def split_double_clicked(self, item: QListWidgetItem):
        """Show split item editors. Hide labels."""
        widget_item = self.split_list.itemWidget(item)
        widget_item.toggle_editors()

    def split_current_item_changed(self, cur: QListWidgetItem, prev: QListWidgetItem):
        """Show split item labels. Hide editors."""
        if prev:
            widget_item = self.split_list.itemWidget(prev)
            widget_item.toggle_labels()

    def update_high_score_pb(self):
        """Update in memory DB and saves to JSON"""
        new_pb = int(self.high_score_edit.text())
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.test_game_info[game_name]['hs'] = new_pb
            save_pb_to_json(self.test_game_info, pb_db)

    def update_distance_pb(self):
        """Update in memory DB and saves to JSON"""
        new_pb = self.distance_edit.text()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.test_game_info[game_name]['distance'] = new_pb
            save_pb_to_json(self.test_game_info, pb_db)

    def menu_button_1_clicked(self) -> None:
        """Temporary"""
        self.save_state_tree.hide()

    def menu_button_2_clicked(self) -> None:
        """Temporary"""
        self.save_state_tree.show()

    # TODO Same problem here I have to disconnect and reconnect slot to avoid breaking shit. Look into it.
    def add_path_button_clicked(self) -> None:
        """Prompt user for new MAME path, then clear and refill save state tree."""
        path = self.get_mame_path()
        if path:
            self.mame_paths.append(path)
            raw_paths = get_raw_paths(self.mame_paths)
            save_raw_paths_to_json(raw_paths, paths_db)
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
