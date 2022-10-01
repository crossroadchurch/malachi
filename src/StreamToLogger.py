# https://stackoverflow.com/a/51612402
# https://stackoverflow.com/a/616686
import sys

class StreamToLogger(object):
   """
   Fake file-like stream object that redirects writes to a logger instance.
   """
   def __init__(self, logger, level):
      self.logger = logger
      self.level = level
      self.linebuf = ''
      self.stdout = sys.stdout

   def write(self, buf):
      try:
         for line in buf.rstrip().splitlines():
            self.stdout.write(line + '\n')
            self.logger.log(self.level, line.rstrip())
      except UnicodeEncodeError as e:
         print("UnicodeEncodeError encountered")

   def flush(self):
      pass

