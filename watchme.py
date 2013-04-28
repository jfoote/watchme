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

class JsArrayFile(object):
  def __init__(self, filename):
      self.out_fd = file(filename, "wt")
      self.out_fd.write("var watchme_data = new Array(); \n") # beginning of array def'n
      self.i = 0
      
  def append(self, item):
      if not getattr(self, "out_fd", None):
          raise RuntimeException("out_fd not available, was finish() called already?")
      try:
          item = [i.replace("\\", "\\\\").replace("\"", "\\\"") for i in item] # escape \'s to appease JS rules, TODO: are there more to add?
      except Exception as e:
          logger.error("error processing item=%s: %s" % (str(item), str(e)))
          
      # [exe_name, window_title, start_time, end_time]
      self.out_fd.write("watchme_data[%d] = {\n\tid: %d,\n\texe_name: \"%s\",\n\twindow_title: \"%s\",\n\tstart_time: %s,\n\tend_time:%s};\n" %\
        ((self.i, self.i, ) + tuple(item)))
      self.i += 1
      
  def finish(self):
      self.out_fd.close()
      self.out_fd = None
      self.i = 0

class Analyzer(object):
  def __init__(self, directory):
    self.directory = directory
    
  def analyze(self):
    '''
    Parses CSV files created by logger and writes result to an HTML file as 
    a javascript array (as a workaround to same-origin-policy security). 
    There might be a better way...
    '''
    logging.info("Analyzer.analyze called")
    data = []
    try:
      js_array = JsArrayFile(os.path.join(self.directory, "alldata.js"))
    except Exception as e:
      logging.error("error while creating JsArrayFile: %s" % str(e))
      raise e
      
    try:
      for fname in os.listdir(self.directory):
        if re.match(".*windows.csv$", fname):
          print "fname match: ", fname
          start_time = None
          with open(os.path.join(self.directory, fname), "rt") as csvfile:
            for row in csv.reader(csvfile):
              if row[0] == "window_info": # window_info row
                if start_time != None: 
                  # get end_time for previous row and dump to DB
                  end_time = row[3] 
                  js_array.append([exe_name, window_title, start_time, end_time])
                  
                # get data for current row
                exe_name, window_title, start_time = row[1:]
                  
              else: # idle_time row
                  if not start_time: # this is the first entry in the file, skip it
                      continue
                  # get end_time for previous row and dump to DB
                  end_time = row[1]
                  js_array.append([exe_name, window_title, start_time, end_time])
                  
    except Exception as e:
      logging.error("error while gathering data: %s" % str(e))
      raise e
    
    try:  
        js_array.finish() # write end of HTML doc
    except Exception as e:
      logging.error("error while writing chart postlude: %s" % str(e))
      raise e
    
    try:
        #chart.show()
        pass
    except Exception as e:
      logging.error("error while launching chart viewer: %s" % str(e))
      raise e
    
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
  datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
  print "datadir = " + datadir
  if not os.path.exists(datadir):
      os.makedirs(datadir)
      
  logger = logging.getLogger()
  handler = logging.FileHandler(os.path.join(datadir, "log.txt"))
  fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
  handler.setFormatter(fmt)
  logger.addHandler(handler)
  #if len(sys.argv) > 1 and sys.argv[1] == "-d":
  logger.setLevel(logging.DEBUG)
  #else:
  #  logger.setLevel(logging.INFO)
  
  Watcher(datadir)