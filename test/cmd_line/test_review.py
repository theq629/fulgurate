from pathlib import Path
import sys
import io
import datetime
import csv
from contextlib import nullcontext
from unittest.mock import patch, Mock, ANY
import pytest
from fulgurate import Card, files, review
from fulgurate._cmd_line import review as cmd_line_review
from fulgurate._cmd_line.review import main, _ExternalFilter, _DEFAULT_CSV_DIALECT
from ._mock_ttyio import mock_ttyio
from ._shared import FixNowDatetime

_time_fmt = "%Y-%m-%d"
_cards_time = datetime.datetime(2022, 10, 18)

@pytest.fixture(scope='function')
def test_cards_path(tmpdir):
    cards_path = str(tmpdir / "cards")
    deck = [
        Card(top="a", bottom="b", last_repeat_time=_cards_time),
        Card(top="c", bottom="d", last_repeat_time=_cards_time),
        Card(top="e", bottom="f", last_repeat_time=_cards_time),
    ]
    with open(cards_path, 'w', encoding='utf-8') as out_file:
        files.save(deck, out_file)
    return cards_path

def _minimal_call(args, key_inputs=()):
    """Call that mocks out the whole of the review."""
    with patch.object(review, 'review_cards') as review_cards_mock, \
         mock_ttyio(key_inputs), \
         patch.object(sys, 'argv', [""] + list(args)):
        main()
    return review_cards_mock

class _DummySourcedDeck:
    def __init__(self, sources):
        self._sources = sources

    def get_source(self, card):
        return self._sources[id(card)]

    def save(self, _path, *, _encoding):
        return

class _ExternalFilterMock:
    def __init__(self, command):
        self.command = command

    def interact(self, dialect, _deck):
        return nullcontext((self.command, dialect))

def _minimal_real_call(args, key_inputs=()):
    """Call that does a real review but mocks interaction."""
    with patch.object(cmd_line_review, '_review_card', Mock(return_value=5)) as review_card_mock, \
         patch.object(cmd_line_review, '_ExternalFilter', _ExternalFilterMock), \
         mock_ttyio(key_inputs), \
         patch.object(sys, 'argv', [""] + list(args)):
        main()
    return review_card_mock

def _assert_review_cards_called_once_with(mock, *, cards=ANY, now=ANY, review_card=ANY,
                                          max_old=ANY, max_new=ANY, randomize=ANY):
    mock.assert_called_once_with(cards, now, review_card, max_old=max_old, max_new=max_new,
                                 randomize=randomize)

def _assert_batch_review_called_once_with(mock, *, cards=ANY, now=ANY, batch_size=ANY,
                                          show_batch=ANY, review_card=ANY, max_old=ANY,
                                          max_new=ANY, randomize=ANY, randomize_batch=ANY):
    mock.assert_called_once_with(cards, now, batch_size=batch_size, show_batch=show_batch,
                                 review_card=review_card, max_old=max_old, max_new=max_new,
                                 randomize=randomize, randomize_batch=randomize_batch)

def _assert_review_card_called_with(mock, card=ANY, deck=ANY, ext_filter_interacter=ANY,
                                    ext_finish_interacter=ANY):
    mock.assert_called_with(card, deck=deck, ext_filter_interacter=ext_filter_interacter,
                            ext_finish_interacter=ext_finish_interacter)

def test_review_basic(test_cards_path):
    set_time = _cards_time
    set_time_str = set_time.strftime(_time_fmt)
    with open(test_cards_path, encoding='utf-8') as in_file:
        deck = list(files.load(in_file))

    # Note: make sure we test both keys for quality 0
    key_inputs = ["x", "`"] * (len(deck) - 1) + ["x", "0"] + ["x", "1"] * len(deck) \
        + ["x", "2"] * len(deck) + ["y", "3", "y", "4", "y", "5"]
    out_file = io.StringIO()
    with mock_ttyio(key_inputs, "CLEAR"), \
         patch.object(sys, 'stdout', io.StringIO()) as out_file, \
         patch.object(sys, 'argv', ["", "-n", set_time_str, str(test_cards_path)]):
        main()

    output = list(zip(*([iter(out_file.getvalue().splitlines())] * 4)))
    assert len(output) == len(deck) * 4
    for (got_clear_line, got_cards_line, got_top, got_bot), want_card in zip(output, deck):
        assert got_clear_line == "CLEAR"
        assert got_cards_line == test_cards_path
        assert got_top == want_card.top
        assert got_bot == want_card.bottom
    with open(test_cards_path, encoding='utf-8') as in_file:
        new_deck = tuple(files.load(in_file))
        assert new_deck[0].easiness <= new_deck[1].easiness < new_deck[2].easiness \
            < min(c.easiness for c in deck)

def test_review_no_set_time(test_cards_path):
    now_time = _cards_time + datetime.timedelta(days=3)
    with patch.object(datetime, 'datetime', FixNowDatetime(now_time)):
        review_cards_mock = _minimal_call([str(test_cards_path)])
    _assert_review_cards_called_once_with(review_cards_mock, now=now_time)

def test_review_set_time(test_cards_path):
    set_time = _cards_time + datetime.timedelta(days=2)
    review_cards_mock = _minimal_call(["-n", set_time.strftime(_time_fmt), str(test_cards_path)])
    _assert_review_cards_called_once_with(review_cards_mock, now=set_time)

def test_review_set_max_reviews(test_cards_path):
    review_cards_mock = _minimal_call(["-O", "12", str(test_cards_path)])
    _assert_review_cards_called_once_with(review_cards_mock, max_old=12)

def test_review_set_max_new(test_cards_path):
    review_cards_mock = _minimal_call(["-N", "34", str(test_cards_path)])
    _assert_review_cards_called_once_with(review_cards_mock, max_new=34)

def test_review_set_randomize(test_cards_path):
    review_cards_mock = _minimal_call(["-r", str(test_cards_path)])
    _assert_review_cards_called_once_with(review_cards_mock, randomize=True)

def test_review_set_batch_size(test_cards_path):
    with patch.object(review, 'review_cards_batched') as batch_review_mock:
        _minimal_call(["-b", "56", str(test_cards_path)])
    _assert_batch_review_called_once_with(batch_review_mock, batch_size=56, randomize_batch=False)

def test_review_set_randomize_batch(test_cards_path):
    with patch.object(review, 'review_cards_batched') as batch_review_mock:
        _minimal_call(["-b", "56", "-R", str(test_cards_path)])
    _assert_batch_review_called_once_with(batch_review_mock, batch_size=56, randomize_batch=True)

def test_review_set_card_encoding(test_cards_path):
    deck = _DummySourcedDeck({})
    with patch.object(cmd_line_review, 'SourcedDeck', Mock(return_value=deck)) as load_mock, \
         patch.object(_DummySourcedDeck, 'save', Mock()) as save_mock:
        _minimal_call(["-e", "dummyencoding", str(test_cards_path)])
    load_mock.assert_called_once_with(ANY, encoding="dummyencoding")
    save_mock.assert_called_once_with(encoding="dummyencoding")

def test_external_filter(tmp_path):
    rev_path = Path(tmp_path) / "rev"
    with open(rev_path, 'w', encoding='utf-8') as out_file:
        print("import sys", file=out_file)
        print("for line in sys.stdin:", file=out_file)
        print("    print(''.join(reversed(line.strip())))", file=out_file)
        print("    sys.stdout.flush()", file=out_file)
    rev_csv_fields_path = Path(tmp_path) / "rev-csv-fields"
    with open(rev_csv_fields_path, 'w', encoding='utf-8') as out_file:
        print("import sys", file=out_file)
        print("for line in sys.stdin:", file=out_file)
        print("    print(','.join(reversed(line.strip().split(','))))", file=out_file)
        print("    sys.stdout.flush()", file=out_file)

    card0 = Card(top="abc", bottom="def", last_repeat_time=_cards_time)
    card1 = Card(top="efg", bottom="hij", last_repeat_time=_cards_time)
    deck = _DummySourcedDeck({
        id(card0): "file0",
        id(card1): "file1",
    })

    f = _ExternalFilter(f"{sys.executable} {rev_path}")
    with f.interact(csv.excel_tab, deck) as i:
        i.send_card(card0)
        i.send_card(card1)
        assert i.receive() == ("fed", "cba", "0elif")
        assert i.receive() == ("jih", "gfe", "1elif")

    assert _DEFAULT_CSV_DIALECT != 'excel', "need non-default to check dialect passing"
    f = _ExternalFilter(f"{sys.executable} {rev_csv_fields_path}")
    with f.interact(csv.excel, deck) as i:
        i.send_card(card0)
        i.send_card(card1)
        assert i.receive() == ("def", "abc", "file0")
        assert i.receive() == ("hij", "efg", "file1")

def test_review_ext_filter(test_cards_path):
    assert _DEFAULT_CSV_DIALECT != 'unix', "need non-default to check dialect passing"
    review_card_mock = _minimal_real_call(["-f", "abc", "-d", "unix", str(test_cards_path)])
    _assert_review_card_called_with(
        review_card_mock,
        ext_filter_interacter=('abc', 'unix'),
    )

def test_review_ext_finish(test_cards_path):
    assert _DEFAULT_CSV_DIALECT != 'unix', "need non-default to check dialect passing"
    review_card_mock = _minimal_real_call(["-F", "def", "-d", "unix", str(test_cards_path)])
    _assert_review_card_called_with(
        review_card_mock,
        ext_finish_interacter=('def', 'unix'),
    )
