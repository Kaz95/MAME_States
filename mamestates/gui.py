"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.
"""
import os
import pprint
import sqlite3
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QTimer, QPoint, QSignalBlocker
from PyQt6.QtGui import QAction, QFont, QColor, QBrush
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget, \
    QHBoxLayout, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QMenu, QTextEdit, QInputDialog

import core
import hi2txt_wrapper
import widgets
from mamestates.widgets import DetachableWidget


# TODO Consider moving MainWindow to widgets, as it is technically no different then any other QWidget.
class MainWindow(QMainWindow):
    """Subclasses and extends the QQMainWindow class of the PyQt6.QtWidgets Module

    This class inherits most of its behavior from its parent class, while extending its functionality.
    Houses all GUI elements of the MAMEStates application.
    """

    def __init__(self, mame_states_core: core.MAMEStatesCore) -> None:
        """Initialize the MainWindow subclass

        The MainWindow subclass inherits most of its behavior from, and extends, its parent class QMainWindow. The
        initialization process setups the GUI elements present on program launch, as well as connecting signals to
        slots.
        """
        super().__init__()

        self.pb_scanner = None
        self.core = mame_states_core
        """Entry point for accessing DB and in-memory data structures."""

        self.progress_bar = None
        """Reference to progress bar popup window. Prevents garbage collection and allows access."""

        self.pre_hs_table = None
        """Reference to a roms leaderboard prior to being launched."""

        self.mame_thread = None
        """Reference to thread used to launch MAME subprocess."""

        self.temp_fields = {}
        """References to 'other fields' for a given rom PB. Used to avoid garbage collection of signal connections."""

        self.rom_search_popup: QWidget | None = None
        """Reference to rom search popup window. Prevents garbage collection and allows access."""

        self.save_state_page_text_before_editing: str | None = None
        """Text of the previous selected save state item."""

        # -------------------- #
        # Widget customization #
        # -------------------- #
        self.setWindowTitle('MAME States')

        self.big_font: QFont = QFont()
        """Large font"""
        self.big_font.setPointSize(26)

        self.small_font: QFont = QFont()
        """Small font"""
        self.small_font.setPointSize(20)

        # --------- #
        # File Menu #
        # --------- #
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('&File')

        self.test_button_1_action: QAction = QAction('Test Button 1', self)
        """Used as trigger for work in progress functions."""

        self.test_button_2_action: QAction = QAction('Export Personal Bests to CSV', self)
        """Used as trigger for work in progress functions."""

        self.add_mame_directory_action: QAction = QAction('Add MAME Directory', self)
        """Trigger for 'Add MAME Directory' work flow"""

        self.update_pb_action: QAction = QAction('Update Personal Bests', self)
        """Trigger for 'Update Personal Bests' work flow"""

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
        self.save_state_and_inp_page: QWidget = QWidget()
        """Container widget. Corresponding layout is applied. Added to corresponding container tab widget."""

        self.hiscore_page: QWidget = QWidget()
        """Container widget. Corresponding layout is applied. Added to corresponding container tab widget."""

        self.rom_search_page: QWidget = QWidget()
        """Container widget. Corresponding layout is applied. Added to corresponding container tab widget."""

        # ------------------ #
        #   Save State Page  #
        # ------------------ #

        # Widgets
        self.save_state_and_inp_tree: QTreeWidget = QTreeWidget()
        """Main widget of the save state tab"""

        self.new_save_state_and_inp_tree: widgets.SaveStateInputFileTree = widgets.SaveStateInputFileTree(self.core, self.save_state_and_inp_tree)

        self.terminal_output_box: QTextEdit = QTextEdit()
        """Temporary widget for testing."""

        # Layouts
        self.save_state_and_inp_layout: QVBoxLayout = QVBoxLayout()
        """Top level page layout."""

        self.tree_container: QHBoxLayout = QHBoxLayout()
        self.tree_container.addWidget(self.save_state_and_inp_tree)
        self.tree_container.addWidget(self.new_save_state_and_inp_tree)


        self.save_state_and_inp_layout.setContentsMargins(0, 0, 0, 0)
        self.save_state_and_inp_page.setLayout(self.save_state_and_inp_layout)
        # self.save_state_and_inp_layout.addWidget(self.save_state_and_inp_tree)
        self.save_state_and_inp_layout.addLayout(self.tree_container)
        self.save_state_and_inp_layout.addWidget(self.terminal_output_box)

        # ------------------#
        #   Hiscore Page  #
        # ------------------#

        # Widgets

        self.games_with_pb_tree: QTreeWidget = QTreeWidget()
        """Contains games with personal bests information."""

        self.notes_window = widgets.NotesWindow(self)
        """Popup raw text edit window."""

        self.hiscore_add_game_button: QPushButton = QPushButton('Add Game')
        """Allow user to, manually, add game to hiscore tree."""

        self.hiscore_delete_game_button: QPushButton = QPushButton('Delete Game')
        """Allow user to, manually, remove game from hiscore tree."""

        self.split_tree: widgets.PBSplitTreeWidget = widgets.PBSplitTreeWidget(self.core, self.games_with_pb_tree, 'splits')
        """Contains stage splits for current PB."""

        self.pb_fields_tree: widgets.PBSplitTreeWidget = widgets.PBSplitTreeWidget(self.core, self.games_with_pb_tree, 'pb')
        """Contains the various fields that make up the current personal best."""

        self.add_split_button: QPushButton = QPushButton('Add Split')
        """Allow user to, manually, add a stage split to current PB."""

        self.delete_split_button: QPushButton = QPushButton('Delete Split')
        """Allow user to, manually, remove a stage split from current PB."""

        # Layouts

        self.hiscore_page_layout: QHBoxLayout = QHBoxLayout()
        """Top level page layout."""

        self.game_list_button_container: QHBoxLayout = QHBoxLayout()
        """Contains buttons related to games list."""

        self.game_list_container: QVBoxLayout = QVBoxLayout()
        """Contains list of games with personal best information and related buttons."""

        self.info_layout: QVBoxLayout = QVBoxLayout()
        """Contains PB info, stage splits, and related buttons."""

        self.splits_tree_button_container: QHBoxLayout = QHBoxLayout()
        """Contains buttons related to stage splits."""

        self.personal_best_layout = QVBoxLayout()
        """Contains PB Info"""

        # Add widgets to layout. Setup signals and slots.
        self.setup_save_state_page()
        self.setup_hiscore_panel()
        self.setup_pb_panel()
        self.setup_split_panel()

        self.personal_best_layout.addWidget(self.pb_fields_tree)
        self.info_layout.addLayout(self.personal_best_layout, 1)
        self.info_layout.addStretch()

        self.info_layout.addWidget(self.split_tree, 1)
        self.info_layout.addStretch()

        self.info_layout.addLayout(self.splits_tree_button_container)

        self.info_container = DetachableWidget(self)
        self.info_container.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.info_container.customContextMenuRequested.connect(self.show_info_container_context)
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_container.setLayout(self.info_layout)

        self.hiscore_page_layout.addLayout(self.game_list_container)
        # self.hiscore_page_layout.addLayout(self.info_layout)
        self.hiscore_page_layout.addWidget(self.info_container)
        self.hiscore_page.setLayout(self.hiscore_page_layout)

        self.hiscore_page.setFont(self.big_font)

        # --------------- #
        # Rom Search Page #
        # --------------- #

        # Widgets
        self.rom_search_bar: QLineEdit = QLineEdit()
        """Search bar used by rom search page."""

        self.debounce_timer = QTimer()
        """Timer used to delay filtering of rom list when user stops typing."""

        self.rom_search_tree: QTreeWidget = QTreeWidget()
        """List of all roms supported by MAME."""

        self.rom_search_add_game_button: QPushButton = QPushButton('Add Game')
        """Allow user to manually select a rom from list. Only appears on popup."""

        self.rom_search_cancel_button: QPushButton = QPushButton('Cancel')
        """Allow user to cancel rom search. Only appears on popup."""

        self.rom_description_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_name_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_manufacturer_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_release_year_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_parent_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_video_info_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_video_driver_warnings_label: QLabel = QLabel()
        """Used in full rom info display."""
        self.rom_audio_driver_warnings_label: QLabel = QLabel()
        """Used in full rom info display."""

        # Layouts
        self.rom_search_page_layout = QHBoxLayout()
        """Top level page layout."""

        self.rom_info_layout = QVBoxLayout()
        """Contains labels describing detailed rom info."""

        self.rom_info_container = QWidget()
        """Container widget. Corresponding layout is applied."""

        self.rom_search_panel = QVBoxLayout()
        """Contains searchbar and rom list."""

        self.rom_search_buttons = QHBoxLayout()
        """Contains buttons related to rom search."""

        self.rom_search_container = QWidget()
        """Container widget. Corresponding layout is applied."""

        # Add widgets to layout. Setup signals and slots.
        self.setup_search_page()

        # ------------------- #
        # Finalize tab setup. #
        # ------------------- #
        first_item = self.games_with_pb_tree.topLevelItem(0)
        self.games_with_pb_tree.setCurrentItem(first_item)
        self.tabs.addTab(self.save_state_and_inp_page, 'Save States')
        self.tabs.addTab(self.hiscore_page, 'Hi Score')
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
        self.test_button_1_action.triggered.connect(self.menu_button_1_clicked)
        self.test_button_2_action.triggered.connect(self.menu_button_2_clicked)
        self.add_mame_directory_action.triggered.connect(self.add_path_button_clicked)
        self.update_pb_action.triggered.connect(self.scan_for_pbs)

        self.file_menu.addAction(self.test_button_1_action)

        self.file_menu.addAction(self.add_mame_directory_action)
        self.file_menu.addAction(self.update_pb_action)
        self.file_menu.addAction(self.test_button_2_action)


    def setup_save_state_page(self) -> None:
        """Save State Page windget customization."""
        self.save_state_and_inp_tree.setEditTriggers(
            QTreeWidget.EditTrigger.AnyKeyPressed | QTreeWidget.EditTrigger.DoubleClicked)
        self.save_state_and_inp_tree.setHeaderLabels(['MAME Folders'])
        self.save_state_and_inp_tree.setColumnWidth(0, 1000)
        self.save_state_and_inp_tree.setItemDelegate(widgets.SaveStateNameInputValidator(self))
        self.save_state_and_inp_tree.setTabKeyNavigation(True)
        self.save_state_and_inp_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.save_state_and_inp_tree.customContextMenuRequested.connect(self.show_save_state_tree_context)

        self.fill_save_state_tree()
        self.save_state_and_inp_tree.currentItemChanged.connect(self.save_state_tree_selection_changed)
        # self.save_state_and_inp_tree.itemChanged.connect(self.save_state_tree_leaf_item_changed)

        self.new_save_state_and_inp_tree.currentItemChanged.connect(self.new_save_state_tree_selection_changed)
        self.new_save_state_and_inp_tree.itemChanged.connect(self.ss_or_inp_changed)
        self.new_save_state_and_inp_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.new_save_state_and_inp_tree.customContextMenuRequested.connect(self.show_new_save_state_tree_context)


    def setup_hiscore_panel(self) -> None:
        """Hi Score Panel widget customization"""
        self.notes_window.hide()
        # Fill Game List
        self.fill_hiscore_game_list()

        self.games_with_pb_tree.setHeaderLabels(['Games'])
        self.games_with_pb_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.games_with_pb_tree.customContextMenuRequested.connect(self.show_rom_item_context)
        self.games_with_pb_tree.itemSelectionChanged.connect(self.hi_score_tree_selection_changed)

        self.hiscore_add_game_button.clicked.connect(self.hiscore_add_game_clicked)
        self.hiscore_delete_game_button.clicked.connect(self.delete_game)

        self.game_list_button_container.addWidget(self.hiscore_add_game_button)
        self.game_list_button_container.addWidget(self.hiscore_delete_game_button)

        self.game_list_container.addWidget(self.games_with_pb_tree)
        self.game_list_container.addLayout(self.game_list_button_container)

    def setup_pb_panel(self) -> None:
        """Personal Best Panel widget customization."""
        self.pb_fields_tree.setFont(self.small_font)

    def setup_split_panel(self) -> None:
        """Split Panel widget customization."""
        self.splits_tree_button_container.addWidget(self.add_split_button)
        self.splits_tree_button_container.addWidget(self.delete_split_button)

        self.add_split_button.clicked.connect(self.add_split_clicked)
        self.delete_split_button.clicked.connect(self.delete_split_clicked)

    def setup_search_page_layout(self):
        self.rom_search_container.setLayout(self.rom_search_panel)

        # self.rom_search_container.setFixedWidth(600)
        self.rom_search_panel.addWidget(self.rom_search_bar)
        self.rom_search_panel.addWidget(self.rom_search_tree)
        self.rom_search_buttons.addWidget(self.rom_search_add_game_button)
        self.rom_search_buttons.addWidget(self.rom_search_cancel_button)
        self.rom_search_panel.addLayout(self.rom_search_buttons)
        self.rom_search_add_game_button.hide()
        self.rom_search_cancel_button.hide()

        self.rom_info_container.setLayout(self.rom_info_layout)
        # self.rom_info_container.setFixedWidth(600)
        self.rom_info_container.setFont(self.small_font)
        self.rom_info_layout.addWidget(self.rom_description_label)
        self.rom_info_layout.addWidget(self.rom_name_label)
        self.rom_info_layout.addWidget(self.rom_manufacturer_label)
        self.rom_info_layout.addWidget(self.rom_release_year_label)
        self.rom_info_layout.addWidget(self.rom_parent_label)
        self.rom_info_layout.addWidget(self.rom_video_info_label)
        self.rom_info_layout.addWidget(self.rom_video_driver_warnings_label)
        self.rom_info_layout.addWidget(self.rom_audio_driver_warnings_label)
        self.rom_info_layout.addStretch()

        self.rom_search_page_layout.addWidget(self.rom_search_container)
        self.rom_search_page_layout.addWidget(self.rom_info_container)

        self.rom_search_page.setLayout(self.rom_search_page_layout)
        self.rom_search_page.setFont(self.big_font)

    def setup_search_page(self):
        """Search Page widget customization."""
        self.rom_search_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rom_search_tree.customContextMenuRequested.connect(self.show_rom_item_context)
        self.rom_search_bar.setPlaceholderText('Search items...')
        self.rom_search_bar.textChanged.connect(self.on_text_changed)

        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.update_filter)

        self.rom_search_tree.setHeaderLabels(['Games'])
        for rom_description in self.core.descriptions_and_names:
            item = QTreeWidgetItem(self.rom_search_tree, [rom_description])
            parent = self.core.rom_info[rom_description].parent
            if parent is not None:
                self.paint_clone_rom_item(item)

            item.setToolTip(0, self.core.descriptions_and_names[rom_description])

        self.rom_search_cancel_button.clicked.connect(self.close_rom_search_window)
        self.rom_search_add_game_button.clicked.connect(self.rom_search_add_game_clicked)
        self.rom_search_tree.itemSelectionChanged.connect(self.rom_search_tree_selection_changed)

        self.rom_description_label.setWordWrap(True)

        self.setup_search_page_layout()

    # ------ #
    # Helper #
    # ------ #
    def update_pb_panel(self, hiscore: int, other_fields: dict[str, str | int]) -> None:
        """Clear and refill PB Fields List."""
        self.temp_fields.clear()
        # with QSignalBlocker(self.pb_fields_tree):
        self.pb_fields_tree.add_editable_item('Hi Score', hiscore)
        if other_fields:
            for field_name in other_fields:
                self.pb_fields_tree.add_editable_item(field_name, other_fields[field_name])

    @staticmethod
    def paint_clone_rom_item(item: QTreeWidgetItem) -> None:
        """Paint the given item light grey. """
        color = QColor(211, 211, 211, 127)
        brush = QBrush(color)
        item.setForeground(0, brush)

    def create_rom_search_item(self, rom_description, rom_name, weight=3) -> tuple[QTreeWidgetItem, int]:
        """Create and return rom item, set tooltip to rom name, pain item if is clone."""
        item = QTreeWidgetItem([rom_description])
        item.setToolTip(0, rom_name)
        parent = self.core.rom_info[rom_description].parent
        if parent is not None:
            self.paint_clone_rom_item(item)

        return item, weight

    def valid_path(self, mame_dir: Path) -> bool | None:
        """Validate the given MAME path.

        Return True, if valid, False if 'retry', None if 'cancel'.
        """
        mame_exe = mame_dir / 'mame.exe'
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

    def get_mame_dir(self) -> core.MAMEDir | None:
        """Prompt user for a MAME directory using a file dialog.

        Loops if invalid path and user selects 'retry'.
        """
        mame_path = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                     options=QFileDialog.Option.ShowDirsOnly)

        mame_path = Path(mame_path)
        mame_version = core.get_mame_version(mame_path)
        mame_dir = core.MAMEDir(mame_path, mame_version)

        path_validity = self.valid_path(mame_path)
        if path_validity is True:
            return mame_dir
        if path_validity is False:
            self.get_mame_dir()

        return path_validity

    def fill_hiscore_game_list(self) -> None:
        """Clear and refill Hi Score Game Tree, based on personal best info."""
        with QSignalBlocker(self.games_with_pb_tree):
            self.games_with_pb_tree.clear()
            for rom_description in self.core.pb_info:
                QTreeWidgetItem(self.games_with_pb_tree, [rom_description])

    def fill_save_state_tree(self) -> None:
        """Clear, then fill and customize the Save State Tree Widget.

        Font size is configured on each item. Large for parent items, small for leaf items.
        Leaf items are made editable via flags.
        """
        self.save_state_and_inp_tree.clear()

        # Add path items.
        for mame_dir in self.core.mame_dirs:
            mame_dir_item = QTreeWidgetItem(self.save_state_and_inp_tree, [str(mame_dir.path.name)])
            mame_dir_item.setData(0, Qt.ItemDataRole.UserRole, str(mame_dir.path))
            mame_dir_item.setFont(0, self.big_font)
            save_states_container_item = QTreeWidgetItem(mame_dir_item, ['Save States'])
            save_states_container_item.setFont(0, self.big_font)
            input_files = self.core.input_files.get(str(mame_dir.path))
            if input_files:
                input_files_container_item = QTreeWidgetItem(mame_dir_item, ['Input Files'])
                input_files_container_item.setFont(0, self.big_font)
                # for file in input_files:
                #     item = QTreeWidgetItem(input_files_container_item, [file])
                #     item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                #     item.setFont(0, self.small_font)

            # Add game items.
            for rom_name in self.core.save_states[str(mame_dir.path)]:
                game_description = self.core.rom_description_from_name(rom_name)
                game_item = QTreeWidgetItem(save_states_container_item, [game_description])
                game_item.setFont(0, self.big_font)

                # # Add savestate items.
                # for save_state in self.core.save_states[str(mame_dir.path)][rom_name]:
                #     save_state_item = QTreeWidgetItem(game_item, [save_state.stem])
                #     save_state_item.setFlags(save_state_item.flags() | Qt.ItemFlag.ItemIsEditable)
                #     save_state_item.setFont(0, self.small_font)

    def fill_inps(self, mame_dir: str) -> None:
        self.new_save_state_and_inp_tree.setHeaderLabel('Input Files')
        input_files = self.core.input_files.get(str(mame_dir))
        for file in input_files:
            item = self.new_save_state_and_inp_tree.add_editable_item(file)
            # item = QTreeWidgetItem(self.new_save_state_and_inp_tree, [file])
            # item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setFont(0, self.small_font)

    def fill_saves(self, mame_dir: str, rom_description: str) -> None:
        self.new_save_state_and_inp_tree.setHeaderLabel('Save States')

        rom_name = self.core.descriptions_and_names[rom_description]
        for save_state in self.core.save_states[mame_dir][rom_name]:
            save_state_item = self.new_save_state_and_inp_tree.add_editable_item(save_state.stem)
            # save_state_item = QTreeWidgetItem(self.new_save_state_and_inp_tree, [save_state.stem])
            # save_state_item.setFlags(save_state_item.flags() | Qt.ItemFlag.ItemIsEditable)
            save_state_item.setFont(0, self.small_font)


    #########
    # Slots #
    #########
    # ------------------------- #
    # Personal Bests Page Slots #
    # ------------------------- #
    def close_rom_search_window(self) -> None:
        """Close rom search popup.

        Can't connect self.rom_search_popup.close() directly, as it does not exist at the time of initialization.
        """
        self.rom_search_popup.close()

    def hi_score_tree_selection_changed(self) -> None:
        """Clear and refill 'splits list' and 'pb panel' based on currently selected item.

        Split diffs are calculated and displayed.
        """
        self.pb_fields_tree.clear()
        self.split_tree.clear()

        selected_item = self.games_with_pb_tree.currentItem()
        if selected_item:
            rom_description = selected_item.text(0)
            pb = self.core.pb_info[rom_description]

            self.update_pb_panel(pb.hiscore, pb.other_fields)
            for split in pb.splits:
                # with QSignalBlocker(self.split_tree):
                self.split_tree.add_editable_item(split.label, split.score)
            self.split_tree.add_diffs(pb.splits)
        # After adding all items
        for i in range(self.pb_fields_tree.columnCount()):
            self.pb_fields_tree.resizeColumnToContents(i)
            self.pb_fields_tree.setColumnWidth(0, self.pb_fields_tree.columnWidth(0) + 10)

        for i in range(self.split_tree.columnCount()):
            self.split_tree.resizeColumnToContents(i)
            self.split_tree.setColumnWidth(0, self.pb_fields_tree.columnWidth(0) + 1)


    def hiscore_add_game_clicked(self) -> None:
        """Pop out Rom Search Tab and allow user to choose a rom. Main window is disabled."""

        # self.tabs.removeTab(2)
        search_tab_index = self.tabs.indexOf(self.rom_search_page)
        self.tabs.removeTab(search_tab_index)
        self.rom_search_popup = widgets.RomSearchWindow(self.rom_search_page, self.tabs,
                                                        self.rom_search_add_game_button,
                                                        self.rom_search_cancel_button)
        self.rom_search_popup.show()
        self.setEnabled(False)

    def rom_search_add_game_clicked(self) -> None:
        """Create new Hi Score Game Tree item, based on user selection. Game is added to pb info and database.

        Duplicate games are disallowed. Popup closes upon valid selection. New game is focused.
        """
        selected_item = self.rom_search_tree.currentItem()
        if selected_item:

            rom_description = selected_item.text(0)
            if rom_description in self.core.pb_info:
                QMessageBox.critical(self, 'Error', 'That Game already has a PB entry.')
                self.rom_search_popup.raise_()
                self.rom_search_popup.setFocus()
                return

            new_item = QTreeWidgetItem(self.games_with_pb_tree, [rom_description])
            rom_id = self.core.id_from_description(rom_description)

            self.core.pb_info[rom_description] = core.PersonalBest(0, rom_id)

            self.core.save_pb_to_database()
            self.rom_search_popup.close()
            self.games_with_pb_tree.setCurrentItem(new_item)

    def delete_game(self) -> None:
        """Delete game from Hiscore Game Tree and remove all its information from database.

        Item selection is moved programmatically before deleting.
        """
        selected_item = self.games_with_pb_tree.currentItem()
        if selected_item:

            confirmation = QMessageBox.question(self, 'Confirm.', f'Are you sure you would like to delete PB entry for: {selected_item.text(0)}')
            if confirmation != QMessageBox.StandardButton.Yes:
                return

            previous_item = self.games_with_pb_tree.itemAbove(selected_item)
            next_item = self.games_with_pb_tree.itemBelow(selected_item)

            # Move selection before deleting.
            if previous_item:
                self.games_with_pb_tree.setCurrentItem(previous_item)
            elif next_item:
                self.games_with_pb_tree.setCurrentItem(next_item)
            else:
                self.games_with_pb_tree.clearSelection()

            rom_description = selected_item.text(0)
            # Delete from in-memory database representation.
            del self.core.pb_info[rom_description]
            # Delete from database.
            self.core.delete_personal_best(rom_description)
            self.core.delete_splits(rom_description)

            # Finally, remove item from Hiscore Game Tree.
            game_item_index = self.games_with_pb_tree.indexFromItem(selected_item)
            game_row = game_item_index.row()
            self.games_with_pb_tree.takeTopLevelItem(game_row)

    def add_split_clicked(self) -> None:
        rom_description = self.games_with_pb_tree.currentItem().text(0)
        split_name, ok = QInputDialog.getText(self, 'User Input', 'Split Name', text='Placeholder')
        if split_name and ok:
            splits = self.core.pb_info[rom_description].splits
            split_names = [split.label for split in splits]
            if split_name in split_names:
                QMessageBox.critical(self, 'Error', 'Name already in use for this rom. Try again.')
                self.add_split_clicked()
            else:
                rom_id = self.core.id_from_description(rom_description)
                new_split = core.StageSplit(split_name, 0, rom_id)
                self.core.pb_info[rom_description].splits.append(new_split)
                # with QSignalBlocker(self.split_tree):
                #     new_item = self.split_tree.add_editable_item(new_split.label, new_split.score)
                new_item = self.split_tree.add_editable_item(new_split.label, new_split.score)
                self.split_tree.add_diffs(splits)
                self.split_tree.editItem(new_item, 1)

    def delete_split_clicked(self) -> None:
        rom_description = self.games_with_pb_tree.currentItem().text(0)
        selected_split_item = self.split_tree.currentItem()
        if not selected_split_item:
            return
        item_above = self.split_tree.itemAbove(selected_split_item)
        item_below = self.split_tree.itemBelow(selected_split_item)

        if item_above:
            self.split_tree.setCurrentItem(item_above)
        elif item_below:
            self.split_tree.setCurrentItem(item_below)


        split_index = self.split_tree.indexOfTopLevelItem(selected_split_item)

        split = self.core.pb_info[rom_description].splits.pop(split_index)
        self.core.delete_split(rom_description, split.label)
        self.split_tree.takeTopLevelItem(split_index)
        self.split_tree.add_diffs(self.core.pb_info[rom_description].splits)



    def open_notes(self, some_list: QTreeWidget) -> None:
        """Open notes widget.

        Open the notes widget and change the title to reflect the currently selected item.
        If [rom_name].txt exists, copy data into the notes widget. Otherwise, create [rom_name].txt. Focus notes widget.
        A reference is held to the notes widget to avoid it being automatically deleted. Cannot open multiple notes.
        """
        rom_description = some_list.currentItem().text(0)
        rom_name = self.core.descriptions_and_names[rom_description]
        if self.notes_window.isHidden():
            self.notes_window.show()

        notes_file = Path('./notes') / (rom_name + '.txt')
        notes_file = core.get_abs_path(notes_file)
        print(notes_file.resolve())

        if not notes_file.is_file():
            notes_file.touch()

        with open(notes_file, 'r') as notes:
            text = notes.read()
            if not text:
                text = ''
            self.notes_window.text_edit.setText(text)
        self.notes_window.current_game = rom_name
        self.notes_window.setWindowTitle(f'{rom_description} - Notes')
        self.notes_window.raise_()
        self.notes_window.setFocus()

    def run_mame(self, mame_path: str):
        """Launch MAME.exe from given MAME directory. If MAME directory is found to be invalid, it is removed."""
        mame_dir = Path(mame_path)
        mame_exe = mame_dir / 'mame.exe'
        if mame_exe.is_file():
            self.mame_thread = widgets.MAMEProcess(mame_dir, self.terminal_output_box)
            # subprocess.Popen(mame_exe, cwd=rf'{mame_dir}')
        else:
            self.remove_invalid_mame_dir(mame_path=mame_path)
            print(f'File {mame_exe} not found')


    def remove_invalid_mame_dir(self, *, mame_path: str | None = None, path_item: QTreeWidgetItem | None = None) -> None:
        """Remove MAME directory and all related info(saves, inps, ect) from GUI, in-memory datastructures, and DB

        Use path_item if called from context menu where item is available, then derive mame_path.
        Use mame_path if called from anywhere else, then derive item from path.
        """
        if path_item:
            mame_path = path_item.data(0, Qt.ItemDataRole.UserRole)
            root = self.save_state_and_inp_tree.invisibleRootItem()
            selected_dir = self.save_state_and_inp_tree.currentItem()
            root.removeChild(selected_dir)

        elif mame_path:
            for _ in range(self.save_state_and_inp_tree.topLevelItemCount()):
                if self.save_state_and_inp_tree.topLevelItem(_).text(0) == mame_path:
                    self.save_state_and_inp_tree.takeTopLevelItem(_)
                    QMessageBox.critical(self, 'Error',
                                         'Invalid MAME Directory.\nDirectory has been removed. Please update it.')
                    break

        self.core.new_remove_invalid_mame_dir(mame_path)


    def open_ini_actioned_clicked(self) -> None:
        """Attempt to open the .ini file for the selected MAME directory.

        If a .ini file does not exist, user is given the choice to create a new one.
        """
        mame_dir_item = self.save_state_and_inp_tree.currentItem()
        path_str = mame_dir_item.data(0, Qt.ItemDataRole.UserRole)
        mame_path = Path(path_str)
        if Path(path_str).is_dir():
            mame_ini_file = mame_path / 'mame.ini'
            if mame_ini_file.is_file():
                os.startfile(mame_ini_file)
            else:
                response = QMessageBox.question(self, 'Directory Not Found',
                                                f'Could Not Find File: {mame_ini_file}\nWould you like to create a new ini file?')
                if response == QMessageBox.StandardButton.Yes:
                    subprocess.run([core.get_abs_path(mame_path / 'mame.exe'), '-cc'], cwd=core.get_abs_path(mame_path))
        else:
            self.remove_invalid_mame_dir(mame_path=path_str)

    def open_mame_dir_in_explorer(self, mame_dir_item: QTreeWidgetItem) -> None:
        """Attempt to open a given MAME directory in Windows explorer.

        If the path is found to be invalid, it is removed from the app completely.
        """
        mame_dir = Path(mame_dir_item.data(0, Qt.ItemDataRole.UserRole))
        if not mame_dir.is_dir():
            self.remove_invalid_mame_dir(mame_path=str(mame_dir))
            return
        os.startfile(mame_dir)

    def show_save_state_tree_context(self, position: QPoint) -> None:
        """Create custom context menu, connect slots, execute menu.

        If no item is selected, no menu is created.
        """
        tree_item = self.save_state_and_inp_tree.itemAt(position)
        if not tree_item:
            return

        menu = QMenu()
        if tree_item.parent() is None:
            launch = QAction('Launch')
            delete = QAction('Delete')
            open_ini = QAction('Open mame.ini')
            open_in_explorer = QAction('Open in Explorer')

            launch.triggered.connect(lambda: self.run_mame(tree_item.data(0, Qt.ItemDataRole.UserRole)))
            delete.triggered.connect(lambda: self.remove_invalid_mame_dir(path_item=tree_item))
            open_ini.triggered.connect(self.open_ini_actioned_clicked)
            open_in_explorer.triggered.connect(lambda: self.open_mame_dir_in_explorer(tree_item))

            menu.addAction(launch)
            menu.addAction(open_ini)
            menu.addAction(delete)
            menu.addAction(open_in_explorer)

        elif tree_item.text(0) == 'Input Files' or tree_item.text(0) == 'Save States':
            open_in_explorer = QAction('Open in Explorer')
            open_in_explorer.triggered.connect(lambda: self.open_save_or_inp_in_explorer(tree_item))
            menu.addAction(open_in_explorer)

        else:
            if tree_item.parent().text(0) == 'Save States':  # Lazy way to ensure rom items don't spawn menu.
                rom_description = tree_item.text(0)
                rom_name = self.core.descriptions_and_names[rom_description]
                open_notes = QAction('Open Notes')
                open_notes.triggered.connect(lambda: self.open_notes(self.save_state_and_inp_tree))
                menu.addAction(open_notes)

                open_with_submenu = QMenu('Open with...')
                for mame_dir in self.core.mame_dirs:
                    run = QAction(str(mame_dir.path), self)
                    run.triggered.connect(lambda: self.run_rom(rom_name))
                    open_with_submenu.addAction(run)

                open_with_inp_submenu = QMenu('Open with input file...')
                for mame_dir in self.core.mame_dirs:
                    run_and_record_inp = QAction(str(mame_dir.path), self)
                    run_and_record_inp.triggered.connect(lambda: self.run_rom(rom_name, record_input=True))
                    open_with_inp_submenu.addAction(run_and_record_inp)

                menu.addMenu(open_with_submenu)
                menu.addMenu(open_with_inp_submenu)
            # delete = QAction('Delete')
            # delete.triggered.connect(lambda: self.delete_leaf_item(tree_item))
            # menu.addAction(delete)

            # if tree_item.parent().text(0) == 'Input Files':
            #     input_file_name = tree_item.text(0)
            #     rom_name = input_file_name.split('_')[0]  # inp files created by program will have rom name at start.
            #
            #     sub_menu = QMenu('Playback with...')
            #     for mame_dir in self.core.mame_dirs:
            #         run = QAction(str(mame_dir.path), self)
            #         run.triggered.connect(
            #             lambda: self.run_rom(rom_name, play_back_input=True, input_file_name=input_file_name))
            #         sub_menu.addAction(run)
            #         menu.addMenu(sub_menu)
        menu.exec(self.save_state_and_inp_tree.viewport().mapToGlobal(position))

    def show_new_save_state_tree_context(self, position: QPoint):
        menu = QMenu()
        delete = QAction('Delete')
        delete.triggered.connect(lambda: self.delete_ss_or_inp(tree_item))
        menu.addAction(delete)
        tree_item = self.new_save_state_and_inp_tree.itemAt(position)
        if not tree_item:
            return

        if self.new_save_state_and_inp_tree.headerItem().text(0) == 'Input Files':
            input_file_name = tree_item.text(0)
            rom_name = input_file_name.split('_')[0]  # inp files created by program will have rom name at start.

            sub_menu = QMenu('Playback with...')
            for mame_dir in self.core.mame_dirs:
                run = QAction(str(mame_dir.path), self)
                run.triggered.connect(
                    lambda: self.run_rom(rom_name, play_back_input=True, input_file_name=input_file_name))
                sub_menu.addAction(run)
                menu.addMenu(sub_menu)


        menu.exec(self.new_save_state_and_inp_tree.viewport().mapToGlobal(position))

    def delete_ss_or_inp(self, tree_item: QTreeWidgetItem):
        if self.new_save_state_and_inp_tree.headerItem().text(0) == 'Input Files':
            mame_dir_item = self.save_state_and_inp_tree.currentItem().parent()
            mame_dir_str = mame_dir_item.data(0, Qt.ItemDataRole.UserRole)
            mame_dir = Path(mame_dir_str)
            if not mame_dir.is_dir():
                self.remove_invalid_mame_dir(mame_path=mame_dir_str)
                return

            input_file_dir = mame_dir / 'inp'
            input_file = input_file_dir / f'{tree_item.text(0)}.inp'
            if input_file.is_file():
                input_file.unlink()
            else:
                QMessageBox.critical(self, 'Error', 'File does not exist.')

        if self.new_save_state_and_inp_tree.headerItem().text(0) == 'Save States':
            rom_item = self.save_state_and_inp_tree.currentItem()
            rom_description = rom_item.text(0)
            rom_name = self.core.descriptions_and_names[rom_description]
            # category_item = direct_parent.parent()
            mame_path_item = rom_item.parent().parent()
            mame_dir_str = mame_path_item.data(0, Qt.ItemDataRole.UserRole)
            mame_dir = Path(mame_dir_str)
            if not mame_dir.is_dir():
                self.remove_invalid_mame_dir(mame_path=mame_dir_str)
                return
            save_states_dir = mame_dir / 'sta'
            rom_saves_dir = save_states_dir / f'{rom_name}'
            save_state_file = rom_saves_dir / f'{tree_item.text(0)}.sta'
            if save_state_file.is_file():
                save_state_file.unlink()
            else:
                QMessageBox.critical(self, 'Error', 'File does not exist.')

        item_index = self.new_save_state_and_inp_tree.indexOfTopLevelItem(tree_item)
        self.new_save_state_and_inp_tree.takeTopLevelItem(item_index)
        self.core.save_states = self.core.new_get_save_states()
        self.core.input_files = self.core.get_input_files()

    def delete_leaf_item(self, leaf_item: QTreeWidgetItem) -> None:
        """Delete a childless QTreeWidgetItem. The corresponding file is also deleted.

        MAME paths are validated and removed if found to be invalid.
        """
        answer = QMessageBox.question(self, 'Stop', f'Are you sure you wish to delete: {leaf_item.text(0)}?')
        if answer == QMessageBox.StandardButton.No:
            return
        direct_parent = leaf_item.parent()

        if direct_parent.text(0) == 'Input Files':
            mame_dir_str = direct_parent.parent().text(0)
            mame_dir = Path(mame_dir_str)
            if not mame_dir.is_dir():
                self.remove_invalid_mame_dir(mame_path=mame_dir_str)
                return
            input_file_dir = mame_dir / 'inp'
            input_file = input_file_dir / f'{leaf_item.text(0)}.inp'
            if input_file.is_file():
                input_file.unlink()
            else:
                QMessageBox.critical(self, 'Error', 'File does not exist.')

        else:
            rom_description = direct_parent.text(0)
            rom_name = self.core.descriptions_and_names[rom_description]
            category_item = direct_parent.parent()
            mame_path_item = category_item.parent()
            mame_dir_str = mame_path_item.text(0)
            mame_dir = Path(mame_dir_str)
            if not mame_dir.is_dir():
                self.remove_invalid_mame_dir(mame_path=mame_dir_str)
                return
            save_states_dir = mame_dir / 'sta'
            rom_saves_dir = save_states_dir / f'{rom_name}'
            save_state_file = rom_saves_dir / f'{leaf_item.text(0)}.sta'
            if save_state_file.is_file():
                save_state_file.unlink()
            else:
                QMessageBox.critical(self, 'Error', 'File does not exist.')

        direct_parent.removeChild(leaf_item)

    def open_save_or_inp_in_explorer(self, category_item: QTreeWidgetItem) -> None:
        """Opens a MAME directory's 'inp', and 'sta' folders in Windows explorer."""
        mame_dir = Path(category_item.parent().data(0, Qt.ItemDataRole.UserRole))
        if not mame_dir.is_dir():
            self.remove_invalid_mame_dir(mame_path=str(mame_dir))
            return
        if category_item.text(0) == 'Input Files':
            input_file_dir = mame_dir / 'inp'
            if input_file_dir.is_dir():
                os.startfile(input_file_dir)
            else:
                QMessageBox.critical(self, 'Directory Not Found', f'Could Not Find Directory: {input_file_dir}')

        if category_item.text(0) == 'Save States':
            save_states_dir = mame_dir / 'sta'
            if save_states_dir.is_dir():
                os.startfile(save_states_dir)
            else:
                QMessageBox.critical(self, 'Directory Not Found', f'Could Not Find Directory: {save_states_dir}')

    def show_rom_item_context(self, position: QPoint) -> None:
        """Create custom context menu, connect slots, execute menu.

        If no item is selected, no menu is created. Menu includes 'open notes' and 'open with' functions, based on game.
        """
        tree_clicked: QTreeWidget = self.sender()
        tree_item = tree_clicked.itemAt(position)

        if not tree_item:
            return

        rom_description = tree_item.text(0)
        rom_name = self.core.descriptions_and_names[rom_description]

        menu = QMenu()

        open_notes = QAction('Open Notes')
        open_notes.triggered.connect(lambda: self.open_notes(tree_clicked))
        menu.addAction(open_notes)

        open_with_submenu = QMenu('Open with...')
        for mame_dir in self.core.mame_dirs:
            run = QAction(str(mame_dir.path), self)
            run.triggered.connect(lambda: self.run_rom(rom_name))
            open_with_submenu.addAction(run)

        open_with_inp_submenu = QMenu('Open with input file...')
        for mame_dir in self.core.mame_dirs:
            run_and_record_inp = QAction(str(mame_dir.path), self)
            run_and_record_inp.triggered.connect(lambda: self.run_rom(rom_name, record_input=True))
            open_with_inp_submenu.addAction(run_and_record_inp)

        menu.addMenu(open_with_submenu)
        menu.addMenu(open_with_inp_submenu)
        menu.exec(self.sender().mapToGlobal(position))

    def show_info_container_context(self, position: QPoint):
        menu = QMenu()
        detach = QAction('Detach')
        detach.triggered.connect(self.detach_info_container)
        menu.addAction(detach)
        menu.exec(self.info_container.mapToGlobal(position))

    def detach_info_container(self):
        main_geo = self.geometry()
        self.hiscore_page_layout.removeWidget(self.info_container)
        self.info_container.setWindowFlags(Qt.WindowType.Window)
        self.info_container.setFont(self.big_font)

        popup_width, popup_height = 500, 500
        self.info_container.resize(popup_width, popup_height)

        if not self.info_container.has_been_moved:
            # Calculate coordinates to center over main window on first pop out
            center_x = main_geo.x() + int((main_geo.width() - popup_width) / 2)
            center_y = main_geo.y() + int((main_geo.height() - popup_height) / 2)
            self.info_container.move(QPoint(center_x, center_y))
        else:
            # Use cached coordinates on subsequent pop outs
            self.info_container.move(self.info_container.saved_position)

        self.info_container.show()
        self.info_container.customContextMenuRequested.disconnect(self.show_info_container_context)

    def attach_info_container(self):
        self.info_container.setWindowFlags(Qt.WindowType.Widget)
        self.hiscore_page_layout.addWidget(self.info_container)
        self.info_container.show()
        self.info_container.customContextMenuRequested.connect(self.show_info_container_context)

    def open_rom_for_inp_search(self) -> str:
        """Pop out the 'rom search' tab for use as a search dialog. Rom info is hidden until dialog closes."""
        search_tab_index = self.tabs.indexOf(self.rom_search_page)
        self.tabs.removeTab(search_tab_index)
        self.rom_info_container.hide()
        dialog = widgets.RomSearchDialog(widgets.RomSearchWindow(self.rom_search_page, self.tabs), self.rom_search_tree,
                                         parent=self)
        dialog.exec()
        self.rom_info_container.show()
        self.tabs.addTab(dialog.rom_search_popup, 'Rom Search')
        return dialog.rom_description_for_inp

    # TODO Don't need to do hi2txt if playback.
    def run_rom(self, rom_name: str, record_input=False, play_back_input=False, input_file_name=None) -> None:
        """Attempt to run a rom, with a given MAME path.

        If the rom is hi2txt compatible, a snapshot is taken of current hi score tables.
        This function does not currently check for a roms existence before trying to run it. MAME errors used instead.
        MAME is run in by spawning a subprocess. The subprocess is spawned in a separate thread to avoid blocking GUI.
        """
        # The action that triggered this function call. Its label has the correct MAME path.
        action = self.sender()
        mame_dir = action.text()

        mame_exe = Path(mame_dir) / 'mame.exe'
        # TODO This should explicitly check for dir or exe existence. Currently checks for exe, but deletes dir.
        if not mame_exe.is_file():
            self.remove_invalid_mame_dir(mame_path=mame_dir)
            return

        hiscore_file = Path(mame_dir) / 'hiscore' / (rom_name + '.hi')
        hi2txt_compatible = hi2txt_wrapper.has_xml(rom_name)
        print(core.get_abs_path(r'./hi2txt/hi2txt.exe'))
        if hi2txt_compatible:
            hi2txt_results = subprocess.run(
                [core.get_abs_path(r'./hi2txt/hi2txt.exe').resolve(), '-r', f'{hiscore_file}'],
                cwd=core.get_abs_path(r'./hi2txt').resolve(), capture_output=True, text=True,
                check=True, encoding='utf-8')
            self.pre_hs_table = hi2txt_results.stdout

        # TODO This may need to be a value error. Shouldn't ever have an invalid name. At least not caused by anything the end user can do via GUI.
        if rom_name not in list(self.core.descriptions_and_names.values()):
            QMessageBox.critical(self, 'Error', 'Input File cannot be played back without a valid rom.')
            rom_description = self.open_rom_for_inp_search()
            if rom_description:
                rom_name = self.core.descriptions_and_names[rom_description]


        self.mame_thread = widgets.MAMEProcess(Path(mame_dir), self.terminal_output_box, rom_name, record_input=record_input, playback_input=play_back_input, input_file_name=input_file_name)
        self.mame_thread.finished.connect(self.rom_done)

        print(f'Running {rom_name}, from {action.text()}')

    def rom_done(self) -> None:
        """Perform actions after rom finishes running.

        If rom is hi2txt compatible, a new snapshot is taken of roms hiscore tables. Tables are compared to find PB.
        If new PB is found, user is prompted to add or discard new PB.
        """

        hiscore_file = Path(self.mame_thread.mame_dir) / 'hiscore' / (self.mame_thread.rom_name + '.hi')
        if not hiscore_file.is_file():
            self.showNormal()
            self.raise_()
            self.activateWindow()
            return
        hi2txt_results = subprocess.run(
            [core.get_abs_path(r'./hi2txt/hi2txt.exe'), '-r', f'{hiscore_file}'],
            cwd=core.get_abs_path(r'./hi2txt'), capture_output=True,
            text=True,
            check=True, encoding='utf-8')

        post_hs_table = hi2txt_results.stdout
        test_dic = {self.mame_thread.mame_dir: {self.mame_thread.rom_name: post_hs_table}}
        if self.pre_hs_table:

            new_pb = hi2txt_wrapper.get_new_pb(self.pre_hs_table, post_hs_table)
            if new_pb == hi2txt_wrapper.Hi2TxtError.INCOMPATIBLE_TABLE_SCHEMA:
                QMessageBox.critical(self, 'Error', "Incompatible hiscore table schema detected. Hi2txt may have "
                                                    "been updated. Please manually remove previous hiscore entry "
                                                    "and run a manual PB scan.")
                return
            if new_pb:
                response = QMessageBox.question(self, 'New PB Detected!',
                                                f'A new personal best has been detected\n{new_pb['col']}\n{new_pb['row']}\nWould you like to add new PB?')
                if response == QMessageBox.StandardButton.Yes:
                    # new_pb = hi2txt_wrapper.prepare_pb_for_db(new_pb, self.mame_thread.rom_name, self.core.cursor)
                    # hi2txt_wrapper.save_pbs(new_pb, self.core.connection, self.core.cursor)
                    hi2txt_wrapper.save_pb(new_pb, self.mame_thread.rom_name, self.core.connection, self.core.cursor)
                    QMessageBox.information(self, 'Ok', 'Pb Updated!')
                else:
                    QMessageBox.information(self, 'Ok', 'PB discarded.')

        else:
            new_pb = hi2txt_wrapper._get_new_pbs(test_dic, self.core.cursor)
            pprint.pp(new_pb)
            if new_pb:
                response = QMessageBox.question(self, 'New PB Detected!',
                                                f'A new personal best has been detected\n{new_pb}\nWould you like to add new PB?')
                if response == QMessageBox.StandardButton.Yes:
                    # new_pb = hi2txt_wrapper.prepare_pb_for_db(new_pb, self.mame_thread.rom_name, self.core.cursor)
                    # hi2txt_wrapper.save_pbs(new_pb, self.core.connection, self.core.cursor)
                    hi2txt_wrapper._save_pbs(new_pb, self.core.connection, self.core.cursor)
                    QMessageBox.information(self, 'Ok', 'Pb Updated!')
                else:
                    QMessageBox.information(self, 'Ok', 'PB discarded.')

        self.core.pb_info = self.core.get_personal_bests()
        self.fill_hiscore_game_list()
        rom_description = self.core.rom_description_from_name(self.mame_thread.rom_name)
        rom_item = self.games_with_pb_tree.findItems(rom_description, Qt.MatchFlag.MatchExactly)[0]
        if rom_item:
            self.games_with_pb_tree.scrollToItem(rom_item)
            self.games_with_pb_tree.setCurrentItem(rom_item)
            self.showNormal()
            self.raise_()
            self.activateWindow()
    # --------------------- #
    # Rom Search Page Slots #
    # --------------------- #
    def on_text_changed(self) -> None:
        """Start a timer used to delay rom search filtering."""
        self.debounce_timer.start(300)

    def update_filter(self) -> None:
        """Filter the rom search list based on searchbar text.

        Search is case-insensitive. List is cleared before adding back items that clear filter.
        Items are colored based on rom lineage. Clone roms are colored light grey.
        Implements weighted sorting on resulting list. Exact match > Starts with > contains.
        """
        search_text = self.rom_search_bar.text().lower()
        self.rom_search_tree.clear()
        items = []
        for rom_description, rom_name in self.core.descriptions_and_names.items():
            if search_text == rom_name.lower() or search_text == rom_description.lower():
                weight = 1
                item = self.create_rom_search_item(rom_description, rom_name, weight)
                items.append(item)

            elif rom_name.lower().startswith(search_text) or rom_description.lower().startswith(search_text):
                weight = 2
                item = self.create_rom_search_item(rom_description, rom_name, weight)
                items.append(item)

            elif search_text in rom_name.lower() or search_text in rom_description.lower():
                weight = 3
                item = self.create_rom_search_item(rom_description, rom_name, weight)
                items.append(item)

        items.sort(key=lambda x: (x[1], x[0].text(0)))

        for item in items:
            self.rom_search_tree.addTopLevelItem(item[0])

    def rom_search_tree_selection_changed(self) -> None:
        """Clear and attempt to refill Rom Search Info Panel based on selected item.

        Info Panel is hidden/shown depending on if search tab is detached or not.
        """
        selected_item = self.rom_search_tree.currentItem()
        if selected_item:
            if self.tabs.count() == 3:
                self.rom_info_container.show()
            else:
                if self.rom_info_container.isVisible():
                    self.rom_info_container.hide()
            rom_description = selected_item.text(0)
            rom_info = self.core.rom_info[rom_description]
            self.rom_description_label.setText(f'Game: {rom_description}')
            self.rom_name_label.setText(f'Rom Name: {rom_info.name}')
            self.rom_manufacturer_label.setText(f'Manufacturer: {rom_info.manufacturer}')
            self.rom_release_year_label.setText(f'Year: {rom_info.year}')
            self.rom_parent_label.setText(f'Parent: {rom_info.parent}')
            self.rom_video_info_label.setText(
                f'Video Info: {rom_info.hres}x{rom_info.vres}@{rom_info.refresh} - {rom_info.rotate}°')
            self.rom_video_driver_warnings_label.setText(f'Video Driver: {rom_info.video}')
            self.rom_audio_driver_warnings_label.setText(f'Sound Driver: {rom_info.sound}')

        else:
            self.rom_info_container.hide()

    # --------------------- #
    # Save State Page Slots #
    # --------------------- #
    def new_save_state_tree_selection_changed(self, current_item: QTreeWidgetItem) -> None:
        if current_item:
            self.save_state_page_text_before_editing = current_item.text(0)

    def save_state_tree_selection_changed(self, current_item: QTreeWidgetItem) -> None:
        """Used internally for renaming."""
        self.new_save_state_and_inp_tree.clear()
        self.new_save_state_and_inp_tree.setHeaderLabel('It Could Be Anything...Even an Empty List!')
        self.new_save_state_and_inp_tree.blockSignals(True)
        if current_item.parent():
            if current_item.parent().text(0) == 'Save States':
                self.fill_saves(f'{current_item.parent().parent().data(0, Qt.ItemDataRole.UserRole)}', current_item.text(0))
            elif current_item.text(0) == 'Input Files':
                self.fill_inps(current_item.parent().data(0, Qt.ItemDataRole.UserRole))
        self.new_save_state_and_inp_tree.blockSignals(False)

    def ss_or_inp_changed(self, item_that_changed: QTreeWidgetItem) -> None:
        """Rename save state or input file corresponding to leaf item in tree.

        If file name already in use, item has its text reverted and file is not renamed.
        """
        # TODO Should probably be using the NotEmpty custom validator here. Would remove need to track text before editing.
        if not item_that_changed.text(0):
            self.new_save_state_and_inp_tree.blockSignals(True)
            item_that_changed.setText(0, self.save_state_page_text_before_editing)
            self.new_save_state_and_inp_tree.blockSignals(False)
            return

        if self.new_save_state_and_inp_tree.headerItem().text(0) == 'Input Files':
            input_file_name = item_that_changed.text(0)
            mame_dir_item = self.save_state_and_inp_tree.currentItem().parent()
            mame_dir_str = mame_dir_item.text(0)
            mame_dir = Path(mame_dir_str)
            if not mame_dir.is_dir():
                self.remove_invalid_mame_dir(mame_path=mame_dir_str)
                return
            old_input_file_path = mame_dir / 'inp' / f'{self.save_state_page_text_before_editing}.inp'
            new_input_file_path = old_input_file_path.with_stem(input_file_name)

            response = QMessageBox.question(self, 'Rename Input File', 'Are you sure you would like to rename file?')
            if response == QMessageBox.StandardButton.Yes:
                try:
                    old_input_file_path.rename(new_input_file_path)
                except FileExistsError:
                    QMessageBox.critical(self, 'Error', 'Sorry, that name is already in use.')
                    self.new_save_state_and_inp_tree.blockSignals(True)
                    item_that_changed.setText(0, self.save_state_page_text_before_editing)
                    self.new_save_state_and_inp_tree.blockSignals(False)
                    return
                self.save_state_page_text_before_editing = input_file_name
            else:
                self.new_save_state_and_inp_tree.blockSignals(True)
                item_that_changed.setText(0, self.save_state_page_text_before_editing)
                self.new_save_state_and_inp_tree.blockSignals(False)
                return

        if self.new_save_state_and_inp_tree.headerItem().text(0) == 'Save States':
            save_state_name = item_that_changed.text(0)
            rom_item = self.save_state_and_inp_tree.currentItem()
            rom_description = rom_item.text(0)

            rom_name = self.core.descriptions_and_names[rom_description]

            mame_dir_item = self.save_state_and_inp_tree.currentItem().parent().parent()
            mame_dir_str = mame_dir_item.text(0)

            mame_dir = Path(mame_dir_str)
            if not mame_dir.is_dir():
                self.remove_invalid_mame_dir(mame_path=mame_dir_str)
                return
            save_state_dir = mame_dir / 'sta' / rom_name
            old_save_state_path = save_state_dir / (self.save_state_page_text_before_editing + '.sta')
            new_save_state_path = old_save_state_path.with_stem(save_state_name)

            try:
                old_save_state_path.rename(new_save_state_path)
            except FileExistsError:
                QMessageBox.critical(self, 'Error', 'Sorry, that name is already in use.')
                self.new_save_state_and_inp_tree.blockSignals(True)
                item_that_changed.setText(0, self.save_state_page_text_before_editing)
                self.new_save_state_and_inp_tree.blockSignals(False)
                return
            # Have to set this to new save_state_name so multiple renames can take place without reselection.
            self.save_state_page_text_before_editing = save_state_name
        self.core.save_states = self.core.new_get_save_states()
        self.core.input_files = self.core.get_input_files()

    # --------------- #
    # File Menu Slots #
    # --------------- #
    def menu_button_1_clicked(self) -> None:
        """Temporary, easily accessible, trigger for prototype methods."""
        self.remove_invalid_mame_dir(mame_path=r'C:\Users\kazac\Downloads\mame')
        # self.save_state_and_inp_tree.hide()

    def menu_button_2_clicked(self) -> None:
        """Temporary, easily accessible, trigger for prototype methods."""
        self.core.export_sqlite_to_csv('personal_bests', core.get_abs_path('./database_backups/pb.csv'))
        self.core.export_sqlite_to_csv('splits', core.get_abs_path('./database_backups/splits.csv'))
        self.save_state_and_inp_tree.show()

    def add_path_button_clicked(self) -> None:
        """Prompt user for new MAME path and then, clear and refill save state tree.

        Path must be valid filepath, not already in the in-memory representation of the 'paths' database table.
        Path is saved to database and in-memory representation. Slots are disconnected before refilling tree.
        This avoids the incidental signals emitted when adding objects.
        """
        mame_dir = self.get_mame_dir()
        if mame_dir:
            if mame_dir not in self.core.mame_dirs:
                self.core.mame_dirs.append(mame_dir)
            else:
                QMessageBox.critical(self, 'Error', 'Path already exists')
                return
            self.core.save_mame_dirs()
            self.core.save_states = self.core.new_get_save_states()
            self.core.input_files = self.core.get_input_files()
            self.save_state_and_inp_tree.blockSignals(True)
            self.fill_save_state_tree()
            self.save_state_and_inp_tree.blockSignals(False)
            # print(f'New MAME path: {path}')
        # else:
        #     print('Cancel chosen')

    def scan_for_pbs(self) -> None:
        """Scan for new personal bests and insert, or update, them into database.

        An indeterminate progress bar is displayed while scanner runs. It runs on its own thread to avoid blocking.
        The in-memory representation of the database is updated when the scan finishes and GUI reloads with new info.
        """
        self.setEnabled(False)
        self.progress_bar = widgets.ProgressBarWidget(self)
        self.progress_bar.show()
        self.pb_scanner = widgets.PBScannerThread(self.core.mame_dirs)
        self.pb_scanner.finished.connect(self.scan_finished)
        self.pb_scanner.start()


    def scan_finished(self) -> None:
        """Personal Best Scanner cleanup. Hide progress bar and re-enable GUI."""
        self.setEnabled(True)
        self.progress_bar.hide()
        self.core.pb_info = self.core.get_personal_bests()
        self.fill_hiscore_game_list()

    # TODO Look into all the ways you can manipulate geometry.
    def center(self):
        # Get the geometry of the main window including frames
        frame = self.frameGeometry()
        # Get the center point of the available screen geometry
        center_of_screen = self.screen().availableGeometry().center()
        # Move the rectangle's center to the screen's center
        frame.moveCenter(center_of_screen)
        # Move the window's top-left to the rectangle's top-left
        self.move(frame.topLeft())

def main(*, logging=False) -> None:
    """MAMEStates program entry point.

    This function allows me to create DB connects with context manager. If the program ends early, rollback occurs.
    Alternative would be creating db connection with context inside MainWindow _init_, which seems not ideal.
    """
    if logging:
        core.turn_on_logging()
    db = core.get_abs_path('./mame_states.db')
    db_schema = core.get_abs_path('./database_backups/mame_states_schema_v4.sql')
    db_roms_data = core.get_abs_path('./database_backups/roms.sql')
    print(db_schema)
    print(db_roms_data)
    if not db.is_file():
        with sqlite3.connect(db) as connection:
            with open(db_schema, 'r') as schema_file:
                schema = schema_file.read()
                connection.executescript(schema)
                connection.commit()

            with open(db_roms_data, 'r', encoding='utf-8') as roms_data:
                data = roms_data.read()
                pprint.pp(data)
                connection.executescript(data)
                connection.commit()

    with sqlite3.connect(db) as connection:
        mame_states_core = core.MAMEStatesCore(connection)
        # The order the objects are initialized in matters.
        app = QApplication([])

        window = MainWindow(mame_states_core)

        window.show()
        # Can't center before show, window does not know its own dimensions yet.
        window.center()
        app.exec()


if __name__ == '__main__':
    main()
