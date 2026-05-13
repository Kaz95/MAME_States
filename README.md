# MAMEStates

## What is MAMEStates?

MAMEStates is a Windows based, multipurpose launcher for the emulator, MAME. My goal when creating this project was to 
create simple way to manage MAME save state files(Renaming, Deleting, Reordering, ect), hence the name. The scope of the
project has grown and now includes the following features:

### Features:
* Add multiple MAME directories and launch them from a central location.
* Quickly access points of interest(.ini, /sta, /inp, ect.) without navigating the file system.
* Launch Roms:
  * With or without input recording. Input files are named automatically.
  * With input playback.
  * From a given MAME directory.


* View all save state and input files in one location.
* Organize save state and input files. 
  * Rename
  * Delete
  * Rearrange order in which save states appear within MAME.


* Track Hi Scores.
  * Hi scores can be added and saved manually.
  * Hi score may be automatically detected and added if a game is supported by 'hi2txt' and the user launched the rom
    using MAMEStates.
  * A manual Hi score scan can be started using the file menu.


* Track Stage Splits.
    * User may add and save, score based, stage splits for each rom.
    * Stages splits can be rearranged to allow inserting new stage splits into an existing list.
    * MAMEStates automatically calculates and displays the differences between stage scores in its own column.
    * Stage splits(as well as Hi Score info) may be detached for easier viewing.  


* Create and save notes on a rom by rom bases(Basic text, plan to add markdown in the future.)
* Rom Search Bar
  * Works with rom name(short name), as well as rom description(long Name).
  * Provides basic rom information. 
    * Manufacturer
    * Release Date
    * Parent/Clone Status
    * Resolution/Orientation
    * Known Driver Issues


* Export Personal Best and Split data to CSV file.


## Quick Start

MAMEStates in portable and does not require any installation. 

To get started, grab the latest release: [Latest Releases](https://github.com/Kaz95/MAME_States/releases)

Extract all the files in the archive into their own folder. Navigate to the new directory and open the 'gui' folder.
Inside will be the MAMEStates executable and an '_internal' folder which houses project files. Run the executable.
Windows will probably show a warning due to lack of signing, click more info and run anyway.


## Future

My current plans are to focus on cleaning up the codebase and building out the testing suite for a while. I will
fix bugs as I find them, but won't be adding new features for some time. I'm a hobbyist and this is the first project
I have released for others to use. It's been a really fun project so far, and I've learned a ton. I have quite a few 
ideas for more features I'd like to add, so stay on the lookout for updates.


## AI Usage Disclosure
It's good ol' USDA Certified Human Slop. Might be some boilerplate copied in there somewheres 
if you look hard enough though!
