"""
Flashcard data and operations.
"""

import datetime
import math
import random
import itertools

time_fmt = "%Y-%m-%d"

class card:
  def __init__(self, top, bot, time, repetitions=0, interval=1, easiness=2.5):
    self.top = top
    self.bot = bot
    self.time = time.replace(second=0, microsecond=0)
    self.repetitions = repetitions
    self.interval = interval
    self.easiness = easiness
    self.filename = None # Reserved for use by {load,save}_all

  def is_new(self):
    return self.repetitions == 0

  def next_time(self):
    return self.time + datetime.timedelta(days=math.ceil(self.interval))

  def repeat(self, quality, time):
    # SM-2
    assert quality >= 0 and quality <= 5
    self.easiness = max(1.3, self.easiness + 0.1 - (5.0 - quality) * (0.08 + (5.0 - quality) * 0.02))
    if quality < 3: self.repetitions = 0
    else: self.repetitions += 1
    if self.repetitions == 1: self.interval = 1
    elif self.repetitions == 2: self.interval = 6
    else: self.interval *= self.easiness
    self.time = time

  is_new = property(is_new)
  next_time = property(next_time)

def save(output, cards):
  for card in cards:
    parts = (card.time.strftime(time_fmt), str(card.repetitions), str(card.interval), str(card.easiness), card.top, card.bot)
    print >> output, '\t'.join(parts)

def load(input):
  for line in input:
    parts = line.strip().split('\t')
    if len(parts) != 6:
      raise IOError("wrong number of records on line")
    time, repetitions, interval, easiness, top, bot = parts
    time = datetime.datetime.strptime(time, time_fmt)
    repetitions = int(repetitions)
    interval = float(interval)
    easiness = float(easiness)
    new = card(top, bot, time, repetitions, interval, easiness)
    yield new

def save_all(cards):
  import argopen
  outputs = {}
  try:
    for card in cards:
      if card.filename not in outputs:
        outputs[card.filename] = argopen.open(card.filename, 'w')
      save(outputs[card.filename], [card])
  finally:
    for output in outputs.values():
      output.close()

def load_all(filenames):
  import argopen
  for filename in filenames:
    with argopen.open(filename) as input:
      for card in load(input):
        card.filename = filename
        yield card

def fetch_cards(cards, now, max_reviews=None, max_new=None, randomize=False):
  new_cards = list(itertools.islice((c for c in cards if c.is_new), max_new))
  new_cards.reverse()
  to_review = list(itertools.islice((c for c in cards if not c.is_new and c.next_time <= now), max_reviews))
  to_review.reverse()
  if randomize:
    random.shuffle(to_review)
  def choose_next():
    if len(to_review) > 0:
      return to_review.pop()
    elif len(new_cards) > 0:
      return new_cards.pop()
    else:
      return None
  def reject_card(card):
    if card.is_new:
      new_cards.insert(0, card)
    else:
      to_review.insert(0, card)
  return choose_next, reject_card

def run_cards(cards, now, review_card, max_reviews=None, max_new=None, randomize=False):
  choose_next, reject_card = fetch_cards(cards, now, max_reviews, max_new, randomize)

  while True:
    current = choose_next()
    if current is None:
      break
    quality = review_card(current)
    current.repeat(quality, now)
    if current.is_new:
      reject_card(current)

def bulk_review(cards, now, batch_size, show_batch, review_card, max_reviews=None, max_new=None, randomize=False):
  import random

  choose_next, reject_card = fetch_cards(cards, now, max_reviews, max_new, randomize)

  batch = [n for i in range(batch_size) for n in [choose_next()] if n is not None]
  while len(batch) > 0:
    random.shuffle(batch)

    show_batch(batch)
    def run_card(card):
      quality = review_card(card)
      card.repeat(quality, now)
      return quality
    batch = [c for c in batch for r in [run_card(c)] if c.is_new]
    
    while len(batch) < batch_size:
      next = choose_next()
      if next is None:
        break
      batch.append(next)
