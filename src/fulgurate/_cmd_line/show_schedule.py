#!/usr/bin/env python2

"""
Prints information about how the cards in a file are currently scheduled. The
first column in the output is the date, the second is number of days in the
future, and the third is the number of cards scheduled for that time. A -1 in
the second column indicates new cards, while 0 indicates the cards that are
ready for review.
"""

from typing import Iterable, MutableMapping
import sys
import collections
import argparse
import datetime
import tabulate
from .._card import Card
from .. import files
from . import _args

_TIME_FMT = "%Y-%m-%d"

_Schedule = Iterable[tuple[datetime.datetime, int, int]]

def _make_schedule(deck: Iterable[Card], now: datetime.datetime) -> _Schedule:
    unseen = 0
    on_day: MutableMapping[datetime.datetime, int] = collections.defaultdict(int)
    for card in deck:
        if card.is_new:
            unseen += 1
        else:
            on_day[card.next_time] += 1

    yield now, -1, unseen

    schedule = [
        (next_time, (next_time - now).days, on_day[next_time])
        for next_time in on_day
    ]
    schedule.sort(key=lambda tdn: tdn[1])
    yield from schedule

def _show_schedule_simple(table: _Schedule) -> None:
    for time, days_away, num in table:
        print(f"{time.strftime(_TIME_FMT)} {days_away} {num}")

def _show_schedule_tabulate(table: _Schedule) -> None:
    print(tabulate.tabulate(
        ((t.strftime(_TIME_FMT), d, n) for t, d, n in table),
        headers=['review time', 'days away', 'number of cards'],
    ))

def make_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description=__doc__.strip())
    arg_parser.add_argument(
        'input_file',
        metavar="DECK-FILE",
        type=argparse.FileType('r'),
        default=[sys.stdin],
        nargs="*",
        help="Path to input deck file.",
    )
    arg_parser.add_argument(
        '-s',
        '--simple-table',
        dest='simple_table',
        default=False,
        action='store_true',
        help="Output a single-space separated table with no header, instead of pretty printing.",
    )
    _args.add_now(arg_parser)
    return arg_parser

def main() -> None:
    """
    Entry point.
    """
    args = make_arg_parser().parse_args()

    args.now = args.now.replace(hour=0, minute=0, second=0, microsecond=0)
    deck = (
        card
        for in_file in args.input_file
        for card in files.load(in_file)
    )
    schedule = _make_schedule(deck, args.now)
    if args.simple_table:
        _show_schedule_simple(schedule)
    else:
        _show_schedule_tabulate(schedule)

if __name__ == "__main__":
    main()
