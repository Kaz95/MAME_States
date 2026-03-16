"""MAMEStates GUI

This module contains the graphical user interface for the MAMEStates application.

TODO:
    * Remove try/except blocks where the program should be allowed to fail.
    * Consider sizing policies and size hints
    * Decide on new features to add.
"""
import os
import pprint
import sqlite3
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QTimer, QPoint
from PyQt6.QtGui import QAction, QFont, QColor, QBrush
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget, \
    QHBoxLayout, QWidget, QVBoxLayout, QLabel, QPushButton, QListWidgetItem, \
    QFileDialog, QMessageBox, QMenu, QListWidget, QInputDialog

import core, hi2txt_wrapper, widgets


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

        self.test_button_2_action: QAction = QAction('Test Button 2', self)
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

        self.high_score_page: QWidget = QWidget()
        """Container widget. Corresponding layout is applied. Added to corresponding container tab widget."""

        self.rom_search_page: QWidget = QWidget()
        """Container widget. Corresponding layout is applied. Added to corresponding container tab widget."""

        # ------------------ #
        #   Save State Page  #
        # ------------------ #

        # Widgets
        self.save_state_and_inp_tree: QTreeWidget = QTreeWidget()
        """Main widget of the save state tab"""

        # Layouts
        self.save_state_and_inp_layout: QHBoxLayout = QHBoxLayout()
        """Top level page layout."""

        self.save_state_and_inp_layout.setContentsMargins(0, 0, 0, 0)
        self.save_state_and_inp_page.setLayout(self.save_state_and_inp_layout)
        self.save_state_and_inp_layout.addWidget(self.save_state_and_inp_tree)

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

        self.splits_list: widgets.StageSplitListWidget = widgets.StageSplitListWidget(self.core)
        """Contains stage splits for current PB."""

        self.pb_fields_list: QListWidget = QListWidget()
        """Contains the various fields that make up the current personal best."""

        self.add_split_button: QPushButton = QPushButton('Add Split')
        """Allow user to, manually, add a stage split to current PB."""

        self.delete_split_button: QPushButton = QPushButton('Delete Split')
        """Allow user to, manually, remove a stage split from current PB."""

        # Layouts

        self.high_score_page_layout: QHBoxLayout = QHBoxLayout()
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

        self.personal_best_layout.addWidget(self.pb_fields_list)
        self.info_layout.addLayout(self.personal_best_layout, 1)
        self.info_layout.addStretch()

        self.info_layout.addWidget(self.splits_list, 1)
        self.info_layout.addStretch()

        self.info_layout.addLayout(self.splits_tree_button_container)

        self.high_score_page_layout.addLayout(self.game_list_container)
        self.high_score_page_layout.addLayout(self.info_layout)
        self.high_score_page.setLayout(self.high_score_page_layout)
        self.high_score_page.setFont(self.big_font)

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
        self.tabs.addTab(self.save_state_and_inp_page, 'Save States')
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
        self.test_button_1_action.triggered.connect(self.menu_button_1_clicked)
        self.test_button_2_action.triggered.connect(self.menu_button_2_clicked)
        self.add_mame_directory_action.triggered.connect(self.add_path_button_clicked)
        self.update_pb_action.triggered.connect(self.scan_for_pbs)

        self.file_menu.addAction(self.test_button_1_action)
        self.file_menu.addAction(self.test_button_2_action)
        self.file_menu.addAction(self.add_mame_directory_action)
        self.file_menu.addAction(self.update_pb_action)

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
        self.save_state_and_inp_tree.itemChanged.connect(self.save_state_tree_leaf_item_changed)

    def setup_hiscore_panel(self) -> None:
        """High Score Panel widget customization"""
        self.notes_window.hide()
        # Fill Game List
        self.fill_hiscore_game_list()

        self.games_with_pb_tree.setHeaderLabels(['Games'])
        self.games_with_pb_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.games_with_pb_tree.customContextMenuRequested.connect(self.show_rom_item_context)
        self.games_with_pb_tree.itemSelectionChanged.connect(self.high_score_tree_selection_changed)

        self.hiscore_add_game_button.clicked.connect(self.hiscore_add_game_clicked)
        self.hiscore_delete_game_button.clicked.connect(self.delete_game)

        self.game_list_button_container.addWidget(self.hiscore_add_game_button)
        self.game_list_button_container.addWidget(self.hiscore_delete_game_button)

        self.game_list_container.addWidget(self.games_with_pb_tree)
        self.game_list_container.addLayout(self.game_list_button_container)

        # FIXME Can't focus right away. Causes incorrect size hint. Look into it.
        # first_item = self.high_score_game_tree.topLevelItem(0)
        # self.high_score_game_tree.setCurrentItem(first_item)

    def setup_pb_panel(self) -> None:
        """Personal Best Panel widget customization."""
        self.pb_fields_list.setFont(self.small_font)
        self.pb_fields_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pb_fields_list.customContextMenuRequested.connect(self.show_pb_fields_context)

    def setup_split_panel(self) -> None:
        """Split Panel widget customization."""
        self.splits_tree_button_container.addWidget(self.add_split_button)
        self.splits_tree_button_container.addWidget(self.delete_split_button)

        self.splits_list.itemDoubleClicked.connect(self.split_double_clicked)
        self.splits_list.currentItemChanged.connect(self.split_current_item_changed)

        self.add_split_button.clicked.connect(self.new_split)
        self.delete_split_button.clicked.connect(self.delete_split)

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
        self.create_pb_field_item('High Score', hiscore)
        if other_fields:
            for field_name in other_fields:
                self.create_pb_field_item(field_name, other_fields[field_name])

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
    def create_pb_field_item(self, field_name: str, field_value: str | int) -> QListWidgetItem:
        """Create a new custom widget item and assign it to a list widget item."""
        pb_field = widgets.PBField(field_name, field_value)
        if field_name == 'High Score':
            self.temp_fields['high score'] = pb_field
        else:
            self.temp_fields[f'{field_name}'] = pb_field

        pb_field.field_value.editor.editingFinished.connect(self.update_high_score_pb)
        list_item = QListWidgetItem(self.pb_fields_list)
        self.pb_fields_list.setItemWidget(list_item, pb_field)
        list_item.setSizeHint(pb_field.sizeHint())
        return list_item


    def create_split_item(self, split: core.StageSplit, rom_description: str) -> QListWidgetItem:
        """Create a new custom widget item and assign it to a list widget item."""
        split_item = widgets.StageSplitItem(split, rom_description, self.splits_list, self.core)
        list_item = QListWidgetItem(self.splits_list)
        self.splits_list.setItemWidget(list_item, split_item)
        list_item.setSizeHint(split_item.sizeHint())
        return list_item

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
        """Clear and refill High Score Game Tree, based on personal best info."""
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
            mame_dir_item = QTreeWidgetItem(self.save_state_and_inp_tree, [str(mame_dir.path)])
            mame_dir_item.setFont(0, self.big_font)
            save_states_container_item = QTreeWidgetItem(mame_dir_item, ['Save States'])
            save_states_container_item.setFont(0, self.big_font)
            input_files = self.core.input_files.get(str(mame_dir.path))
            if input_files:
                input_files_container_item = QTreeWidgetItem(mame_dir_item, ['Input Files'])
                input_files_container_item.setFont(0, self.big_font)
                for file in input_files:
                    item = QTreeWidgetItem(input_files_container_item, [file])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    item.setFont(0, self.small_font)

            # Add game items.
            for rom_name in self.core.save_states[str(mame_dir.path)]:
                game_description = self.core.rom_description_from_name(rom_name)
                game_item = QTreeWidgetItem(save_states_container_item, [game_description])
                game_item.setFont(0, self.big_font)

                # Add savestate items.
                for save_state in self.core.save_states[str(mame_dir.path)][rom_name]:
                    save_state_item = QTreeWidgetItem(game_item, [save_state])
                    save_state_item.setFlags(save_state_item.flags() | Qt.ItemFlag.ItemIsEditable)
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

    def high_score_tree_selection_changed(self) -> None:
        """Clear and refill 'splits list' and 'pb panel' based on currently selected item.

        Split diffs are calculated and displayed.
        """
        self.pb_fields_list.clear()
        self.splits_list.clear()
        selected = self.games_with_pb_tree.selectedItems()
        if selected:
            rom_description = selected[0].text(0)
            pb = self.core.pb_info[rom_description]

            self.update_pb_panel(pb.hiscore, pb.other_fields)
            for split in pb.splits:
                self.create_split_item(split, rom_description)

            self.splits_list.add_diffs(pb.splits)

    def split_double_clicked(self, item: QListWidgetItem) -> None:
        """Show split item editors. Hide labels."""
        item_widget = self.splits_list.itemWidget(item)
        item_widget.toggle_editors()

    def split_current_item_changed(self, current_selection: QListWidgetItem,
                                   previous_selection: QListWidgetItem) -> None:
        """Show split item labels. Hide editors."""
        if previous_selection:
            item_widget = self.splits_list.itemWidget(previous_selection)
            if item_widget:
                item_widget.toggle_labels()

    def update_high_score_pb(self) -> None:
        """Update in-memory representation and saves to database"""
        selected = self.games_with_pb_tree.selectedItems()
        if selected:
            game_item = selected[0]
            rom_description = game_item.text(0)
            self.core.pb_info[rom_description].hiscore = self.temp_fields['high score'].field_value.editor.text()
            for field_name in self.temp_fields:
                if field_name == 'high score':
                    continue
                self.core.pb_info[rom_description].other_fields[field_name] = self.temp_fields[field_name].field_value.editor.text()
            self.core.save_pb_to_database()

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
        """Create new High Score Game Tree item, based on user selection. Game is added to pb info and database.

        Duplicate games are disallowed. Popup closes upon valid selection. New game is focused.
        """
        selected = self.rom_search_tree.selectedItems()
        if selected:
            item = selected[0]
            rom_description = item.text(0)
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
        selected = self.games_with_pb_tree.selectedItems()
        if selected:
            game_item = selected[0]
            previous_item = self.games_with_pb_tree.itemAbove(game_item)
            next_item = self.games_with_pb_tree.itemBelow(game_item)

            # Move selection before deleting.
            if previous_item:
                self.games_with_pb_tree.setCurrentItem(previous_item)
            elif next_item:
                self.games_with_pb_tree.setCurrentItem(next_item)
            else:
                self.games_with_pb_tree.clearSelection()

            rom_description = game_item.text(0)
            # Delete from in-memory database representation.
            del self.core.pb_info[rom_description]
            # Delete from database.
            self.core.delete_personal_best(rom_description)
            self.core.delete_splits(rom_description)

            # Finally, remove item from Hiscore Game Tree.
            game_item_index = self.games_with_pb_tree.indexFromItem(game_item)
            game_row = game_item_index.row()
            self.games_with_pb_tree.takeTopLevelItem(game_row)

    def delete_split(self) -> None:
        """Delete a split in the split list. Also deleted from in-memory database representation and database.

        Row is used instead of .selectedItems() so that it can be used for deleting from in-memory data structure.
        """
        selected = self.games_with_pb_tree.selectedItems()
        if selected:
            rom_description = selected[0].text(0)
            # Row becomes -1 when nothing selected...I think.
            row = self.splits_list.currentRow()
            if row != -1:
                self.splits_list.takeItem(row)
                splits = self.core.pb_info[rom_description].splits
                split_name = splits[row].label
                del splits[row]
                self.core.delete_split(rom_description, split_name)
                self.core.save_pb_to_database()

    def new_split(self) -> None:
        """Create a new, blank split item. Add it to the list widget and the in memory database representation.

        The new split item has its editor toggled on, and is set as the focus.
        """
        selected = self.games_with_pb_tree.selectedItems()
        if selected:
            game_item = selected[0]
            rom_description = game_item.text(0)
            rom_id = self.core.id_from_description(rom_description)
            game_splits = self.core.pb_info[rom_description].splits
            new_split = core.StageSplit('', 0, rom_id)
            game_splits.append(new_split)
            new_split_item = self.create_split_item(new_split, rom_description)
            self.splits_list.setCurrentItem(new_split_item)
            self.split_double_clicked(new_split_item)

    def open_notes(self, some_list: QTreeWidget) -> None:
        """Open notes widget.

        Open the notes widget and change the title to reflect the currently selected item.
        If [rom_name].txt exists, copy data into the notes widget. Otherwise, create [rom_name].txt. Focus notes widget.
        A reference is held to the notes widget to avoid it being automatically deleted. Cannot open multiple notes.
        """
        rom_description = some_list.selectedItems()[0].text(0)
        rom_name = self.core.descriptions_and_names[rom_description]
        if self.notes_window.isHidden():
            self.notes_window.show()

        notes_file = Path('../notes') / (rom_name + '.txt')
        notes_file = core.get_abs_path(notes_file)

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
            subprocess.Popen(mame_exe, cwd=rf'{mame_dir}')
        else:
            self.remove_invalid_mame_dir(mame_path=mame_path)
            print(f'File {mame_exe} not found')

    def delete_pb_field(self, item: QListWidgetItem, rom_description: str) -> None:
        """Attempt to delete a personal best field from the pb fields list.

        Attempting to delete 'High Score' field fails to prevent PB with no fields.
        """
        row = self.pb_fields_list.row(item)
        pb_field = self.pb_fields_list.itemWidget(item)
        field_name = pb_field.field_name.text()
        field_name = field_name.strip(':')
        if field_name == 'High Score':
            QMessageBox.critical(self, 'Error', 'Field required.')
            return

        self.pb_fields_list.takeItem(row)
        del self.core.pb_info[rom_description].other_fields[field_name]
        self.temp_fields.pop(field_name)
        del item
        self.core.save_pb_to_database()

    def add_pb_field(self, rom_description: str) -> None:
        """Create a new PB field entry in the pb fields list.

        User input is used for field name, and repeated field names are disallowed.
        """
        text, ok = QInputDialog.getText(self, 'New Personal Best Field.', 'Please enter the name of the new field:')
        if text == 'High Score':
            QMessageBox.critical(self, 'Error', 'Name already in use.')
            return
        if self.core.pb_info[rom_description].other_fields:
            if text in self.core.pb_info[rom_description].other_fields:
                QMessageBox.critical(self, 'Error', 'Name already in use.')
                return
        if ok:
            self.create_pb_field_item(f'{text}', 0)
            self.core.pb_info[rom_description].other_fields[text] = 0
            self.core.save_pb_to_database()

    def show_pb_fields_context(self, position: QPoint) -> None:
        """Create and show context menu in PB fields list. Context changes depending on if item is clicked or not."""
        pb_field_list_item = self.pb_fields_list.itemAt(position)
        rom_items = self.games_with_pb_tree.selectedItems()
        if rom_items:
            selected_rom = rom_items[0]
            rom_description = selected_rom.text(0)

        menu = QMenu()

        if pb_field_list_item:
            delete_pb_field = QAction('Delete PB Field')
            delete_pb_field.triggered.connect(lambda: self.delete_pb_field(pb_field_list_item, rom_description))
            menu.addAction(delete_pb_field)

        add_pb_field = QAction('Add New PB Field')
        add_pb_field.triggered.connect(lambda: self.add_pb_field(rom_description))
        menu.addAction(add_pb_field)
        menu.exec(self.pb_fields_list.viewport().mapToGlobal(position))


    def remove_invalid_mame_dir(self, *, mame_path: str | None=None, path_item: QTreeWidgetItem | None=None) -> None:
        """Remove MAME directory and all related info(saves, inps, ect) from GUI, in-memory datastructures, and DB

        Use path_item if called from context menu where item is available, then derive mame_path.
        Use mame_path if called from anywhere else, then derive item from path.
        """
        if path_item:
            mame_path = path_item.text(0)
            root = self.save_state_and_inp_tree.invisibleRootItem()
            selected_dir = self.save_state_and_inp_tree.selectedItems()[0]
            root.removeChild(selected_dir)

        elif mame_path:
            for _ in range(self.save_state_and_inp_tree.topLevelItemCount()):
                if self.save_state_and_inp_tree.topLevelItem(_).text(0) == mame_path:
                    self.save_state_and_inp_tree.takeTopLevelItem(_)
                    break

        self.core.new_remove_invalid_mame_dir(mame_path)
        QMessageBox.critical(self, 'Error', 'Invalid MAME Directory.\nDirectory has been removed. Please update it.')


    def open_ini_actioned_clicked(self) -> None:
        """Attempt to open the .ini file for the selected MAME directory.

        If a .ini file does not exist, user is given the choice to create a new one.
        """
        mame_dir_item = self.save_state_and_inp_tree.selectedItems()[0]
        path_str = mame_dir_item.text(0)
        mame_path = Path(path_str)
        if Path(path_str).is_dir():
            mame_ini_file = mame_path / 'mame.ini'
            if mame_ini_file.is_file():
                os.startfile(mame_ini_file)
            else:
                response = QMessageBox.question(self, 'Directory Not Found', f'Could Not Find File: {mame_ini_file}\nWould you like to create a new ini file?')
                if response == QMessageBox.StandardButton.Yes:
                    subprocess.run([core.get_abs_path(mame_path / 'mame.exe'), '-cc'], cwd=core.get_abs_path(mame_path))
        else:
            self.remove_invalid_mame_dir(mame_path=path_str)

    def open_mame_dir_in_explorer(self, mame_dir_item: QTreeWidgetItem) -> None:
        """Attempt to open a given MAME directory in Windows explorer.

        If the path is found to be invalid, it is removed from the app completely.
        """
        mame_dir = Path(mame_dir_item.text(0))
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

            launch.triggered.connect(lambda: self.run_mame(tree_item.text(0)))
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
            if tree_item.childCount() > 0:  # Lazy way to ensure rom items don't spawn menu.
                return
            delete = QAction('Delete')
            delete.triggered.connect(lambda: self.delete_leaf_item(tree_item))
            menu.addAction(delete)

            if tree_item.parent().text(0) == 'Input Files':
                input_file_name = tree_item.text(0)
                rom_name = input_file_name.split('_')[0]  # inp files created by program will have rom name at start.

                sub_menu = QMenu('Playback with...')
                for mame_dir in self.core.mame_dirs:
                    run = QAction(str(mame_dir.path), self)
                    run.triggered.connect(
                        lambda: self.run_rom(rom_name, play_back_input=True, input_file_name=input_file_name))
                    sub_menu.addAction(run)
                    menu.addMenu(sub_menu)
        menu.exec(self.save_state_and_inp_tree.viewport().mapToGlobal(position))

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
            input_file.unlink()

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
            save_state_file.unlink()

        direct_parent.removeChild(leaf_item)

    def open_save_or_inp_in_explorer(self, category_item: QTreeWidgetItem) -> None:
        """Opens a MAME directory's 'inp', and 'sta' folders in Windows explorer."""
        mame_dir = Path(category_item.parent().text(0))
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
        menu.exec(self.sender().viewport().mapToGlobal(position))

    def open_rom_for_inp_search(self) -> str:
        """Pop out the 'rom search' tab for use as a search dialog. Rom info is hidden until dialog closes."""
        self.tabs.removeTab(2)
        self.rom_info_container.hide()
        dialog = widgets.RomSearchDialog(widgets.RomSearchWindow(self.rom_search_page, self.tabs), self.rom_search_tree,
                                      parent=self)
        dialog.exec()
        self.rom_info_container.show()
        self.tabs.addTab(dialog.rom_search_popup, 'Rom Search')
        return dialog.rom_description_for_inp

    def run_rom(self, rom_name: str, record_input=False, play_back_input=False, input_file_name=None) -> None:
        """Attempt to run a rom, with a given MAME path.

        If the rom is hi2txt compatible, a snapshot is taken of current high score tables.
        This function does not currently check for a roms existence before trying to run it. MAME errors used instead.
        MAME is run in by spawning a subprocess. The subprocess is spawned in a separate thread to avoid blocking GUI.
        """
        # The action that triggered this function call. Its label has the correct MAME path.
        action = self.sender()
        mame_dir = action.text()

        mame_exe = Path(mame_dir) / 'mame.exe'
        if not mame_exe.is_file():
            self.remove_invalid_mame_dir(mame_path=mame_dir)
            return

        hiscore_file = Path(mame_dir) / 'hiscore' / (rom_name + '.hi')
        hi2txt_compatible = hi2txt_wrapper.has_xml(rom_name)
        if hi2txt_compatible:
            hi2txt_results = subprocess.run(
                [core.get_abs_path(r'../hi2txt/hi2txt.exe'), '-r', f'{hiscore_file}'],
                cwd=core.get_abs_path(r'../hi2txt'), capture_output=True, text=True,
                check=True, encoding='utf-8')
            self.pre_hs_table = hi2txt_results.stdout

        if rom_name not in list(self.core.descriptions_and_names.values()):
            rom_description = self.open_rom_for_inp_search()
            if rom_description:
                rom_name = self.core.descriptions_and_names[rom_description]
            else:
                QMessageBox.critical(self, 'Error', 'Input File cannot be played back without a valid rom.')
                return
        self.mame_thread = widgets.MAMEThread(mame_exe, rom_name, Path(mame_dir), record_input=record_input,
                                              playback_input=play_back_input, input_file_name=input_file_name)
        self.mame_thread.mame_exited.connect(self.rom_done)
        self.mame_thread.start()

        print(f'Running {rom_name}, from {action.text()}')

    def rom_done(self, results: dict) -> None:
        """Perform actions after rom finishes running.

        If rom is hi2txt compatible, a new snapshot is taken of roms hiscore tables. Tables are compared to find PB.
        If new PB is found, user is prompted to add or discard new PB.
        """

        hiscore_file = Path(self.mame_thread.mame_dir) / 'hiscore' / (self.mame_thread.rom_name + '.hi')
        if results['return_code'] != 0:
            QMessageBox.critical(self, 'Rom Not Found', f'{results['err']}')
        else:
            if not results['output']:
                results['output'] = f'{self.mame_thread.rom_name} has close successfully.'
            QMessageBox.information(self, 'Rom Closed', f'{results['output']}')
            if self.pre_hs_table:
                hi2txt_results = subprocess.run(
                    [core.get_abs_path(r'../hi2txt/hi2txt.exe'), '-r', f'{hiscore_file}'],
                    cwd=core.get_abs_path(r'../hi2txt'), capture_output=True,
                    text=True,
                    check=True, encoding='utf-8')

                post_hs_table = hi2txt_results.stdout
                new_pb = hi2txt_wrapper.get_new_pb(self.pre_hs_table, post_hs_table)

                if new_pb:
                    response = QMessageBox.question(self, 'New PB Detected!',
                                                    f'A new personal best has been detected\n{new_pb['col']}\n{new_pb['row']}\nWould you like to add new PB?')
                    if response == QMessageBox.StandardButton.Yes:
                        new_pb = hi2txt_wrapper.prepare_pb_for_db(new_pb, self.mame_thread.rom_name)
                        hi2txt_wrapper.save_pbs(new_pb, self.core.connection, self.core.cursor)
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

        Info Panel is cleared before refilling to account for no selected item.
        TODO
         I suppose I could clear only if not selected.
        """
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
            rom_info = self.core.rom_info[game_description]
            self.rom_description_label.setText(f'Game: {game_description}')
            self.rom_name_label.setText(f'Rom Name: {rom_info.name}')
            self.rom_manufacturer_label.setText(f'Manufacturer: {rom_info.manufacturer}')
            self.rom_release_year_label.setText(f'Year: {rom_info.year}')
            self.rom_parent_label.setText(f'Parent: {rom_info.parent}')
            self.rom_video_info_label.setText(
                f'Video Info: {rom_info.hres}x{rom_info.vres}@{rom_info.refresh} - {rom_info.rotate}°')
            self.rom_video_driver_warnings_label.setText(f'Video Driver: {rom_info.video}')
            self.rom_audio_driver_warnings_label.setText(f'Sound Driver: {rom_info.sound}')

    # --------------------- #
    # Save State Page Slots #
    # --------------------- #
    def save_state_tree_selection_changed(self, current_item: QTreeWidgetItem) -> None:
        """Used internally for renaming."""
        self.save_state_page_text_before_editing = current_item.text(0)

    def save_state_tree_leaf_item_changed(self, leaf_item: QTreeWidgetItem) -> None:
        """Rename save state or input file corresponding to leaf item in tree.

        If file name already in use, item has its text reverted and file is not renamed.
        """
        # FIXME Pretty sure I can avoid toggling the signal by using a different signal. TextEdited or something...
        if not leaf_item.text(0):
            self.save_state_and_inp_tree.blockSignals(True)
            leaf_item.setText(0, self.save_state_page_text_before_editing)
            self.save_state_and_inp_tree.blockSignals(False)
            return

        if leaf_item.childCount() == 0 and leaf_item.parent().text(0) == 'Input Files':
            input_file_name = leaf_item.text(0)
            mame_dir_item = leaf_item.parent().parent()
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
                    self.save_state_and_inp_tree.blockSignals(True)
                    leaf_item.setText(0, self.save_state_page_text_before_editing)
                    self.save_state_and_inp_tree.blockSignals(False)
                    return
            else:
                self.save_state_and_inp_tree.blockSignals(True)
                leaf_item.setText(0, self.save_state_page_text_before_editing)
                self.save_state_and_inp_tree.blockSignals(False)
                return

        if leaf_item.childCount() == 0 and leaf_item.parent().parent().text(0) == 'Save States':
            save_state_name = leaf_item.text(0)
            rom_item = leaf_item.parent()
            rom_description = rom_item.text(0)

            rom_name = self.core.descriptions_and_names[rom_description]

            mame_dir_item = rom_item.parent().parent()
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
                self.save_state_and_inp_tree.blockSignals(True)
                leaf_item.setText(0, self.save_state_page_text_before_editing)
                self.save_state_and_inp_tree.blockSignals(False)
                return
            # Have to set this to new save_state_name so multiple renames can take place without reselection.
            self.save_state_page_text_before_editing = save_state_name

    # --------------- #
    # File Menu Slots #
    # --------------- #
    def menu_button_1_clicked(self) -> None:
        """Temporary, easily accessible, trigger for prototype methods."""
        self.remove_invalid_mame_dir(mame_path=r'C:\Users\kazac\Downloads\mame')
        # self.save_state_and_inp_tree.hide()

    def menu_button_2_clicked(self) -> None:
        """Temporary, easily accessible, trigger for prototype methods."""
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
            self.core.save_states = self.core.get_save_states()
            self.core.input_files = self.core.get_input_files()
            # self.all_save_states = get_all_roms_with_saves(self.mame_dirs)
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
        pb_scanner = widgets.PBScannerThread(self.core.mame_dirs)
        pb_scanner.finished.connect(self.scan_finished)
        pb_scanner.start()
        self.core.pb_info = self.core.get_personal_bests()
        self.fill_hiscore_game_list()

    def scan_finished(self) -> None:
        """Personal Best Scanner cleanup. Hide progress bar and re-enable GUI."""
        self.setEnabled(True)
        self.progress_bar.hide()


def main() -> None:
    """MAMEStates program entry point.

    This function allows me to create DB connects with context manager. If the program ends early, rollback occurs.
    Alternative would be creating db connection with context inside MainWindow _init_, which seems not ideal.
    """
    db = core.get_abs_path('./mame_states.db')
    db_schema = core.get_abs_path('./database_backups/mame_states_schema_v3.sql')
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

        app.exec()


if __name__ == '__main__':
    main()
