import sys
import io
import datetime
from unittest.mock import patch
import pytest
import tabulate
from fulgurate import Card, files
from fulgurate._cmd_line.show_schedule import main, _make_schedule
from ._shared import FixNowDatetime

_time_fmt = "%Y-%m-%d"
_cards_time = datetime.datetime(2022, 10, 18)

class _DummyCard:
    def __init__(self, is_new, next_time):
        self.is_new = is_new
        self.next_time = next_time

@pytest.fixture(scope='function')
def test_cards_path(tmpdir):
    cards_path = str(tmpdir / "cards")
    deck = [
        Card(top="a", bottom="b", last_repeat_time=_cards_time),
        Card(top="c", bottom="d", last_repeat_time=_cards_time),
        Card(top="e", bottom="f", last_repeat_time=_cards_time),
    ]
    deck[0].repeat(5, _cards_time)
    with open(cards_path, 'w', encoding='utf-8') as out_file:
        files.save(deck, out_file)
    return cards_path

def test_make_schedule():
    now = datetime.datetime(2022, 10, 18)
    cards = [
        _DummyCard(is_new=True, next_time=datetime.datetime(2022, 10, 19)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 19)),
        _DummyCard(is_new=True, next_time=datetime.datetime(2022, 10, 18)),
        _DummyCard(is_new=True, next_time=datetime.datetime(2022, 10, 20)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 19)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 20)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 21)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 18)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 19)),
        _DummyCard(is_new=False, next_time=datetime.datetime(2022, 10, 20)),
    ]
    assert list(_make_schedule(cards, now)) == [
        (now, -1, 3),
        (datetime.datetime(2022, 10, 18), 0, 1),
        (datetime.datetime(2022, 10, 19), 1, 3),
        (datetime.datetime(2022, 10, 20), 2, 2),
        (datetime.datetime(2022, 10, 21), 3, 1),
    ]

def test_tabulate(test_cards_path):
    with patch.object(sys, 'argv', ["", str(test_cards_path)]), \
         patch.object(tabulate, 'tabulate') as tabulate_mock:
        main()
    tabulate_mock.assert_called()

def test_set_time_shortly_after(test_cards_path):
    set_time = _cards_time + datetime.timedelta(hours=2)
    set_time_str = set_time.strftime(_time_fmt)
    card_time_day_later_str = (_cards_time + datetime.timedelta(days=1)).strftime(_time_fmt)
    with open(test_cards_path, encoding='utf-8') as in_file:
        num_cards = len(list(files.load(in_file)))

    with patch.object(sys, 'stdout', io.StringIO()) as output, \
         patch.object(sys, 'argv', ["", "-n", set_time_str, str(test_cards_path), "-s"]):
        main()

    assert output.getvalue().splitlines() == [
        f"{set_time_str} {-1} {num_cards - 1}",
        f"{card_time_day_later_str} {1} {1}",
    ]

def test_no_set_time_layer(test_cards_path):
    now_time = _cards_time + datetime.timedelta(days=3)
    now_time_str = now_time.strftime(_time_fmt)
    card_time_day_later_str = (_cards_time + datetime.timedelta(days=1)).strftime(_time_fmt)
    with open(test_cards_path, encoding='utf-8') as in_file:
        num_cards = len(list(files.load(in_file)))

    with patch.object(datetime, 'datetime', FixNowDatetime(now_time)), \
         patch.object(sys, 'stdout', io.StringIO()) as output, \
         patch.object(sys, 'argv', ["", str(test_cards_path), "-s"]):
        main()

    assert output.getvalue().splitlines() == [
        f"{now_time_str} {-1} {num_cards - 1}",
        f"{card_time_day_later_str} {-2} {1}",
    ]
