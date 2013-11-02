'''
watchme.py: MS Windows usage data collector & analyzer. 

See README.md for a description, usage, etc.

Written by Jonathan Foote (jmfoote@andrew.cmu.edu).
Original code is released under the MIT license; see LICENSE.md for details.

Design notes:
__main__ creates a Watcher

Watcher instantiates a Logger and an Analyzer and connects them to a system 
  tray widget (which it also creates).

Logger polls every second, collecting window info and writing it to CSV files
  on disk, which are named according to the date. Logger starts when this
  script is launched.

Analyzer aggregates data from all of the CSV files and writes them to a JS
  file, then launches a web page (with the default browser) that lets the
  user analyze the data. Analyzer is invoked via the system tray widget
  right click menu.
'''

from ctypes import windll, Structure, c_ulong, byref
import ctypes
import threading
import time
import os
import warnings
import datetime
import sys
import subprocess
import re
from collections import namedtuple
import csv
import logging

from systrayicon import SysTrayIcon


def pointer_size():
    '''
    Gets pointer size for the current platform in bytes.
    '''
    import platform
    bits = platform.architecture()[0]
    return int(re.match("^([\d]*)", bits).groups()[0]) / 8


class LastInputInfo(Structure):
    '''
    Instances of this class are used as reference (return) parameters for calls
    to GetLastInputInfo.
    See: http://msdn.microsoft.com/en-us/library/ms646272(v=vs.85).aspx
    '''
    _fields_ = [("cbSize", c_ulong),
                ("dwTime", c_ulong)] # tick count of last input event


class Logger(threading.Thread):
    '''
    Logs information about the active window.
    '''
    def __init__(self, logdir, *args, **kwargs):
        self.windows = []
        self._run = True
        self.logdir = logdir
        threading.Thread.__init__(self, *args, **kwargs)
      
    def stop(self):
        '''
        Sets a flag that causes the thread loop to exit
        '''
        self._run = False
      
    def run(self):
        '''
        Polls to gather and log information about the active window
        '''
        last_title = ""
        last_exe_name = ""
        last_day = None
        idle_start = 0
        while(self._run):
            try:
                # Log idle time info
                #
                # Detail: Check idle time; if it has exceeded 3 minutes, log 
                # elasped idle time when window activity resumes
                
                # Get idle time
                # see: http://msdn.microsoft.com/en-us/library/ms646302%28VS.85%29.aspx
                # GetTickCount() returns the tick count for the current time 
                #   (ms since system boot)
                # GetLastInputInfo(..) returns the tick count for the last 
                #   input event, with some caveats
                # idle_ms = GetTickCount() - GetLastInputInfo(..)
                info = LastInputInfo()
                info.cbSize = pointer_size() * 2
                if(windll.user32.GetLastInputInfo(byref(info)) != 0):
                    idle_ms = windll.kernel32.GetTickCount() - info.dwTime
                else:
                    idle_ms = 0
                    logging.warning("GetLastInputInfo failed")
                  
                # If no activity for more than than 3 min, log an idle time 
                # event.
                #
                # Detail: When 3 mins have passed since last input event, set
                # idle_start; If idle_start is set and less than 3 mins have 
                # passed since last input event (i.e. window activity has 
                # resumed), log an idle time event and clear idle_start.
                threshold = 1000 * 60 * 3 # min
                if idle_ms > threshold and not idle_start:
                    idle_start = time.time()  
                elif idle_ms < threshold and idle_start:
                  try:
                      fname = datetime.datetime.now().strftime("%Y-%m-%d windows.csv")
                      with open(os.path.join(self.logdir, fname), "ab") as csvfile:
                          csv.writer(csvfile).writerow(["idle_time", idle_start, time.time()])
                      idle_start = 0
                  except IOError as e:
                      logging.error("idle time logging failed: " + str(e))
                      
                # Log foreground window info
                #
                # Detail: Get the foreground window info; if has changed, log 
                # it
                
                # Get foreground window information
                wh = windll.user32.GetForegroundWindow()
                textlen = windll.user32.GetWindowTextLengthA(wh) + 1
                window_title = " " * textlen
                windll.user32.GetWindowTextA(wh, window_title, textlen)
                pid = ctypes.c_int()
                if not windll.user32.GetWindowThreadProcessId(wh, ctypes.byref(pid)):
                    warnings.warn("GetWindowThreadId failed (NULL tid)")
                    continue
                ph = windll.kernel32.OpenProcess(0x410, False, pid) 
                in_len = 128
                out_len = 129
                while out_len > in_len:
                    exe_name = " "*in_len
                    out_len = windll.psapi.GetProcessImageFileNameA(ph, exe_name, in_len)
                    in_len += out_len
                exe_name = os.path.basename(exe_name[:out_len])
                  
                # If foreground info has changed, log it
                if (exe_name, window_title) != (last_exe_name, last_title):
                  start_time = time.time()
                  last_exe_name = exe_name
                  last_title = window_title
                  try:
                      fname = datetime.datetime.now().strftime("%Y-%m-%d windows.csv")
                      with open(os.path.join(self.logdir, fname), "ab") as csvfile:
                          csv.writer(csvfile).writerow(["window_info", exe_name, window_title, start_time])
                  except IOError as e:
                      logging.error("window info logging failed: " + str(e))
                  
                time.sleep(1) 
            except Exception as e:
                logging.exception("exception in run loop:" + str(e))
                logging.error("failure, run exiting")
        logging.debug("stopping")


class JsArrayFile(object):
  '''
  Represents a Javascript array file that gets written to disk.
  Used by Analyzer; part of a hack to give javascript in chart.html access to
  the log data on disk. There is probably a better way to do this : )
  '''
  def __init__(self, filename):
      '''
      Opens a file descriptor and writes a Javascript Array declaration.
      '''
      self.out_fd = file(filename, "wt")
      self.out_fd.write("var watchme_data = new Array(); \n") # beginning of array def'n
      self.i = 0
      
  def append(self, item):
      '''
      Writes item to self.out_fd as a Javascript Array element
      '''
      if not getattr(self, "out_fd", None):
          raise RuntimeException("out_fd not available, was finish() called already?")
      try:
          item = [i.replace("\\", "\\\\").replace("\"", "\\\"") for i in item] # escape \'s to appease JS rules, TODO: are there more to add?
      except Exception as e:
          logger.error("error processing item=%s: %s" % (str(item), str(e)))
          
      # [exe_name, window_title, start_time, end_time, date]
      self.out_fd.write("watchme_data[%d] = {\n\tid: %d,\n\texe_name: \"%s\",\n\twindow_title: \"%s\",\n\tstart_time: %s,\n\tend_time:%s, \n\tdate:\"%s\"};\n" %\
          ((self.i, self.i, ) + tuple(item)))
      self.i += 1
      
  def finish(self):
      '''
      Closes the file descriptor
      '''
      self.out_fd.close()
      self.out_fd = None
      self.i = 0


# >python -i -c "from watchme import Analyzer; import os; a = Analyzer(os.getcwd() + \"\\data\"); a.analyze()"
class Analyzer(object):
  '''
  Used to Analyze log data. Aggregates log data from CSV files on disk, writes 
  them to a javascript file, then launches an HTML file with the default 
  browser that reads the javascript file and supplies a GUI for the user to 
  analyze the data.
  '''
  def __init__(self, directory):
    self.directory = directory
    
  def analyze(self):
    '''
    Parses CSV files created by logger and writes result to an HTML file as 
    a javascript array (as a workaround to same-origin-policy security). 
    There might be a better way...
    '''
    logging.info("Analyzer.analyze called, self.directory=%s" % self.directory)
    data = []
    
    # Create a Javascript file for aggregated log data
    try:
        js_array = JsArrayFile(os.path.join(self.directory, "alldata.js"))
    except Exception as e:
        logging.error("error while creating JsArrayFile: %s" % str(e))
        raise e
        
    # Loop over log files and store data to Javascript array files
    try:
        for fname in os.listdir(self.directory):
            try:
                if re.match(".*windows.csv$", fname):
                    start_time = None
                    
                    # Process a log file
                    with open(os.path.join(self.directory, fname), "rt") as csvfile:
                      
                        for row in csv.reader(csvfile):
                            # If this is a window_info row: if we've already 
                            # seen a window_info row, calculate inter-window 
                            # time and log it. Otherwise we don't know when 
                            # this window started, so store this window info
                            # to memory and log it later.
                            if row[0] == "window_info": 
                                # Row format: row_type,proc_name,window_title,start_time
                                if start_time != None: 
                                    # Get end_time for previous row and dump to file
                                    end_time = row[3] 
                                    date = datetime.datetime.fromtimestamp(float(start_time)).strftime("%Y/%m/%d")
                                    js_array.append([exe_name, window_title, start_time, end_time, date])
                                    
                                # Get data for current row
                                exe_name, window_title, start_time = row[1:]
                                
                            else: # this is a idle_time row
                                # Since this is an idle_time row, we just have 
                                # to log the info for the preceding window_info
                                # (since we know know the end_time) and move on.
                                
                                if not start_time: 
                                    # If we haven't seen a start time, this 
                                    # log file started with an idle_time row: 
                                    # no window activity to log; move on. 
                                    continue
                                    
                                # Get end_time for previous row and dump to DB
                                end_time = row[1] # row[1] = start of idle time
                                if end_time < start_time:
                                    # This is a workaround for a bug in 
                                    # previous versions of this script that
                                    # has corrupted some data: 
                                    # Due to the bug, now idle_time rows are 
                                    # not in chronological order in some of my 
                                    # old log files. 
                                    # So for now, we skip these rows.
                                    # TODO: correct the old log files and delete
                                    # this workaround. Also, add versioning to 
                                    # this script and log files : )
                                    continue
                                date = datetime.datetime.fromtimestamp(float(start_time)).strftime("%Y/%m/%d")
                                js_array.append([exe_name, window_title, start_time, end_time, date])
            except Exception as e:
                logging.error("error while processing file: %s" % csvfile.name)
                raise e
                
    except Exception as e:
        logging.error("error while gathering data: %s" % str(e))
        raise e
      
    # Close the Javascript Array file, which now contains all activity data.
    try:  
        js_array.finish()
    except Exception as e:
        logging.error("error while writing chart postlude: %s" % str(e))
        raise e
      
    # Launch the analyzer page (which reads the Javascript array file) with the
    # default browser.
    try:
        subprocess.Popen("chart.html", shell=True)
    except Exception as e:
        logging.error("error while launching chart viewer: %s" % str(e))
        raise e
 

class Watcher(SysTrayIcon):
    '''
    Watches window activity and supplies a UI to the user via a system tray
    widget.
    '''
    def __init__(self, path):
        '''
        Starts the logger and sets up the system tray widget.
        '''
        if not os.path.exists(path):
          os.makedirs(path)
          
        self.analyzer = Analyzer(path)
        self.logger = Logger(path)
        self.logger.start()
        logging.debug("Logger started; path=%s" % path)
        SysTrayIcon.__init__(self, 
            "./resources/watchme.ico", 
            "watchme", 
            (('Analyze me', None, self.analyze),), 
            on_quit=self.stop, 
            default_menu_index=1)
        
    def stop(self):
        # Tells the logger to stop
        self.logger.stop()
        logging.debug("logger.stop called")
      
    def analyze(self, trayicon):
        # Runs the analysis script
        self.analyzer.analyze()


if __name__=="__main__":
    # Launches the Watcher system tray widget, which in turns starts window 
    # activity logging
    
    datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
    if not os.path.exists(datadir):
        os.makedirs(datadir)
        
    logger = logging.getLogger()
    handler = logging.FileHandler(os.path.join(datadir, "log.txt"))
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    Watcher(datadir)