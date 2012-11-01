import re
def isEmail(window):
  if "Outlook" in window.window_title:
    return True
  return False

def isWebSurfing(window):
  if "Chrome" in window.window_title:
    return True
  return False
  
def isPythonCode(window):
  return bool(re.match('.*\\\([\w]*\.py).*', window.window_title))
'''
def isPythonCoding(window):
  if "UltraEdit" in window.window_title and 
'''
'''
perhaps create a special predicate for 'isInTitle' so I can just
define a list of keywords in title/executable?

will still need explicit rules...
'''