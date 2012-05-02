"""
Unbuffered IO.
"""

import os
import sys
import tty, termios
import tempfile, shutil

_clear = os.popen("clear").read()

class unbuffered:
  def __init__(self, output):
    self.output = output

  def __enter__(self):
    try:
      self.fd = self.output.fileno()
      self.old_attr = termios.tcgetattr(self.fd)
      tty.setraw(self.fd)
    except termios.error:
      pass
    return self.output

  def __exit__(self, type, value, traceback):
    try:
      termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_attr)
    except termios.error, AttibuteError:
      pass

def getch():
  ch = sys.stdin.read(1)
  if ch == '\x03':
    raise KeyboardInterrupt()
  return ch

def clear():
  sys.stdout.write(_clear)
