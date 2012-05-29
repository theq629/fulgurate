"""
Utility for opening files, handling both the '-' as stdin/out convention and optional atomic writing.
"""

import sys
import __builtin__
import tempfile, shutil
import itertools
import os
import os.path

class open:
  def __init__(self, filename, mode='r', atomic=False, *rest):
    self.filename = filename
    self.mode = mode
    self.rest = rest
    self.atomic = atomic
    self.using_std = False
    self.using_temp = False
    self.file = None

  def __enter__(self):
    writing = 'w' in self.mode
    if self.filename == '-':
      import sys
      if writing:
        self.file = sys.stdout
      else:
        self.file = sys.stdin
      self.using_std = True
    else:
      if self.atomic and writing:
        self.file = tempfile.NamedTemporaryFile(prefix=os.path.basename(self.filename), delete=False)
        self.using_temp = True
      else:
        self.file = __builtin__.open(self.filename, self.mode, *self.rest)
    return self.file

  def __exit__(self, type, value, traceback):
    self.close()

  def close(self):
    if self.file is not None:
      if not self.using_std:
        self.file.close()
      if self.using_temp:
        shutil.move(self.file.name, self.filename)

  def write(self, string):
    if self.file is None:
      self.__enter__()
    self.file.write(string)
