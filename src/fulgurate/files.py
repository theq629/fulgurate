"""
Cards file IO.
"""

from typing import TypeVar, Any, Callable, Union, Optional, Iterable, TextIO, overload
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
    'save_path_sourced',
    'save_path_sourced',
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

S = TypeVar('S')

def _make_default_writer(out_file: TextIO) -> DictWriter:
    return csv.DictWriter(out_file, fieldnames=_FIELD_NAMES, dialect=_CSV_DIALECT)

def _make_default_reader(in_file: TextIO) -> DictReader:
    return csv.DictReader(in_file, fieldnames=_FIELD_NAMES, dialect=_CSV_DIALECT)

MakeWriter = Callable[[TextIO], DictWriter]
MakeReader = Callable[[TextIO], DictReader]

def write_cards(cards: Iterable[Card[S]], writer: DictWriter) -> None:
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

@overload
def read_cards(reader: DictReader) -> Iterable[Card[None]]: ...

@overload
def read_cards(reader: DictReader, *, source: S) -> Iterable[Card[S]]: ...

def read_cards(reader: DictReader, *, source: Optional[S] = None) -> Iterable[Card[Any]]:
    """
    Read cards from a `csv.DictReader`.
    """
    for row in reader:
        yield Card(
            top=row['top'],
            bottom=row['bottom'],
            source=source,
            last_repeat_time=datetime.datetime.strptime(row['last repeat time'], _TIME_FMT),
            repetitions=int(row['repetitions']),
            interval=float(row['interval']),
            easiness=float(row['easiness']),
        )

def save(
    cards: Iterable[Card[S]],
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

@overload
def load(
    in_file: TextIO,
    *,
    make_reader: Optional[MakeReader] = None,
) -> Iterable[Card[None]]:
    ...

@overload
def load(
    in_file: TextIO,
    *,
    source: S,
    make_reader: Optional[MakeReader] = None,
) -> Iterable[Card[S]]:
    ...

def load(
    in_file: TextIO,
    *,
    source: Optional[S] = None,
    make_reader: Optional[MakeReader] = None,
) -> Iterable[Card[Any]]:
    """
    Load cards from a file.
    """
    if make_reader is None:
        make_reader = _make_default_reader
    reader = make_reader(in_file)
    yield from read_cards(reader, source=source)

def save_path_sourced(
    cards: Iterable[Card[Path]],
    *,
    make_writer: Optional[MakeWriter] = None,
    encoding: str,
) -> None:
    """
    Given cards with the source field being a path, save them to their
    respective files.
    """
    outputs = {}
    with ExitStack() as file_stack:
        for card in cards:
            if card.source not in outputs:
                # pylint: disable=consider-using-with
                out_file = open(card.source, 'w', newline='', encoding=encoding)
                outputs[card.source] = file_stack.enter_context(out_file)
            save([card], outputs[card.source], make_writer=make_writer)

def load_path_sourced(
    paths: Iterable[Union[Path, str]],
    *,
    make_reader: Optional[MakeReader] = None,
    encoding: str,
) -> Iterable[Card[Path]]:
    """
    Load cards from multiple files, setting the source field for each card to
    be the path of the file it came from.
    """
    for path in paths:
        path = Path(path)
        with open(path, newline='', encoding=encoding) as in_file:
            yield from load(in_file, source=path, make_reader=make_reader)
