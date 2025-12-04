"""
Cards file IO.
"""

from typing import Callable, Union, Optional, Iterable, Iterator, TextIO
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
    'SourcedDeck',
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
    for row in reader:
        yield Card(
            top=row['top'],
            bottom=row['bottom'],
            last_repeat_time=datetime.datetime.strptime(row['last repeat time'], _TIME_FMT),
            repetitions=int(row['repetitions']),
            interval=float(row['interval']),
            easiness=float(row['easiness']),
        )

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

def load(
    in_file: TextIO,
    *,
    make_reader: Optional[MakeReader] = None,
) -> Iterable[Card]:
    """
    Load cards from a file.
    """
    if make_reader is None:
        make_reader = _make_default_reader
    reader = make_reader(in_file)
    yield from read_cards(reader)

class SourcedDeck:
    """
    Loads and stores cards from multiple files, tracking the source file path
    for each card.
    """
    def __init__(
        self,
        paths: Iterable[Union[Path, str]],
        *,
        make_reader: Optional[MakeReader] = None,
        encoding: str,
    ) -> None:
        def load_path(path: Union[Path, str]) -> Iterable[tuple[Path, Card]]:
            path = Path(path)
            with open(path, newline='', encoding=encoding) as in_file:
                for card in load(in_file, make_reader=make_reader):
                    yield path, card
        cards = tuple((p, c) for p in paths for p, c in load_path(p))
        self._cards = tuple(c for _, c in cards)
        self._sources = {id(c):p for p, c in cards}

    def save(
        self,
        *,
        make_writer: Optional[MakeWriter] = None,
        encoding: str,
    ) -> None:
        """
        Save cards bach to their respective source files.
        """
        outputs = {}
        with ExitStack() as file_stack:
            for card in self._cards:
                source = self._sources[id(card)]
                if source not in outputs:
                    # pylint: disable=consider-using-with
                    out_file = open(source, 'w', newline='', encoding=encoding)
                    outputs[source] = file_stack.enter_context(out_file)
                save([card], outputs[source], make_writer=make_writer)

    def get_source(self, card: Card) -> Path:
        return self._sources[id(card)]

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards)
