"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Reactivate file renaming eventually.
    * Consider sizing policies and size hints
    * Decide on new features to add.
"""
import pprint
import sqlite3
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QTimer, QPoint
from PyQt6.QtGui import QAction, QFont, QIntValidator, QColor, QBrush
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QLineEdit, \
    QTabWidget, QHBoxLayout, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QListWidgetItem, \
    QFileDialog, QMessageBox, QMenu

from custom.widgets import StageSplitListWidget, StageSplitItem, SaveStateNameInputValidator, \
    NotesWindow, RomSearchWindow, PBScannerThread, ProgressBarWidget, NewToggleableLabel, MAMEThread
from logic.main import get_real_name, load_path_from_db, get_all_roms_with_saves, \
    delete_personal_best, delete_splits, get_all_input_files, load_personal_bests_from_database, \
    save_pb_to_database, save_pbs, has_xml, get_new_pb, \
    prepare_pb_for_db, get_formatted_rom_info, PersonalBestDataBase
from logic.main import save_paths_to_database, get_descriptions_and_names, \
    delete_split


class MainWindow(QMainWindow):
    """Subclasses and extends the QQMainWindow class of the PyQt6.QtWidgets Module

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Houses all GUI elements of the MAMEStates application.
    """

    def __init__(self, db_connection: sqlite3.Connection):
        """Initialize the MainWindow subclass

        The MainWindow subclass inherits most of its behavior from, and extends, its parent class QMainWindow. The
        initialization process setups the GUI elements present on program launch, as well as connecting signals to
        slots.
        """
        super().__init__()
        self.progress_bar = None
        """Reference to progress bar popup window. Prevents garbage collection and allows access."""

        self.pre_launch_hs_table = None
        """Reference to a roms leaderboard prior to being launched."""

        self.mame_thread = None
        """Reference to thread used to launch MAME subprocess."""

        self.temp_fields = []
        """References to 'other fields' for a given rom PB. Used for deletion."""

        self.rom_search_popup: QWidget | None = None
        """Reference to rom search popup window. Prevents garbage collection and allows access."""

        self.db_connection: sqlite3.Connection = db_connection
        """Connection object that points to database connection."""

        self.db_cursor: sqlite3.Cursor = self.db_connection.cursor()
        """Cursor object used to navigate database."""

        self.text_before_editing: str | None = None
        """Text of the previous selected save state item."""

        self.descriptions_and_names: dict[str, str] = {}
        """Maps a roms long name to its short name in the format: \n{'description': 'rom'}"""

        self.all_save_states: dict[str:dict[str:list[str]]] | None = None
        """Names of games that have a save folder, and their respective save states"""

        self.all_input_files = None
        """MAME paths and the contents of their respective inp directories."""

        self.all_rom_info: dict | None = None
        """All rom related information. Keyed to rom description."""

        # --------- #
        # Load Data #
        # --------- #
        self.mame_paths: list[Path] = load_path_from_db(self.db_cursor)
        """List of all MAME directories that will be used by the application."""

        self.pb_info: PersonalBestDataBase = load_personal_bests_from_database(self.db_cursor)
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
        self.button_4_action: QAction = QAction('Update Personal Bests', self)

        self.setup_file_menu()

        # ----------------- #
        # Tab Customization #
        # ----------------- #
        self.tabs: QTabWidget = QTabWidget()
        """Tab container"""
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)

        #########
        # Pages #
        #########
        self.save_state_page: QWidget = QWidget()
        self.high_score_page: QWidget = QWidget()
        self.rom_search_page: QWidget = QWidget()

        # ------------------ #
        #   Save State Page  #
        # ------------------ #

        # Widgets
        self.save_state_tree: QTreeWidget = QTreeWidget()
        """Main widget of the save state tab"""

        # Layouts
        self.save_state_page_layout: QHBoxLayout = QHBoxLayout()
        self.save_state_page_layout.setContentsMargins(0, 0, 0, 0)
        self.save_state_page.setLayout(self.save_state_page_layout)
        self.save_state_page_layout.addWidget(self.save_state_tree)

        # ------------------#
        #   Highscore Page  #
        # ------------------#

        # Widgets
        self.high_score_label: QLabel = QLabel('High Score:')
        self.high_score_value_label = NewToggleableLabel('')

        self.high_score_game_tree: QTreeWidget = QTreeWidget()
        self.notes_window = NotesWindow(self)
        self.highscore_add_game_button: QPushButton = QPushButton('Add Game')
        self.delete_game_button: QPushButton = QPushButton('Delete Game')

        self.split_list: StageSplitListWidget = StageSplitListWidget(self.pb_info, self.db_connection, self.db_cursor)
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
        self.setup_save_state_page()
        self.setup_highscore_panel()
        self.setup_pb_panel()
        self.setup_split_panel()

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
        for game_name in self.descriptions_and_names.keys():
            item = QTreeWidgetItem(self.rom_search_tree, [game_name])
            parent = self.all_rom_info[game_name]['parent']
            if parent is not None:
                color = QColor(211, 211, 211, 127)
                brush = QBrush(color)
                # Apply to item (column 0)
                item.setForeground(0, brush)
            item.setToolTip(0, self.descriptions_and_names[game_name])

        self.rom_search_add_game_button: QPushButton = QPushButton('Add Game')
        self.rom_search_cancel_button: QPushButton = QPushButton('Cancel')

        self.rom_search_cancel_button.clicked.connect(self.close_rom_search_window)
        self.rom_search_add_game_button.clicked.connect(self.rom_search_add_game_clicked)
        self.rom_search_tree.itemSelectionChanged.connect(self.rom_search_tree_selection_changed)


        self.rom_description_label: QLabel = QLabel()
        self.rom_description_label.setWordWrap(True)
        self.rom_name_label: QLabel = QLabel()
        self.rom_manufacturer_label: QLabel = QLabel()
        self.rom_release_year_label: QLabel = QLabel()
        self.rom_parent_label: QLabel = QLabel()
        self.rom_video_info_label: QLabel = QLabel()
        self.rom_video_driver_warnings_label: QLabel = QLabel()
        self.rom_audio_driver_warnings_label: QLabel = QLabel()

        # Layouts
        self.rom_search_page_layout = QHBoxLayout()
        self.rom_info_panel = QVBoxLayout()
        self.rom_search_panel = QVBoxLayout()
        self.rom_search_buttons = QHBoxLayout()
        self.rom_search_container = QWidget()
        self.rom_search_container.setLayout(self.rom_search_panel)
        # self.rom_search_container.setFixedWidth(800)
        self.rom_search_panel.addWidget(self.rom_search_bar)
        self.rom_search_panel.addWidget(self.rom_search_tree)
        self.rom_search_buttons.addWidget(self.rom_search_add_game_button)
        self.rom_search_buttons.addWidget(self.rom_search_cancel_button)
        self.rom_search_panel.addLayout(self.rom_search_buttons)
        self.rom_search_add_game_button.hide()
        self.rom_search_cancel_button.hide()

        self.rom_info_container = QWidget()
        self.rom_info_container.setLayout(self.rom_info_panel)
        # self.rom_info_container.setFixedWidth(600)
        self.rom_info_panel.addWidget(self.rom_description_label)
        self.rom_info_panel.addWidget(self.rom_name_label)
        self.rom_info_panel.addWidget(self.rom_manufacturer_label)
        self.rom_info_panel.addWidget(self.rom_release_year_label)
        self.rom_info_panel.addWidget(self.rom_parent_label)
        self.rom_info_panel.addWidget(self.rom_video_info_label)
        self.rom_info_panel.addWidget(self.rom_video_driver_warnings_label)
        self.rom_info_panel.addWidget(self.rom_audio_driver_warnings_label)
        self.rom_info_panel.addStretch()


        self.rom_search_page_layout.addWidget(self.rom_search_container)
        self.rom_search_page_layout.addWidget(self.rom_info_container)


        self.rom_search_page.setLayout(self.rom_search_page_layout)
        self.rom_search_page.setFont(self.top_level_item_font)

        # Finalize tab setup.
        self.tabs.addTab(self.save_state_page, 'Save States')
        self.tabs.addTab(self.high_score_page, 'High Scores')
        self.tabs.addTab(self.rom_search_page, 'Rom Search')
        self.setCentralWidget(self.tabs)

    ###########
    # Methods #
    ###########
    def sizeHint(self) -> QSize:
        """Default window size."""
        return QSize(1920, 1080)

    # ----- #
    # Setup #
    # ----- #
    def setup_file_menu(self) -> None:
        """File Menu widget customization."""
        self.button_1_action.triggered.connect(self.menu_button_1_clicked)
        self.button_2_action.triggered.connect(self.menu_button_2_clicked)
        self.button_3_action.triggered.connect(self.add_path_button_clicked)
        self.button_4_action.triggered.connect(self.scan_for_pb)

        self.file_menu.addAction(self.button_1_action)
        self.file_menu.addAction(self.button_2_action)
        self.file_menu.addAction(self.button_3_action)
        self.file_menu.addAction(self.button_4_action)

    def setup_save_state_page(self):
        self.save_state_tree.setEditTriggers(QTreeWidget.EditTrigger.AnyKeyPressed)
        self.save_state_tree.setHeaderLabels(['MAME Folders'])
        self.save_state_tree.setColumnWidth(0, 1000)
        self.save_state_tree.setItemDelegate(SaveStateNameInputValidator(self))
        self.save_state_tree.setTabKeyNavigation(True)
        self.save_state_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.save_state_tree.customContextMenuRequested.connect(self.show_input_file_context)

        self.fill_save_state_tree()
        self.save_state_tree.currentItemChanged.connect(self.save_state_tree_selection_changed)
        self.save_state_tree.itemChanged.connect(self.save_state_tree_leaf_item_changed)

    def fill_highscore_game_list(self):
        self.high_score_game_tree.clear()
        for key in self.pb_info:
            QTreeWidgetItem(self.high_score_game_tree, [key])

    def setup_highscore_panel(self) -> None:
        """High Score Panel widget customization"""
        self.notes_window.hide()
        # Fill Game List
        self.fill_highscore_game_list()

        self.high_score_game_tree.setHeaderLabels(['Games'])
        self.high_score_game_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.high_score_game_tree.customContextMenuRequested.connect(self.show_high_score_tree_context)
        self.high_score_game_tree.itemSelectionChanged.connect(self.high_score_tree_selection_changed)

        self.highscore_add_game_button.clicked.connect(self.highscore_add_game_clicked)
        self.delete_game_button.clicked.connect(self.delete_game)

        self.game_list_button_container.addWidget(self.highscore_add_game_button)
        self.game_list_button_container.addWidget(self.delete_game_button)

        self.game_list_container.addWidget(self.high_score_game_tree)
        self.game_list_container.addLayout(self.game_list_button_container)

        first_item = self.high_score_game_tree.topLevelItem(0)
        self.high_score_game_tree.setCurrentItem(first_item)

    def setup_pb_panel(self) -> None:
        """Personal Best Panel widget customization."""
        self.high_score_value_label.editor.setValidator(QIntValidator())
        self.high_score_value_label.editor.editingFinished.connect(self.update_high_score_pb)

        self.personal_best_layout.addWidget(self.high_score_label, 0, 0)
        self.personal_best_layout.addWidget(self.high_score_value_label, 0, 1)


    def setup_split_panel(self) -> None:
        """Split Panel widget customization."""
        self.splits_tree_button_container.addWidget(self.add_split_button)
        self.splits_tree_button_container.addWidget(self.delete_split_button)

        self.split_list.itemDoubleClicked.connect(self.split_double_clicked)
        self.split_list.currentItemChanged.connect(self.split_current_item_changed)

        self.add_split_button.clicked.connect(self.new_split)
        self.delete_split_button.clicked.connect(self.delete_split)

    def setup_search_page(self):
        color = QColor(211, 211, 211, 127)
        brush = QBrush(color)


    # ------ #
    # Helper #
    # ------ #
    def update_pb_panel(self, high_score: int, other_fields: dict) -> None:
        for _ in self.temp_fields:
            self.personal_best_layout.removeWidget(_)
            if not _.isHidden():
                _.hide()
            print(self.temp_fields)
        self.temp_fields.clear()

        self.high_score_value_label.editor.setText(str(high_score))
        self.high_score_value_label.label.setText(str(high_score))
        self.high_score_value_label.editor.hide()


        if not other_fields:
            return

        for index, key in enumerate(other_fields):
            tlabel = NewToggleableLabel(other_fields[key])
            tlabel.editor.editingFinished.connect(lambda: self.update_other_fields(label.text()))
            label = QLabel(key)
            self.temp_fields.append(label)
            self.temp_fields.append(tlabel)
            self.personal_best_layout.addWidget(label, (index + 1), 0)
            self.personal_best_layout.addWidget(tlabel, (index + 1), 1)


    def create_split_item(self, split: list[int | str], game_name: str) -> QListWidgetItem:
        """Create a new custom widget item and assign it to a list widget item."""
        split_item = StageSplitItem(split, self.pb_info, game_name, self.split_list, self.db_connection, self.db_cursor)
        list_item = QListWidgetItem(self.split_list)
        self.split_list.setItemWidget(list_item, split_item)
        return list_item

    def valid_path(self, mame_folder: Path) -> bool | None:
        """Validate the given MAME path.

        Return True, if valid, False if 'retry', None if 'cancel'.
        """
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

    def get_mame_path(self) -> Path | None:
        """Prompt user for a MAME directory using a file dialog.

        Loops if invalid path and user selects 'retry'.
        """
        mame_folder = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                       options=QFileDialog.Option.ShowDirsOnly)

        mame_folder = Path(mame_folder)

        path_validity = self.valid_path(mame_folder)
        if path_validity is True:
            return mame_folder
        if path_validity is False:
            self.get_mame_path()

        return path_validity

    def fill_data_structures(self) -> None:
        """Fill data structures that are used as convenient in-memory references."""
        self.descriptions_and_names = get_descriptions_and_names(self.db_cursor)
        self.all_save_states = get_all_roms_with_saves(self.mame_paths)
        self.all_input_files = get_all_input_files(self.mame_paths)
        self.all_rom_info = get_formatted_rom_info(self.db_cursor)

    def fill_save_state_tree(self) -> None:
        """Clear, then fill and customize the Save State Tree Widget.

        Font size is configured on each item. Large for paths and games, small for save states.
        Save state items are made editable via flags.
        """
        self.save_state_tree.clear()

        # Add path items.
        for path in self.mame_paths:
            path_item = QTreeWidgetItem(self.save_state_tree, [str(path)])
            path_item.setFont(0, self.top_level_item_font)
            saves_container_item = QTreeWidgetItem(path_item, ['Save States'])
            saves_container_item.setFont(0, self.top_level_item_font)
            input_files = self.all_input_files.get(path)
            if input_files:
                input_files_container = QTreeWidgetItem(path_item, ['Input Files'])
                input_files_container.setFont(0, self.top_level_item_font)
                for file in input_files:
                    item = QTreeWidgetItem(input_files_container, [file.split('.')[0]])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    item.setFont(0, self.sub_item_font)

            # Add game items.
            for key in self.all_save_states[path]:
                game_description = get_real_name(self.descriptions_and_names, key)
                game_item = QTreeWidgetItem(saves_container_item, [game_description])
                game_item.setFont(0, self.top_level_item_font)

                # Add savestate items.
                for save_state in self.all_save_states[path][key]:
                    save_state_item = QTreeWidgetItem(game_item, [save_state])
                    save_state_item.setFlags(save_state_item.flags() | Qt.ItemFlag.ItemIsEditable)
                    save_state_item.setFont(0, self.sub_item_font)

    #########
    # Slots #
    #########
    # ------------------------- #
    # Personal Bests Page Slots #
    # ------------------------- #
    def close_rom_search_window(self):
        self.rom_search_popup.close()

    def high_score_tree_selection_changed(self) -> None:
        """Clear and refill 'splits list' based on currently selected item. Split diffs are calculated and displayed."""
        self.split_list.clear()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            info = self.pb_info[game_name]

            hs = info['hs']
            other_fields = info['other_fields']
            splits = info['splits']

            self.update_pb_panel(hs, other_fields)

            for split in splits:
                self.create_split_item(split, game_name)

            self.split_list.add_diffs(splits)

    def split_double_clicked(self, item: QListWidgetItem) -> None:
        """Show split item editors. Hide labels."""
        widget_item = self.split_list.itemWidget(item)
        widget_item.toggle_editors()

    def split_current_item_changed(self, cur: QListWidgetItem, prev: QListWidgetItem) -> None:
        """Show split item labels. Hide editors."""
        if prev:
            widget_item = self.split_list.itemWidget(prev)
            if widget_item:
                widget_item.toggle_labels()

    def update_high_score_pb(self) -> None:
        """Update in database representation and saves to database"""
        new_pb = int(self.high_score_value_label.editor.text())
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            self.pb_info[game_name]['hs'] = new_pb
            save_pb_to_database(self.db_connection, self.db_cursor, self.pb_info)

    def update_other_fields(self, label):
        sender = self.sender()
        updated_data = sender.text()
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            game_name = game_item.text(0)
            print(label, ' - ', sender.text())
            self.pb_info[game_name]['other_fields'][label] = updated_data
            pprint.pp(self.pb_info)
            save_pb_to_database(self.db_connection, self.db_cursor, self.pb_info)


    def highscore_add_game_clicked(self) -> None:
        """Add a game to PB game tree. User is prompted to enter the games name. Save new game to database.

        If the game name entered does not match any roms description, it causes problems later.
        """

        self.tabs.removeTab(2)
        self.rom_search_popup = RomSearchWindow(self.rom_search_page, self.tabs, self.rom_search_add_game_button,
                                                self.rom_search_cancel_button)
        self.rom_search_popup.show()
        self.setEnabled(False)

    def rom_search_add_game_clicked(self):
        selected = self.rom_search_tree.selectedItems()
        if selected:
            item = selected[0]
            rom_description = item.text(0)
            if rom_description in self.pb_info.keys():
                QMessageBox.critical(self, 'Error', 'That Game already has a PB entry.')
                self.rom_search_popup.raise_()
                self.rom_search_popup.setFocus()
                return

            print(rom_description)

            item = QTreeWidgetItem(self.high_score_game_tree, [rom_description])

            self.pb_info[rom_description] = {'hs': 0,
                                             'other_fields': None,
                                             'splits': []}

            save_pb_to_database(self.db_connection, self.db_cursor, self.pb_info)
            self.rom_search_popup.close()
            self.high_score_game_tree.setCurrentItem(item)

    def delete_game(self) -> None:
        """Delete game from Highscore Game Tree and remove all its information from database."""
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_item = selected[0]
            previous_item = self.high_score_game_tree.itemAbove(game_item)
            next_item = self.high_score_game_tree.itemBelow(game_item)

            # Move selection before deleting.
            if previous_item:
                self.high_score_game_tree.setCurrentItem(previous_item)
            elif next_item:
                self.high_score_game_tree.setCurrentItem(next_item)
            else:
                self.high_score_game_tree.clearSelection()

            rom_description = game_item.text(0)
            # Delete from in-memory database representation.
            del self.pb_info[rom_description]
            # Delete from database.
            delete_personal_best(self.db_connection, self.db_cursor, rom_description)
            delete_splits(self.db_connection, self.db_cursor, rom_description)

            # Finally, remove item from Highscore Game Tree.
            game_item_index = self.high_score_game_tree.indexFromItem(game_item)
            game_row = game_item_index.row()
            self.high_score_game_tree.takeTopLevelItem(game_row)

    def delete_split(self) -> None:
        """Delete a split in the split list. Also deleted from in-memory database representation and database."""
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            game_name = selected[0].text(0)
            # Row becomes -1 when nothing selected.....I think.
            row = self.split_list.currentRow()
            if row != -1:
                self.split_list.takeItem(row)
                splits = self.pb_info[game_name]['splits']
                label = splits[row][0]
                del splits[row]
                delete_split(self.db_connection, self.db_cursor, game_name, label)
                save_pb_to_database(self.db_connection, self.db_cursor, self.pb_info)

    def new_split(self) -> None:
        """Create a new, blank split item. Add it to the list widget and the in memory database representation.

        The new split item has its editor toggled on, and is set as the focus.
        """
        selected = self.high_score_game_tree.selectedItems()
        if selected:
            highscore_tree_item = selected[0]
            rom_description = highscore_tree_item.text(0)
            game_splits = self.pb_info[rom_description]['splits']
            new_split = ['', 0]
            game_splits.append(new_split)
            new_item = self.create_split_item(new_split, rom_description)
            self.split_list.setCurrentItem(new_item)
            self.split_double_clicked(new_item)

    def open_notes(self) -> None:
        """Open notes widget.

        Open the notes widget and change the title to reflect the currently selected item.
        If [rom_name].txt exists, copy data into the notes widget. Otherwise, create [rom_name].txt. Focus notes widget.
        A reference is held to the notes widget to avoid it being automatically deleted. Cannot open multiple notes.
        """
        game_name = self.high_score_game_tree.selectedItems()[0].text(0)
        rom_name = self.descriptions_and_names[game_name]
        if self.notes_window.isHidden():
            self.notes_window.show()

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

    def show_input_file_context(self, position: QPoint):
        tree_item = self.save_state_tree.itemAt(position)
        if not tree_item:
            return
        if tree_item.childCount() > 0:
            return
        menu = QMenu()

        delete = QAction('Delete')
        menu.addAction(delete)
        sub_menu = QMenu('Playback with...')
        for path in self.mame_paths:
            action = QAction(str(path), self)
            action.triggered.connect(lambda: print(self.sender().text()))
            sub_menu.addAction(action)
        menu.addMenu(sub_menu)
        menu.exec(self.save_state_tree.viewport().mapToGlobal(position))


    def show_high_score_tree_context(self, position: QPoint) -> None:
        """Create custom context menu, connect slots, execute menu.

        If no item is selected, no menu is created. Menu includes 'open notes' and 'open with' functions, based on game.
        """
        tree_item = self.high_score_game_tree.itemAt(position)
        if not tree_item:
            return

        item_name = tree_item.text(0)
        rom_name = self.descriptions_and_names[item_name]

        menu = QMenu()

        open_notes = QAction('Open Notes')
        open_notes.triggered.connect(self.open_notes)
        menu.addAction(open_notes)

        sub_menu = QMenu('Open with...')
        for path in self.mame_paths:
            action = QAction(str(path), self)
            action.triggered.connect(lambda: self.run_rom(rom_name))
            sub_menu.addAction(action)

        sub_menu_two = QMenu('Open with input file...')
        for path in self.mame_paths:
            action = QAction(str(path), self)
            action.triggered.connect(lambda:print(self.sender().text()))
            sub_menu_two.addAction(action)

        menu.addMenu(sub_menu)
        menu.addMenu(sub_menu_two)
        menu.exec(self.high_score_game_tree.viewport().mapToGlobal(position))

    # TODO Take another look at this.
    def run_rom(self, rom_name: str) -> None:
        """Attempt to run a rom, with a given MAME path.

        This function does not currently check for a roms existence before trying to run it. MAME errors used instead.
        All MAME output and errors are captured for display in GUI.
        """
        # The action that triggered this function call. Its label has the correct MAME path.
        action = self.sender()
        mame_path = action.text()
        mame_exe = Path(mame_path) / 'mame.exe'
        rom_path = Path(mame_path) / 'roms' / (rom_name + '.zip')
        hi_path = Path(mame_path) / 'hiscore' / (rom_name + '.hi')

        print(rom_path)
        print(rom_path.is_file())

        hi2txt_compatible = has_xml(rom_name)
        if hi2txt_compatible:
            try:
                results = subprocess.run([r'C:\Users\kazac\Downloads\hi2txt\hi2txt.exe', '-r', f'{hi_path}'],
                                         cwd=r'C:\Users\kazac\Downloads\hi2txt', capture_output=True, text=True,
                                         check=True, encoding='utf-8')
                self.pre_launch_hs_table = results.stdout
            except FileNotFoundError:
                print('whoops')


        self.mame_thread = MAMEThread(mame_exe, rom_name, mame_path)
        self.mame_thread.done.connect(self.rom_done)
        self.mame_thread.start()

        print(f'Running {rom_name}, from {action.text()}')

    def rom_done(self, results):
        new_hs_table = None

        hi_path = Path(self.mame_thread.mame_path) / 'hiscore' / (self.mame_thread.rom_name + '.hi')
        if results['return_code'] == 2:
            QMessageBox.critical(self, 'Rom Not Found', 'See console for full error message.')
        else:
            QMessageBox.information(self, 'Rom Closed', f'{self.mame_thread.rom_name} closed successfully.')
            if self.pre_launch_hs_table:
                try:
                    hi2txt_results = subprocess.run([r'C:\Users\kazac\Downloads\hi2txt\hi2txt.exe', '-r', f'{hi_path}'],
                                             cwd=r'C:\Users\kazac\Downloads\hi2txt', capture_output=True, text=True,
                                             check=True, encoding='utf-8')
                    new_hs_table = hi2txt_results.stdout
                except FileNotFoundError:
                    print('whoops')

                new_pb = get_new_pb(self.pre_launch_hs_table, new_hs_table)
                if new_pb:
                    response = QMessageBox.question(self, 'New PB Detected!', f'A new personal best has been detected\n{new_pb['col']}\n{new_pb['row']}\nWould you like to add new PB?')
                    if response == QMessageBox.StandardButton.Yes:
                        new_pb = prepare_pb_for_db(new_pb, self.mame_thread.rom_name)
                        save_pbs(new_pb, self.db_connection, self.db_cursor)
                        QMessageBox.information(self, 'Ok', 'Pb Updated!')
                    else:
                        QMessageBox.information(self, 'Ok', 'PB discarded.')
        print(f'Return code is: {results['return_code']}')

    # --------------------- #
    # Rom Search Page Slots #
    # --------------------- #
    def on_text_changed(self) -> None:
        """Start a timer used to delay rom search filtering."""
        self.debounce_timer.start(300)

    def update_filter(self) -> None:
        """Filter the rom search list based on searchbar text.

        Search is case-insensitive. List is cleared before adding back items that clear filter.
        """
        search_text = self.rom_search_bar.text().lower()
        self.rom_search_tree.clear()
        items = []
        for rom_description, rom_name in self.descriptions_and_names.items():
            if search_text == rom_name.lower() or search_text == rom_description.lower():
                item = QTreeWidgetItem([rom_description])
                item.setToolTip(0, rom_name)
                parent = self.all_rom_info[rom_description]['parent']
                if parent is not None:
                    color = QColor(211, 211, 211, 127)
                    brush = QBrush(color)
                    # Apply to item (column 0)
                    item.setForeground(0, brush)
                item = (item, 1)
                items.append(item)

            elif rom_name.lower().startswith(search_text) or rom_description.lower().startswith(search_text):
                item = QTreeWidgetItem([rom_description])
                item.setToolTip(0, rom_name)
                parent = self.all_rom_info[rom_description]['parent']
                if parent is not None:
                    color = QColor(211, 211, 211, 127)
                    brush = QBrush(color)
                    # Apply to item (column 0)
                    item.setForeground(0, brush)
                item = (item, 2)
                items.append(item)

            elif search_text in rom_name.lower() or search_text in rom_description.lower():
                item = QTreeWidgetItem([rom_description])
                item.setToolTip(0, rom_name)
                parent = self.all_rom_info[rom_description]['parent']
                if parent is not None:
                    color = QColor(211, 211, 211, 127)
                    brush = QBrush(color)
                    # Apply to item (column 0)
                    item.setForeground(0, brush)
                item = (item, 3)
                items.append(item)

        items.sort(key=lambda x: (x[1], x[0].text(0)))

        for item in items:
            self.rom_search_tree.addTopLevelItem(item[0])

    def rom_search_tree_selection_changed(self):
        self.rom_description_label.setText('')
        self.rom_name_label.setText('')
        self.rom_manufacturer_label.setText('')
        self.rom_release_year_label.setText('')
        self.rom_parent_label.setText('')
        self.rom_video_info_label.setText('')
        self.rom_video_driver_warnings_label.setText('')
        self.rom_audio_driver_warnings_label.setText('')

        selected = self.rom_search_tree.selectedItems()
        if selected:
            game_description = selected[0].text(0)
            rom_info = self.all_rom_info[game_description]
            self.rom_description_label.setText(f'Game: {game_description}')
            self.rom_name_label.setText(f'Rom Name: {rom_info['name']}')
            self.rom_manufacturer_label.setText(f'Manufacturer: {rom_info['manufacturer']}')
            self.rom_release_year_label.setText(f'Year: {str(rom_info['year'])}')
            self.rom_parent_label.setText(f'Parent: {rom_info['parent']}')
            self.rom_video_info_label.setText(f'Video Info: {rom_info['video_info']}')
            self.rom_video_driver_warnings_label.setText(f'Video Driver: {rom_info['video_driver']}')
            self.rom_audio_driver_warnings_label.setText(f'Sound Driver: {rom_info['sound_driver']}')



    # --------------------- #
    # Save State Page Slots #
    # --------------------- #
    def save_state_tree_selection_changed(self, current_item: QTreeWidgetItem) -> None:
        """Used internally for renaming."""
        self.text_before_editing = current_item.text(0)

    def save_state_tree_leaf_item_changed(self, leaf_item: QTreeWidgetItem) -> None:
        """Rename save state file corresponding to item in tree.

        If file name already in use, item has its text reverted and file is not renamed.
        """
        if not leaf_item.text(0):
            self.save_state_tree.blockSignals(True)
            leaf_item.setText(0, self.text_before_editing)
            self.save_state_tree.blockSignals(False)
            return

        if leaf_item.childCount() == 0 and leaf_item.parent().text(0) == 'Input Files':
            input_file = leaf_item.text(0)
            mame_path_item = leaf_item.parent().parent()
            mame_path = mame_path_item.text(0)
            mame_path = Path(mame_path)
            old_input_file_path = mame_path / 'inp'/ f'{self.text_before_editing}.inp'
            new_input_file_path = old_input_file_path.with_stem(input_file)

            response = QMessageBox.question(self, 'Rename Input File', 'Are you sure you would like to rename file?')
            if response == QMessageBox.StandardButton.Yes:
                try:
                    old_input_file_path.rename(new_input_file_path)
                except FileExistsError:
                    QMessageBox.critical(self, 'Error', 'Sorry, that name is already in use.')
                    self.save_state_tree.blockSignals(True)
                    leaf_item.setText(0, self.text_before_editing)
                    self.save_state_tree.blockSignals(False)
                    return
            else:
                self.save_state_tree.blockSignals(True)
                leaf_item.setText(0, self.text_before_editing)
                self.save_state_tree.blockSignals(False)
                return

        if leaf_item.childCount() == 0 and leaf_item.parent().parent().text(0) == 'Save States':
            save_state_name = leaf_item.text(0)
            game_item = leaf_item.parent()
            game_name = game_item.text(0)

            rom_name = self.descriptions_and_names[game_name]

            mame_path_item = game_item.parent().parent()
            mame_path = mame_path_item.text(0)

            mame_path = Path(mame_path)
            save_folder = mame_path / 'sta' / rom_name
            old_save_state_path = save_folder / (self.text_before_editing + '.sta')
            new_save_state_path = old_save_state_path.with_stem(save_state_name)

            try:
                old_save_state_path.rename(new_save_state_path)
            except FileExistsError:
                QMessageBox.critical(self, 'Error', 'Sorry, that name is already in use.')
                self.save_state_tree.blockSignals(True)
                leaf_item.setText(0, self.text_before_editing)
                self.save_state_tree.blockSignals(False)
                return
            # Have to set this to new save_state_name so multiple renames can take place without reselection.
            self.text_before_editing = save_state_name

    # --------------- #
    # File Menu Slots #
    # --------------- #
    def menu_button_1_clicked(self) -> None:
        """Temporary"""
        self.save_state_tree.hide()

    def menu_button_2_clicked(self) -> None:
        """Temporary"""
        self.save_state_tree.show()

    def add_path_button_clicked(self) -> None:
        """Prompt user for new MAME path and then, clear and refill save state tree.

        Path must be valid filepath, not already in the in-memory representation of the 'paths' database table.
        Path is saved to database and in-memory representation. Slots are disconnected before refilling tree.
        This avoids the incidental signals emitted when adding objects.
        """
        path = self.get_mame_path()
        if path:
            if path not in self.mame_paths:
                self.mame_paths.append(path)

            save_paths_to_database(self.db_connection, self.db_cursor, self.mame_paths)
            self.all_save_states = get_all_roms_with_saves(self.mame_paths)
            self.save_state_tree.blockSignals(True)
            self.fill_save_state_tree()
            self.save_state_tree.blockSignals(False)
            # print(f'New MAME path: {path}')
        # else:
        #     print('Cancel chosen')

    def scan_for_pb(self):
        self.setEnabled(False)
        self.progress_bar = ProgressBarWidget(self)
        self.progress_bar.show()
        pb_scanner = PBScannerThread()
        pb_scanner.finished.connect(self.scan_finished)
        pb_scanner.start()
        self.pb_info = load_personal_bests_from_database(self.db_cursor)
        self.fill_highscore_game_list()

    def scan_finished(self):
        self.setEnabled(True)
        self.progress_bar.hide()



def main() -> None:
    """MAMEStates program entry point.

    This function allows me to create DB connects with context manager. If the program ends early, rollback occurs.
    Alternative would be creating db connection with context inside MainWindow _init_, which seems not ideal.
    """
    with sqlite3.connect(r'mame_states.db') as connection:
        # The order the objects are initialized in matters.
        app = QApplication([])

        window = MainWindow(connection)
        window.show()

        app.exec()


if __name__ == '__main__':
    main()
