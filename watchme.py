'''
Windows usage data collector & analyzer
Usage: python watchme.py ... then use the task tray interface

TODOs:
Daemonize & survive Windows sleeping (works with python.exe, but not pythonw.exe) [DONE]
Add idle time logging [DONE]
Add support for idle_time/window_time processing to analyzer
Add additional analysis
Implement lock/some sort of singleton to prevent running proc twice
Add ML :)

Written by Jonathan Foote (jmfoote@andrew.cmu.edu)

NTS: to get date/time in excel: =(((C2-(6*3600))/86400)+25569)
'''

from ctypes import windll, Structure, c_ulong, byref
import ctypes, threading, time, os, warnings, datetime, sys
from collections import namedtuple
import csv, logging

from systrayicon import SysTrayIcon

def pointer_size():
  import platform
  bits = platform.architecture()[0]
  return int(re.match("^([\d]*)", bits).groups()[0]) / 8

class LastInputInfo(Structure):
  _fields_ = [("cbSize", c_ulong),
              ("dwTime", c_ulong)]

class Logger(threading.Thread):
  def __init__(self, logdir, *args, **kwargs):
    self.windows = []
    self._run = True
    self.logdir = logdir
    threading.Thread.__init__(self, *args, **kwargs)
    
  def stop(self):
    self._run = False
    
  def run(self):
    last_title = ""
    last_exe_name = ""
    last_day = None
    idle_start = 0
    while(self._run):
      try:
        #logging.debug("running")
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
          in_len = out_len
        exe_name = os.path.basename(exe_name[:out_len])
          
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
            
        # get idle time
        # see: http://msdn.microsoft.com/en-us/library/ms646302%28VS.85%29.aspx
        info = LastInputInfo()
        info.cbSize = pointer_size() * 2
        if(windll.user32.GetLastInputInfo(byref(info)) != 0):
          idle_ms = windll.kernel32.GetTickCount() - info.dwTime
        else:
          idle_ms = 0
          logging.warning("GetLastInputInfo failed")
        
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
          
        time.sleep(1)
      except Exception as e:
        logging.error("exception=" + str(e) + ", sys.exc_info=" + str(sys.exc_info()))
        logging.error("failure -- run exiting")
    logging.debug("stopping")
    
import subprocess, re

class Analyzer(object):
  def __init__(self, directory):
    self.directory = directory
    
  def analyze(self):
    logging.debug("Analyzer.analyze called")
    #import pdb; pdb.set_trace()
    try:
      # gather rows from all log files
      rows = []
      for fname in os.listdir(self.directory):
        if re.match(".*windows.csv$", fname):
          print "fname match: ", fname
          with open(os.path.join(self.directory, fname), "rb") as csvfile:
            for row in csv.reader(csvfile):
              rows.append(row)
  
      # analyze data            
      rows = sorted(rows, lambda x, y: x[-1] > y[-1]) # sort by time
      for i in xrange(0, len(rows)):
        rows[i].append(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(rows[i][2]))))
        if i == len(rows) - 1:
          break
        rows[i].append(int(round(float(rows[i+1][2]) - float(rows[i][2]), 0)))
    except Exception as e:
      logging.error("error while gathering data: %s" % str(e))
      raise e
    
    # output result
    try:
      fname = datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S analysis.csv")
      with open(os.path.join(self.directory, fname), "ab") as csvfile:
        for row in rows: # TODO: fix
          csv.writer(csvfile).writerow(row)
    except Exception as e:
      #warnings.warn(str(e))
      logging.error("error while writing result: %s" % str(e))
      raise e
      
    # display result w/ default CSV app
    # TODO: make this secure
    try:
      subprocess.Popen(os.path.join(self.directory, fname), shell=True)
    except Exception as e:
      logging.error("error while running csv viewer app: %s" % str(e))
      raise  
    
class Watcher(SysTrayIcon):
  def __init__(self, path):
    if not os.path.exists(path):
      os.makedirs(path)
      
    self.analyzer = Analyzer(path)
    self.logger = Logger(path)
    self.logger.start()
    logging.debug("Logger started; logging to %s" % path)
    SysTrayIcon.__init__(self, 
      "watchme.ico", 
      "watchme", 
      (('Analyze me', None, self.analyze),), 
      on_quit=self.stop, 
      default_menu_index=1)
      
  def stop(self):
    self.logger.stop()
    logging.debug("logger.stop called")
    
  def analyze(self, trayicon):
    self.analyzer.analyze()
    
if __name__=="__main__":  
  appdir = os.path.join(os.environ["HOMEPATH"], "watchme")
  logger = logging.getLogger()
  handler = logging.FileHandler(os.path.join(appdir, "log.txt"))
  fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
  handler.setFormatter(fmt)
  logger.addHandler(handler)
  #if len(sys.argv) > 1 and sys.argv[1] == "-d":
  logger.setLevel(logging.DEBUG)
  #else:
  #  logger.setLevel(logging.INFO)
  
  Watcher(appdir)