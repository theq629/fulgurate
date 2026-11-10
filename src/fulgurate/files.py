"""
Cards file IO.
"""

from typing import Callable, Union, Optional, Iterable, TextIO
from pathlib import Path
import sys
import datetime
import csv
from contextlib import ExitStack
from ._card import Card

if sys.version_info.major == 3 and sys.version_info.minor > 11:
    DictWriter = csv.DictWriter[str]
    DictReader = csv.DictReader[str]
else:
    DictWriter = csv.DictWriter # type: ignore
    DictReader = csv.DictReader # type: ignore

__all__ = (
    'MakeReader',
    'MakeWriter',
    'write_cards',
    'read_cards',
    'save',
    'load',
    'save_all',
    'load_all',
)

_TIME_FMT = "%Y-%m-%d"
_CSV_DIALECT = csv.excel_tab # pylint: disable=invalid-name
_FIELD_NAMES = (
    'last repeat time',
    'repetitions',
    'interval',
    'easiness',
    'top',
    'bottom',
)

def _make_default_writer(out_file: TextIO) -> DictWriter:
    return csv.DictWriter(out_file, fieldnames=_FIELD_NAMES, dialect=_CSV_DIALECT)

def _make_default_reader(in_file: TextIO) -> DictReader:
    return csv.DictReader(in_file, fieldnames=_FIELD_NAMES, dialect=_CSV_DIALECT)

MakeWriter = Callable[[TextIO], DictWriter]
MakeReader = Callable[[TextIO], DictReader]

def write_cards(cards: Iterable[Card], writer: DictWriter) -> None:
    """
    Write cards to a `csv.DictWriter`.
    """
    for card in cards:
        writer.writerow({
            'top': card.top,
            'bottom': card.bottom,
            'last repeat time': card.last_repeat_time.strftime(_TIME_FMT),
            'repetitions': card.repetitions,
            'interval': card.interval,
            'easiness': card.easiness,
        })

def read_cards(reader: DictReader) -> Iterable[Card]:
    """
    Read cards from a `csv.DictReader`.
    """
    for row_number, row in enumerate(reader, start=1):
        try:
            yield Card(
                top=row['top'],
                bottom=row['bottom'],
                last_repeat_time=datetime.datetime.strptime(row['last repeat time'], _TIME_FMT),
                repetitions=int(row['repetitions']),
                interval=float(row['interval']),
                easiness=float(row['easiness']),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError("Invalid card data on row %d: %s" % (row_number, e))

def save(
    cards: Iterable[Card],
    out_file: TextIO,
    *,
    make_writer: Optional[MakeWriter] = None,
) -> None:
    """
    Save cards to a file.
    """
    if make_writer is None:
        make_writer = _make_default_writer
    writer = make_writer(out_file)
    write_cards(cards, writer)

def load(in_file: TextIO, *, make_reader: Optional[MakeReader] = None) -> Iterable[Card]:
    """
    Load cards from a file.
    """
    if make_reader is None:
        make_reader = _make_default_reader
    reader = make_reader(in_file)
    yield from read_cards(reader)

def save_all(
    cards: Iterable[Card],
    *,
    make_writer: Optional[MakeWriter] = None,
    encoding: str = 'utf-8'
) -> None:
    """
    Given cards with the path field set, save them to their respectively files.
    """
    outputs = {}
    with ExitStack() as file_stack:
        for card in cards:
            if card.path is not None:
                if card.path not in outputs:
                    # pylint: disable=consider-using-with
                    out_file = open(card.path, 'w', newline='', encoding=encoding)
                    outputs[card.path] = file_stack.enter_context(out_file)
                save([card], outputs[card.path], make_writer=make_writer)

def load_all(
    paths: Iterable[Union[Path, str]],
    *,
    make_reader: Optional[MakeReader] = None,
    encoding: str = 'utf-8',
) -> Iterable[Card]:
    """
    Load cards from multiple files, with the path field set.
    """
    for path in paths:
        path = Path(path)
        with open(path, newline='', encoding=encoding) as in_file:
            for card in load(in_file, make_reader=make_reader):
                card.path = path
                yield card
