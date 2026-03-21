"""Core Logic Package

TODO:
    * Programmatically change focus where appropriate. Raise and focus program where appropriate.
    * Add GUI 'updates' where appropriate(eg., new item added, personal bests updated)
    * Testing.
    * Set default MAME directory of some kind. Possibly, base it on current monitor to avoid GroovyMAME jank.
        * DoubleClick rom to launch in default MAME.
    * Disallow stage splits with blank name. Also, disallow duplicate names.
    * Add program default location.
    * Derive roms dir from MAME ini, instead of assuming it is called roms.
    * Remove QMessageBpx when dir deleted via file menu.
    * Decide how terminal output will be displayed on front-end.
        * Implement QProcesses to replace Popen usage.
    * Consider sizing policies and size hints
    * Decide on new features to add.
"""