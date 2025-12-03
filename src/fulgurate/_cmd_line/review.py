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

from typing import Optional, Iterable, NamedTuple
from pathlib import Path
import sys
import os
import subprocess
import datetime
import argparse
from .._card import Card, RepetitionQuality
from .. import files, review
from . import _ttyio, _args

def _show_batch(cards: Iterable[Card[Path]]) -> None:
    _ttyio.clear()
    for i, card in enumerate(cards):
        print(f"{i + 1}: {card.top}\r")
    print("\r")

class _ExternalFilterRow(NamedTuple):
    path: str
    top: str
    bottom: str

class _ExternalFilter:
    """
    Manages an external filter program.
    """
    def __init__(self, command: str) -> None:
        # pylint: disable=consider-using-with
        self._proc = subprocess.Popen(
            command,
            shell=True,
            encoding='utf-8',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def send_card(self, card: Card[Path]) -> None:
        """
        Send a card to the external filter program.
        """
        assert self._proc.stdin is not None
        print(f"{str(card.source) or ''}\t{card.top}\t{card.bottom}", file=self._proc.stdin)
        self._proc.stdin.flush()

    def receive(self) -> _ExternalFilterRow:
        """
        Get result from the external filter.
        """
        assert self._proc.stdout is not None
        got = tuple(self._proc.stdout.readline().rstrip('\n').split('\t'))
        if len(got) != 3:
            raise ValueError("wrong number of values on line from external filter")
        return _ExternalFilterRow(*got)

    def close(self) -> None:
        """
        Close the program.
        """
        assert self._proc.stdin is not None
        self._proc.stdin.close()
        os.waitpid(self._proc.pid, 0)

def _review_card(
    card: Card[Path],
    *,
    clear: bool = True,
    wait: bool = True,
    ext_filter: Optional[_ExternalFilter] = None,
    ext_finish: Optional[_ExternalFilter] = None,
) -> RepetitionQuality:
    if clear:
        _ttyio.clear()
    with _ttyio.Unbuffered(sys.stdin):
        if ext_filter is None:
            source, top, bottom = str(card.source), card.top, card.bottom
        else:
            ext_filter.send_card(card)
            source, top, bottom = ext_filter.receive()
        if source:
            print(f"{source}\r")
        print(f"{top}\r")
        if wait:
            _ttyio.getch()
        print(f"{bottom}\r")
        if ext_finish is not None:
            ext_finish.send_card(card)
        while True:
            in_char = _ttyio.getch()
            if in_char in ('0', '`'):
                return RepetitionQuality(0)
            if in_char in "12345":
                return RepetitionQuality(int(in_char))

def _review_deck(
    deck: Iterable[Card[Path]],
    *,
    now: datetime.datetime,
    max_reviews: int,
    max_new: int,
    randomize: bool,
    batch_size: Optional[int],
    ext_filter: Optional[_ExternalFilter],
    ext_finish: Optional[_ExternalFilter] = None,
) -> None:
    try:
        with _ttyio.Unbuffered(sys.stdin):
            now = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if batch_size is None:
                review.review_cards(
                    deck,
                    now,
                    lambda *args: _review_card(
                        *args,
                        ext_filter=ext_filter,
                        ext_finish=ext_finish
                    ),
                    max_reviews=max_reviews,
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
                        clear=False,
                        wait=False,
                        ext_filter=ext_filter,
                        ext_finish=ext_finish
                    ),
                    max_reviews=max_reviews,
                    max_new=max_new,
                    randomize=randomize,
                    randomize_batch=True,
                )
    except KeyboardInterrupt:
        pass
    finally:
        files.save_path_sourced(deck)

def make_arg_parser() -> argparse.ArgumentParser:
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
    arg_parser.add_argument(
        '-R',
        '--max-to-review',
        dest='max_reviews',
        type=int,
        help="The maximum number of cards to review.",
    )
    arg_parser.add_argument(
        '-N',
        '--max-new',
        dest='max_new',
        type=int,
        help="The maximum number of new cards.",
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
        help="""
            Set a command to filter cards. It should take on stdin a sequence
            of card data lines consisting of path, card top, and card bottom,
            separated by tabs. It should output to stdout new card data in the
            same format, which will be shown instead of the original card data.
        """
    )
    arg_parser.add_argument(
        '-F',
        '--finish-filter',
        dest='ext_finish',
        type=_ExternalFilter,
        default=None,
        help="""
            Set a command to execute after a card's second field is shown. It
            should take cards on stdin in the same format as the command for
            -f. Its output is ignored.
        """
    )
    return arg_parser

def main() -> None:
    """
    Entry point.
    """

    args = make_arg_parser().parse_args()

    _review_deck(
        deck=tuple(files.load_path_sourced(args.input_paths)),
        now=args.now,
        max_reviews=args.max_reviews,
        max_new=args.max_new,
        randomize=args.randomize,
        batch_size=args.batch_size,
        ext_filter=args.ext_filter,
        ext_finish=args.ext_finish,
    )

if __name__ == "__main__":
    main()
