#!/usr/bin/env python2

"""
Reviews one or more sets of flashcards interactively at the terminal. Cards can
be presented individually (the default) or in batches where several cards will
be presented before user feedback is required.

The interaction for each card is as follows. The program first shows the first
(top) part of the card. Press any key after deciding on an answer. The program
then shows the second (bottom) part of the card. Press ~,1,2,3,4,5 for 0
through 5 respectively, indicating your evaluation of how well you remembered
the answer. 0 through 2 are failure responses and 3 through 5 are success.
"""

from typing import Any, Optional, Iterable, NamedTuple
import sys
import os
import subprocess
from contextlib import nullcontext
import datetime
import csv
import argparse
from .._card import Card, RepetitionQuality
from .. import review
from ..files import SourcedDeck
from . import _ttyio, _args

def _show_batch(cards: Iterable[Card]) -> None:
    _ttyio.clear()
    for i, card in enumerate(cards):
        print(f"{i + 1}: {card.top}\r")
    print("\r")

_DEFAULT_CSV_DIALECT = 'excel-tab'
_EXTERNAL_FILTER_CSV_FIELDS = ('source', 'top', 'bottom')

class _ExternalFilterRow(NamedTuple):
    path: str
    top: str
    bottom: str

class _ExternalFilterInteracter:
    """
    Manages interaction with an external filter program.
    """
    def __init__(self, command: str, csv_dialect: type[csv.Dialect], deck: SourcedDeck):
        # pylint: disable=consider-using-with
        self._proc = subprocess.Popen(
            command,
            shell=True,
            encoding='utf-8',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        self._writer = csv.DictWriter(
            self._proc.stdin,
            fieldnames=_EXTERNAL_FILTER_CSV_FIELDS,
            dialect=csv_dialect,
        )
        self._reader = csv.DictReader(
            self._proc.stdout,
            fieldnames=_EXTERNAL_FILTER_CSV_FIELDS,
            dialect=csv_dialect,
        )
        self._deck = deck

    def send_card(self, card: Card) -> None:
        """
        Send a card to the external filter program.
        """
        assert self._proc.stdin is not None
        self._writer.writerow({
            'source': self._deck.get_source(card),
            'top': card.top,
            'bottom': card.bottom,
        })
        self._proc.stdin.flush()

    def receive(self) -> _ExternalFilterRow:
        """
        Get result from the external filter.
        """
        assert self._proc.stdout is not None
        row = next(self._reader)
        return _ExternalFilterRow(row['source'], row['top'], row['bottom'])

    def __enter__(self) -> "_ExternalFilterInteracter":
        return self

    def __exit__(self, _type: Any, _value: Any, _traceback: Any) -> None:
        self.close()

    def close(self) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.close()
        os.waitpid(self._proc.pid, 0)

class _ExternalFilter:
    """
    Manages an external filter program.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, command: str) -> None:
        self._command = command

    def interact(self, dialect: type[csv.Dialect], deck: SourcedDeck) -> _ExternalFilterInteracter:
        return _ExternalFilterInteracter(self._command, dialect, deck)

def _review_card(
    card: Card,
    *,
    deck: SourcedDeck,
    clear: bool = True,
    wait: bool = True,
    ext_filter_interacter: Optional[_ExternalFilterInteracter] = None,
    ext_finish_interacter: Optional[_ExternalFilterInteracter] = None,
) -> RepetitionQuality:
    if clear:
        _ttyio.clear()
    with _ttyio.Unbuffered(sys.stdin):
        if ext_filter_interacter is None:
            source, top, bottom = str(deck.get_source(card)), card.top, card.bottom
        else:
            ext_filter_interacter.send_card(card)
            source, top, bottom = ext_filter_interacter.receive()
        if source:
            print(f"{source}\r")
        print(f"{top}\r")
        if wait:
            _ttyio.getch()
        print(f"{bottom}\r")
        if ext_finish_interacter is not None:
            ext_finish_interacter.send_card(card)
        while True:
            in_char = _ttyio.getch()
            if in_char in ('0', '`'):
                return RepetitionQuality(0)
            if in_char in "12345":
                return RepetitionQuality(int(in_char))

def _review_deck(
    deck: SourcedDeck,
    *,
    now: datetime.datetime,
    max_old: int,
    max_new: int,
    randomize: bool,
    randomize_batch: bool,
    batch_size: Optional[int],
    ext_filter: Optional[_ExternalFilter],
    ext_finish: Optional[_ExternalFilter] = None,
    filter_csv_dialect: type[csv.Dialect],
    card_file_encoding: str,
) -> None:
    ext_filter_int_ctx = ext_filter.interact(filter_csv_dialect, deck) \
        if ext_filter is not None else nullcontext()
    ext_finish_int_ctx = ext_finish.interact(filter_csv_dialect, deck) \
        if ext_finish is not None else nullcontext()
    try:
        with ext_filter_int_ctx as ext_filter_int, \
             ext_finish_int_ctx as ext_finish_int, \
             _ttyio.Unbuffered(sys.stdin):
            now = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if batch_size is None:
                review.review_cards(
                    deck,
                    now,
                    lambda *args: _review_card(
                        *args,
                        deck=deck,
                        ext_filter_interacter=ext_filter_int,
                        ext_finish_interacter=ext_finish_int
                    ),
                    max_old=max_old,
                    max_new=max_new,
                    randomize=randomize,
                )
            else:
                review.review_cards_batched(
                    deck,
                    now,
                    batch_size=batch_size,
                    show_batch=_show_batch,
                    review_card=lambda *args: _review_card(
                        *args,
                        deck=deck,
                        clear=False,
                        wait=False,
                        ext_filter_interacter=ext_filter_int,
                        ext_finish_interacter=ext_finish_int
                    ),
                    max_old=max_old,
                    max_new=max_new,
                    randomize=randomize,
                    randomize_batch=randomize_batch,
                )
    except KeyboardInterrupt:
        pass
    finally:
        deck.save(encoding=card_file_encoding)

def make_arg_parser() -> argparse.ArgumentParser:
    filter_input_info = "It should take on stdin a CSV or TSV file, according to the dialect set" \
                        " on the command line. The fields are card source (path), card top, and" \
                        " card bottom, in that order."
    arg_parser = argparse.ArgumentParser(description=__doc__.strip())
    arg_parser.add_argument(
        'input_paths',
        metavar="DECK-FILE",
        type=str,
        nargs="*",
        default=["-"],
        help="Path to input deck file.",
    )
    _args.add_now(arg_parser)
    _args.add_card_file_encoding(arg_parser)
    arg_parser.add_argument(
        '-O',
        '--max-to-old',
        dest='max_old',
        type=int,
        help="The maximum number of old cards to review.",
    )
    arg_parser.add_argument(
        '-N',
        '--max-new',
        dest='max_new',
        type=int,
        help="The maximum number of new cards to review.",
    )
    arg_parser.add_argument(
        '-r',
        '--randomize',
        dest='randomize',
        default=False,
        action='store_true',
        help="Randomly order cards to review, from among all input card sets."
    )
    arg_parser.add_argument(
        '-R',
        '--randomize-batch',
        dest='randomize_batch',
        default=False,
        action='store_true',
        help="Randomly order cards within each batch, if using batch mode."
    )
    arg_parser.add_argument(
        '-b',
        '--batch-size',
        dest='batch_size',
        type=int,
        help="The size for each batch. Setting this enables batch mode.",
    )
    arg_parser.add_argument(
        '-f',
        '--card-filter',
        dest='ext_filter',
        type=_ExternalFilter,
        default=None,
        help=f"""
            Set a command to filter cards. {filter_input_info} It should output
            to stdout new card data in the same format, which will be shown
            instead of the original card data. It should either not buffer
            output, or flush after each row, since cards will be sent
            and read one-by-one.
        """
    )
    arg_parser.add_argument(
        '-F',
        '--finish-filter',
        dest='ext_finish',
        type=_ExternalFilter,
        default=None,
        help=f"""
            Set a command to send a card to after the card's second field is
            shown. {filter_input_info} Its output is ignored.
        """
    )
    arg_parser.add_argument(
        '-d',
        '--filter-csv-dialect',
        dest='filter_csv_dialect',
        type=str,
        choices=csv.list_dialects(),
        default=_DEFAULT_CSV_DIALECT,
        help=f"""
            The CSV dialect from Python's csv module to use for reading to and
            writing from the card filter and finish filter. Defaults to
            '{_DEFAULT_CSV_DIALECT}'.
        """
    )
    return arg_parser

def main() -> None:
    """
    Entry point.
    """

    args = make_arg_parser().parse_args()

    _review_deck(
        deck=SourcedDeck(args.input_paths, encoding=args.card_file_encoding),
        now=args.now,
        max_old=args.max_old,
        max_new=args.max_new,
        randomize=args.randomize,
        randomize_batch=args.randomize_batch,
        batch_size=args.batch_size,
        ext_filter=args.ext_filter,
        ext_finish=args.ext_finish,
        filter_csv_dialect=args.filter_csv_dialect,
        card_file_encoding=args.card_file_encoding,
    )

if __name__ == "__main__":
    main()
