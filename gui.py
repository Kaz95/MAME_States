import os.path
import pprint

from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QFileDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from logic.main import get_roms_with_saves, get_save_names, get_real_name, build_rom_db, rename, create_rom_list
from logic.main import change_mame_path


# TODO Look into adding type notes or hints or w.e
# TODO Account for romlist.txt existing, but not yet having mame path. Just incase.
# TODO What happens if no directory is chosen?
# TODO Remove print statements
# TODO Sort some list at some point to ensure alphabetical. Maybe use treewidget functionality.
# TODO Comment/Code Review/Refactor
# TODO Find more shit TODO

# TODO Comment
# Subclass so I can alter event handling behavior
class TreeWidget(QTreeWidget):
    def __init__(self, mame_folder, description_db, rom_db):
        super().__init__()

        # init attributes
        self.mame_folder = mame_folder
        self.description_db = description_db
        self.rom_db = rom_db

        # TODO Figure out if this can be replaced with method
        #  Fill out data structures for later use.
        roms_with_saves = get_roms_with_saves(self.mame_folder)

        for rom in roms_with_saves:
            real_name = get_real_name(self.rom_db, rom)
            self.description_db[real_name] = rom

    # Override Key press event for purposes of custom behavior
    def keyPressEvent(self, event):
        # Capturing both return and enter is important for compatibility
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            selected_items = self.selectedItems()
            if selected_items:
                for item in selected_items:
                    if self.isPersistentEditorOpen(item):
                        rom_item = item.parent()
                        rom_name = self.description_db[rom_item.text(0)]
                        old_text = item.text(0)
                        self.closePersistentEditor(item)
                        rename(self.mame_folder, rom_name, old_text, item.text(0))
            # TODO Figure out if this is needed needed.
            else:
                print('Enter pressed, but no items selected')

            # Mark event as handled if the given keys were pressed.
            # Only do this if you want to override existing behavior of a given keybind.
            event.accept()
        # Pass to normal event handler if the given keys were not pressed.
        else:
            super().keyPressEvent(event)


# TODO Comment
# TODO Clean up init
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        if os.path.isfile('logic/romlist.txt'):
            with open('logic/romlist.txt', 'r') as romlist:
                first_line = romlist.readline()
                self.mame_folder = first_line.strip()
        else:
            self.mame_folder = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                                options=QFileDialog.Option.ShowDirsOnly)
            create_rom_list(self.mame_folder)
            change_mame_path(self.mame_folder)

        self.text_before_editing = None

        # TODO Figure this out
        # Setup class variables to be used later. They *may* need to be accessed by other methods.
        # If they are not needed by other methods, I suppose they don't need to be class var.

        # Previous selected item in TreeWidget
        self.prev = None

        # {'real_name': 'rom_name'}
        self.description_db = {}

        # TODO Do I really need two dictionaries that mirror each other?
        # {'rom_name':'real_name'}
        self.rom_db = build_rom_db('logic/romlist.txt')

        # List of actual game names, rather than rom name.
        self.real_names = []

        # List that hold references to all items in tree. Needed to create sub items.
        # Could assign each item its own var, but with no way of knowing how many this seems best.
        self.game_items = []

        self.saves = None

        self.fill_data_structures()

        # Widget customization
        self.setWindowTitle('MAME States')
        self.tree_widget = TreeWidget(self.mame_folder, self.description_db, self.rom_db)
        self.tree_widget.setHeaderLabels(['Games'])

        # Signals
        self.tree_widget.itemClicked.connect(self.item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.item_double_clicked)
        self.tree_widget.currentItemChanged.connect(self.selection_changed)

        self.add_top_level_items()

        # TODO Figure out why this is needed. Showing the MainWindow(parent) should make this visible?
        # I guess this makes the widget visible without using .show()
        self.setCentralWidget(self.tree_widget)

        self.add_sub_items()

        # Add file menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('&File')

        self.button_action = QAction('Add MAME Path', self)
        self.button_action.triggered.connect(self.menu_button_clicked)

        self.file_menu.addAction(self.button_action)

    # Slots
    def update_treewidget(self):
        self.tree_widget.rom_db = self.rom_db
        self.tree_widget.description_db = self.description_db
        self.tree_widget.mame_folder = self.mame_folder

    def add_sub_items(self):
        # Adds save states as sub items to a given games main item.
        pprint.pprint(self.game_items)
        for game in self.game_items:
            if game.text(0) in self.description_db:
                rom_name = self.description_db[game.text(0)]
                if rom_name in self.saves:
                    for state in self.saves[rom_name]:
                        QTreeWidgetItem(game, [state])

    def add_top_level_items(self):
        # Creates top level list items. Also captures reference to every item created in a list.
        # These references will be used to create sub items.
        for game in self.real_names:
            game_item = QTreeWidgetItem(self.tree_widget, [game])
            self.game_items.append(game_item)

    def fill_data_structures(self):
        # reset data structs
        self.rom_db = build_rom_db('logic/romlist.txt')
        self.real_names = []
        self.description_db = {}
        self.game_items = []
        #  Fill out data structures for later use.
        roms_with_saves = get_roms_with_saves(self.mame_folder)

        for rom in roms_with_saves:
            real_name = get_real_name(self.rom_db, rom)
            self.real_names.append(real_name)
            self.description_db[real_name] = rom

        self.saves = get_save_names(roms_with_saves, self.mame_folder)

    def menu_button_clicked(self):
        mame_path = QFileDialog.getExistingDirectory(self, 'Choose a Directory',
                                                     options=QFileDialog.Option.ShowDirsOnly)
        self.mame_folder = mame_path
        self.tree_widget.clear()
        create_rom_list(self.mame_folder)
        change_mame_path(mame_path)
        self.fill_data_structures()
        self.update_treewidget()
        self.add_top_level_items()
        self.add_sub_items()

        print('clicked', mame_path)

    # def item_clicked(self, item):
    #     if item.parent() is None:
    #         pass

    def item_double_clicked(self, item, col):
        if item.parent() is not None:
            self.text_before_editing = item.text(0)
            self.tree_widget.openPersistentEditor(item, col)

        # close all expanded child items except for the parent of the current selected item.
        for item in self.game_items:
            if item.isExpanded() and not item.isSelected() and self.tree_widget.selectedItems()[0].parent() != item:
                self.tree_widget.collapseItem(item)

    # On program load, prev is always None, and cur is first item.
    # TODO Clean this up and remove text prompts.
    def selection_changed(self, cur, prev):
        if prev and cur:
            if prev.parent():
                prev.setText(0, self.text_before_editing)
            self.tree_widget.closePersistentEditor(prev)


if __name__ == '__main__':
    # The order the objects are initialized in matters.
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
