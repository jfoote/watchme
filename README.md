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
  
To see if it is working, try this (assuming you have cygwin, git shell, or tail otherwise installed):

  > tail -f data/<YYYY-MM-DD>\ windows.csv
  
  ... as you click around you should see raw window activity info logged to your shell


Dependencies
------------
Requires pywin32: http://sourceforge.net/projects/pywin32/


Background
----------
This is a toy application that I occassionally work on for fun, largely as a pastime when I end up having to watch a chick flick or reality TV :). Please feel free to hack it up.

Design notes
------------
Numbers
- - - -
This script logs activity to CSV files. I've been running it on a machine that gets moderate to heavy use every day for the past 308 days (as of 9/8/2013), and the CSV files take up less than 100MB of disk space. From the outset I figured the current implementation of window logging would take up a little over 100MB per year, and based on data so far I think that is accurate.

Polling
- - - -
This script uses polling to grab window activity. I usually try to avoid polling in favor of event-driven design, but after reading a bit on methods for logging window activity (and implementing some tests) I went with polling for these reasons: 1) I had to build a DLL to support handling win API callbacks, which complicated the build. 2) The win 32 API calls that I was playing with didn't cover all of the events I needed -- certain events, like minimizing a window, didn't trigger callbacks. 3) According to a 2012 (or was it 2011?) blog post the team from "time cockpit", who do this for a living, use polling too, so at a minimum it probably will be usable (even if it is not the best solution).


TODOs
-----
- [x] Daemonize & survive Windows sleeping (works with python.exe, but not pythonw.exe)
- [x] Add idle time logging
- [x] Gather licenses for included open source code
- [x] Add license to text to readme and warn about privacy implications
- [x] Clean up and comment code
- [ ] Add unit tests
- [ ] Add install/egg
- [ ] Beef up readme to include example and internals info
- [x] Make icon
- [x] Publish to github
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