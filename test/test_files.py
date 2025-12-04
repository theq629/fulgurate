from pathlib import Path
import datetime
import pytest
from fulgurate import Card, files

_time = datetime.datetime(2022, 10, 18)

def _check_decks_equal(input_deck, output_deck):
    assert len(output_deck) == len(input_deck)
    for got_card, want_card in zip(output_deck, input_deck):
        assert got_card.top == want_card.top
        assert got_card.bottom == want_card.bottom
        assert got_card.last_repeat_time == want_card.last_repeat_time
        assert got_card.repetitions == want_card.repetitions
        assert got_card.interval == want_card.interval
        assert got_card.easiness == want_card.easiness
        assert got_card.is_new == want_card.is_new

def test_save_set_writer(tmpdir):
    cards_path = str(tmpdir / "cards")
    made = []
    with open(cards_path, 'w', encoding='utf-8') as out_file:
        def make_writer(f):
            assert f == out_file
            made.append(None)
        files.save([], out_file, make_writer=make_writer)
        assert made

def test_load_set_reader(tmpdir):
    cards_path = str(tmpdir / "cards")
    with open(cards_path, 'w', encoding='utf-8'):
        pass
    made = []
    with open(cards_path, encoding='utf-8') as in_file:
        def make_reader(f):
            assert f == in_file
            made.append(None)
            return []
        list(files.load(in_file, make_reader=make_reader))
        assert made

def test_save_load(tmpdir):
    cards_path = str(tmpdir / "cards")

    input_deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=0, interval=1.0,
             easiness=2.5),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=2, interval=6.0,
             easiness=2.22),
    ]

    with open(cards_path, 'w', encoding='utf-8') as out_file:
        files.save(input_deck, out_file)
    with open(cards_path, encoding='utf-8') as in_file:
        output_deck = tuple(files.load(in_file))

    _check_decks_equal(input_deck, output_deck)

def test_load_error(tmpdir):
    tsv_path = str(tmpdir / "cards")

    with open(tsv_path, 'w', encoding='utf-8') as out_file:
        print("\t".join(["a", "b", "c"]), file=out_file)

    with open(tsv_path, encoding='utf-8') as in_file:
        with pytest.raises(Exception):
            tuple(files.load(in_file))

def test_save_path_sourced_load_path_sourced(tmpdir):
    cards_path0 = str(tmpdir / "cards0")
    cards_path1 = str(tmpdir / "cards1")

    input_deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=0, interval=1.0,
             easiness=2.5),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=2, interval=6.0,
             easiness=2.22),
    ]
    input_deck[0]._source = Path(cards_path0)
    input_deck[1]._source = Path(cards_path1)
    input_deck[2]._source = Path(cards_path0)

    files.save_path_sourced(input_deck, encoding='utf-8')
    output_deck = list(files.load_path_sourced([cards_path0, cards_path1], encoding='utf-8'))

    output_deck.sort(key=lambda c: c.top)
    _check_decks_equal(input_deck, output_deck)
