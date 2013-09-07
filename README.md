watchme
=======
Window usage data collector and analyzer script for MS Windows. AKA an "active window logger" or "active window tracker"

Written by Jonathan Foote (jmfoote@andrew.cmu.edu)


Description
-----------
watchme.py is a Python script for MS Windows that polls to collect information about the active window. The script can be controlled via a the task tray interface it adds the system tray after it is launched. In addition to tracking window information, it also includes some basic data analysis capabilities.


WARNING!
--------
This script will collect data about what you do on your system and store it in plaintext to your local filesystem. USE THIS SCRIPT AT YOUR OWN RISK -- there is no warranty, and I take NO responsibility for what you do with it, or anything that happens to you as a result of using it.


Usage
-----
Run watchme.py via python from the commandline:

  python watchme.py

Or, to "install" it, create a batch script to run it with pythonw and add a shortcut to the batch script to your Startup folder.

  pythonw watchme.py


Dependencies
------------
Requires pywin32: http://sourceforge.net/projects/pywin32/


Background
----------
This is a toy application that I occassionally work on for fun, largely as a pastime when I end up having to watch a chick flick or reality TV :). Please feel free to hack it up.


TODOs
-----
- [x] Daemonize & survive Windows sleeping (works with python.exe, but not pythonw.exe)
- [x] Add idle time logging
- [x] Gather licenses for included open source code
- [x] Add license to text to readme and warn about privacy implications
- [ ] Clean up and comment code
- [ ] Add install/egg
- [ ] Beef up readme to include example and internals info
- [x] Make icon
- [ ] Publish to github
- [ ] Add support for exe name processing to analyzer
- [ ] Add support for idle_time/window_time processing to analyzer
- [ ] Add additional analysis: histrograms, search by exe name, etc.
- [ ] Implement lock/some sort of singleton to prevent running proc twice
- [ ] Add ML :)
- [ ] Add support for aggregating data across machines (for VM use)
- [ ] Add support for other desktop managers
- [ ] Become a rich philanthropist, etc.


Licenses
--------
See LICENSE.txt for details on the licenses of this project and included open source code