import builtins
import sys
import os.path
import datetime
from unittest.mock import patch, Mock, ANY, call
import pytest
from fulgurate import files
from fulgurate._cmd_line import import_cards as cmd_line_import_cards
from fulgurate._cmd_line.import_cards import main, _load_data
from ._shared import FixNowDatetime

_time_fmt = "%Y-%m-%d"
_example_path = os.path.join(os.path.dirname(__file__), "..", "..", "example.tsv")

def _load_raw_cards(in_file):
    next(in_file, None) # skip header
    for line in in_file:
        parts = tuple(line.strip().split('\t'))
        assert len(parts) == 2
        yield parts

def _save_raw_cards_tsv(rows, out_file):
    for row in rows:
        print("\t".join(row), file=out_file)

def _save_raw_cards_csv(rows, out_file):
    for row in rows:
        print(",".join(row), file=out_file)

def _call(args):
    with patch.object(sys, 'argv', [""] + list(args)):
        main()

def _minimal_call(args):
    with patch.object(files, 'save') as save_mock, \
         patch.object(sys, 'argv', [""] + list(args)):
        main()
    return save_mock

def test_load_data_tsv(tmpdir):
    cards_path = str(tmpdir / "cards")
    with open(_example_path, encoding='utf-8') as in_file, \
         open(cards_path, 'w', encoding='utf-8') as out_file:
        input_data = tuple(_load_raw_cards(in_file))
        _save_raw_cards_tsv(input_data, out_file)

    with open(cards_path, encoding='utf-8') as in_file:
        got_data = tuple(_load_data(in_file, dialect='sniff-tsv', read_header=False))
    assert tuple((r['top'], r['bottom']) for r in got_data) == input_data

def test_load_data_csv(tmpdir):
    cards_path = str(tmpdir / "cards")
    with open(_example_path, encoding='utf-8') as in_file, \
         open(cards_path, 'w', encoding='utf-8') as out_file:
        input_data = tuple(_load_raw_cards(in_file))
        _save_raw_cards_csv(input_data, out_file)

    with open(cards_path, encoding='utf-8') as in_file:
        got_data = tuple(_load_data(in_file, dialect='sniff-csv', read_header=False))
    assert tuple((r['top'], r['bottom']) for r in got_data) == input_data

def test_load_data_read_header(tmpdir):
    cards_path = str(tmpdir / "cards")
    with open(_example_path, encoding='utf-8') as in_file, \
         open(cards_path, 'w', encoding='utf-8') as out_file:
        input_data = tuple(_load_raw_cards(in_file))
        print("bottom\ttop", file=out_file)
        _save_raw_cards_tsv(((b, t) for t, b in input_data), out_file)

    with open(cards_path, encoding='utf-8') as in_file:
        got_data = tuple(_load_data(in_file, dialect='sniff-tsv', read_header=True))
    assert tuple((r['top'], r['bottom']) for r in got_data) == input_data

def test_load_data_read_header_unknown(tmpdir):
    cards_path = str(tmpdir / "cards")
    with open(cards_path, 'w', encoding='utf-8') as out_file:
        print("top\tx", file=out_file)

    with open(cards_path, encoding='utf-8') as in_file:
        with pytest.raises(ValueError, match=r"unknown.*field name"):
            tuple(_load_data(in_file, dialect='sniff-tsv', read_header=True))

def test_basic(tmpdir):
    cards_path = str(tmpdir / "cards")
    with open(_example_path, encoding='utf-8') as in_file:
        input_data = tuple(_load_raw_cards(in_file))

    with patch.object(sys, 'argv', ["", _example_path, cards_path]):
        main()

    with open(cards_path, encoding='utf-8') as in_file:
        deck = tuple(files.load(in_file))
    assert len(deck) == len(input_data)
    assert all(c.top == t and c.bottom == b for c, (t, b) in zip(deck, input_data))
    assert all(c.is_new for c in deck)
    assert all(c.repetitions == 0 for c in deck)

def test_no_set_time(tmpdir):
    now_time = datetime.datetime(2021, 12, 24)
    cards_path = str(tmpdir / "cards")
    with patch.object(datetime, 'datetime', FixNowDatetime(now_time)):
        save_mock = _minimal_call([str(_example_path), str(cards_path)])
    assert all(c.last_repeat_time == now_time for c in save_mock.call_args[1])

def test_set_time(tmpdir):
    cards_path = str(tmpdir / "cards")
    set_time = datetime.datetime(2022, 10, 18)
    save_mock = _minimal_call([
        "-n", set_time.strftime(_time_fmt),
        str(_example_path),
        str(cards_path),
    ])
    assert all(c.last_repeat_time == set_time for c in save_mock.call_args[1])

def test_set_dialect(tmpdir):
    cards_path = str(tmpdir / "cards")

    with patch.object(cmd_line_import_cards, '_load_data', Mock(return_value=[])) as load_data_mock:
        _minimal_call([str(_example_path), str(cards_path), "-d", "excel"])
    load_data_mock.assert_called_with(ANY, dialect="excel", read_header=ANY)

    with patch.object(cmd_line_import_cards, '_load_data', Mock(return_value=[])) as load_data_mock:
        _minimal_call([str(_example_path), str(cards_path), "-d", "excel-tab"])
    load_data_mock.assert_called_with(ANY, dialect="excel-tab", read_header=ANY)

def test_set_dialect_unknown(tmpdir):
    cards_path = str(tmpdir / "cards")
    with pytest.raises(SystemExit):
        _minimal_call([str(_example_path), str(cards_path), "-d", "x"])

def test_set_read_headers(tmpdir):
    cards_path = str(tmpdir / "cards")

    with patch.object(cmd_line_import_cards, '_load_data', Mock(return_value=[])) as load_data_mock:
        _minimal_call([str(_example_path), str(cards_path)])
    load_data_mock.assert_called_with(ANY, dialect=ANY, read_header=True)

    with patch.object(cmd_line_import_cards, '_load_data', Mock(return_value=[])) as load_data_mock:
        _minimal_call([str(_example_path), str(cards_path), "-H"])
    load_data_mock.assert_called_with(ANY, dialect=ANY, read_header=False)

def test_review_set_card_encoding(tmpdir):
    cards_path = str(tmpdir / "cards")

    # Need existing card file for load call
    _call([str(_example_path), str(cards_path)])

    builtins_open = builtins.open
    def wrap_open(path, mode='r', **_kwargs):
        return builtins_open(path, mode, encoding='utf-8')

    with patch.object(files, 'load_path_sourced', Mock(return_value=[])) as load_mock, \
        patch.object(builtins, 'open', Mock(wraps=wrap_open)) as open_mock:
        _call([str(_example_path), str(cards_path), "-e", "dummyencoding"])
    load_mock.assert_called_once_with(ANY, encoding="dummyencoding")
    open_mock.assert_has_calls([
        call(ANY, ANY, encoding=ANY),
        call(ANY, ANY, encoding="dummyencoding"),
    ])

def test_review_set_input_encoding(tmpdir):
    cards_path = str(tmpdir / "cards")

    _call([str(_example_path), str(cards_path)])

    builtins_open = builtins.open
    def wrap_open(path, mode='r', **_kwargs):
        return builtins_open(path, mode, encoding='utf-8')

    with patch.object(builtins, 'open', Mock(wraps=wrap_open)) as open_mock:
        _call([str(_example_path), str(cards_path), "-E", "dummyencoding"])
    open_mock.assert_has_calls([
        call(ANY, ANY, encoding="dummyencoding"),
        call(ANY, ANY, encoding=ANY),
    ])

def test_allow_existing(tmpdir):
    cards_path = str(tmpdir / "cards")

    # Make initial file with modified card data like reviews have been done on it
    _call([str(_example_path), str(cards_path)])
    with open(cards_path, 'r', encoding='utf-8') as in_file:
        text = in_file.read()
    with open(cards_path, 'w', encoding='utf-8') as out_file:
        mod_text = text.replace("2.5", "10.0")
        assert mod_text != text, "need to change something to get a valid test"
        out_file.write(mod_text)
    with open(cards_path, 'r', encoding='utf-8') as in_file:
        orig_lines = tuple(in_file)

    # Importing without allow existing should not change file
    _call([str(_example_path), str(cards_path)])
    with open(cards_path, 'r', encoding='utf-8') as in_file:
        new_lines = tuple(in_file)
    assert new_lines == orig_lines

    # Importing with allow existing should double the cards
    _call([str(_example_path), str(cards_path), "-a"])
    with open(cards_path, 'r', encoding='utf-8') as in_file:
        new_lines = tuple(in_file)
    assert new_lines != orig_lines
    assert len(new_lines) == len(orig_lines) * 2
