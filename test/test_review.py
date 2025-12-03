import datetime
import random
from unittest.mock import patch
import pytest
from fulgurate import Card
from fulgurate.review import review_cards, review_cards_batched

_time = datetime.datetime(2022, 10, 18)
_day = datetime.timedelta(days=1)

def _make_review_tracker():
    got = []
    def make_review_card(*qualities):
        qualities = iter(qualities)
        def review_card(card):
            got.append(card)
            return next(qualities)
        return review_card
    return got, make_review_card

def test_review_cards_basic():
    def make_deck():
        return [
            Card(top="a", bottom="b", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="c", bottom="d", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="e", bottom="f", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="g", bottom="h", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="i", bottom="h", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="k", bottom="l", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.36),
            Card(top="m", bottom="n", last_repeat_time=_time, repetitions=2, interval=6.0,
                 easiness=2.22),
        ]

    got_reviews, make_review_card = _make_review_tracker()

    del got_reviews[:]
    deck = make_deck()
    review_cards(deck, _time, make_review_card(5, 5, 5, 5, 5))
    assert len(got_reviews) == 5
    assert [c.repetitions for c in deck] == [1, 1, 1, 1, 1, 1, 2]
    assert [c.top for c in got_reviews] == ["a", "c", "e", "g", "i"]

    del got_reviews[:]
    deck = make_deck()
    review_cards(deck, _time, make_review_card(4, 0, 3, 1, 2, 5, 5, 1, 5))
    assert len(got_reviews) == 9
    assert [c.repetitions for c in deck] == [1, 1, 1, 1, 1, 1, 2]
    assert [c.top for c in got_reviews] == ["a", "c", "e", "g", "i", "c", "g", "i", "i"]
    review_cards(deck, _time + _day, make_review_card(5, 5, 5, 5, 5, 5))
    assert len(got_reviews) == 15
    assert [c.repetitions for c in deck] == [2, 2, 2, 2, 2, 2, 2]
    assert [c.top for c in got_reviews] == ["a", "c", "e", "g", "i", "c", "g", "i", "i", "a", "c",
                                            "e", "g", "i", "k"]

def test_review_cards_max_reviews():
    deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=2, interval=6.0,
             easiness=2.22),
    ]

    got_reviews, make_review_card = _make_review_tracker()

    del got_reviews[:]
    review_cards(deck, _time + _day, make_review_card(4, 5), max_reviews=0)
    assert len(got_reviews) == 0
    assert [c.repetitions for c in deck] == [1, 1, 2]

    del got_reviews[:]
    review_cards(deck, _time + _day, make_review_card(4, 5), max_reviews=1)
    assert len(got_reviews) == 1
    assert [c.repetitions for c in deck] == [2, 1, 2]

def test_review_cards_max_new():
    deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=0, interval=1.0,
             easiness=2.5),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=0, interval=1.0,
             easiness=2.5),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
    ]

    got_reviews, make_review_card = _make_review_tracker()

    del got_reviews[:]
    review_cards(deck, _time + _day, make_review_card(4, 5, 5), max_new=0)
    assert len(got_reviews) == 1
    assert [c.repetitions for c in deck] == [0, 0, 2]

    del got_reviews[:]
    review_cards(deck, _time + _day, make_review_card(4, 5, 5), max_new=1)
    assert len(got_reviews) == 1
    assert [c.repetitions for c in deck] == [1, 0, 2]

def test_review_cards_randomize():
    rng = random.Random(0)

    def make_deck():
        return [
            Card(top="a", bottom="b", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="e", bottom="f", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="g", bottom="h", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="i", bottom="j", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
        ]

    got_reviews, make_review_card = _make_review_tracker()

    with patch.object(random, 'shuffle', rng.shuffle):
        del got_reviews[:]
        deck = make_deck()
        review_cards(deck, _time + _day, make_review_card(3, 4, 5, 3, 4), randomize=True)
        got0 = [(c.top, c.bottom) for c in got_reviews]
        del got_reviews[:]
        deck = make_deck()
        review_cards(deck, _time + _day, make_review_card(3, 4, 5, 3, 4), randomize=True)
        got1 = [(c.top, c.bottom) for c in got_reviews]
        assert len(got0) > 0
        assert got0 != got1

def test_review_cards_review_failure():
    """
    Should cleanly handle failures during review_card().
    """

    deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=2, interval=6.0,
             easiness=2.22),
    ]

    got_reviews, make_review_card = _make_review_tracker()

    del got_reviews[:]
    with pytest.raises(ValueError, match=".*quality.*"):
        review_cards(deck, _time + _day, make_review_card(4, -1))
    assert len(got_reviews) == 2
    assert [c.repetitions for c in deck] == [2, 1, 2]

def test_batch_review_basic():
    def make_deck():
        return [
            Card(top="a", bottom="b", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="c", bottom="d", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="e", bottom="f", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="g", bottom="h", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="i", bottom="h", last_repeat_time=_time, repetitions=0, interval=1.0,
                 easiness=2.5),
            Card(top="k", bottom="l", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.36),
            Card(top="m", bottom="n", last_repeat_time=_time, repetitions=2, interval=6.0,
                 easiness=2.22),
        ]

    got_reviews, make_review_card = _make_review_tracker()
    got_batches = []
    def show_batch(batch):
        got_batches.append(batch)

    del got_reviews[:], got_batches[:]
    deck = make_deck()
    review_cards_batched(
        deck,
        _time,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(5, 5, 5, 5, 5)
    )
    assert len(got_reviews) == 5
    assert [len(b) for b in got_batches] == [2, 2, 1]
    assert [c.repetitions for c in deck] == [1, 1, 1, 1, 1, 1, 2]
    assert [c.top for c in got_reviews] == ["a", "c", "e", "g", "i"]

    del got_reviews[:], got_batches[:]
    deck = make_deck()
    review_cards_batched(
        deck,
        _time,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(4, 0, 3, 1, 2, 5, 5, 1, 5),
    )
    assert len(got_reviews) == 9
    assert [len(b) for b in got_batches] == [2, 2, 2, 2, 1]
    assert [c.repetitions for c in deck] == [1, 1, 1, 1, 1, 1, 2]
    assert [c.top for c in got_reviews] == ["a", "c", "c", "e", "e", "g", "e", "i", "i"]
    del got_reviews[:], got_batches[:]
    review_cards_batched(
        deck,
        _time + _day,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(5, 5, 5, 5, 5, 5),
    )
    assert len(got_reviews) == 6
    assert [len(b) for b in got_batches] == [2, 2, 2]
    assert [c.repetitions for c in deck] == [2, 2, 2, 2, 2, 2, 2]
    assert [c.top for c in got_reviews] == ["a", "c", "e", "g", "i", "k"]

def test_batch_review_max_reviews():
    deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=2, interval=6.0,
             easiness=2.22),
    ]

    got_reviews, make_review_card = _make_review_tracker()
    def show_batch(_batch):
        pass

    del got_reviews[:]
    review_cards_batched(
        deck,
        _time + _day,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(4, 5),
        max_reviews=0,
    )
    assert len(got_reviews) == 0
    assert [c.repetitions for c in deck] == [1, 1, 2]

    del got_reviews[:]
    review_cards_batched(
        deck,
        _time + _day,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(4, 5),
        max_reviews=1,
    )
    assert len(got_reviews) == 1
    assert [c.repetitions for c in deck] == [2, 1, 2]

def test_batch_review_max_new():
    deck = [
        Card(top="a", bottom="b", last_repeat_time=_time, repetitions=0, interval=1.0,
             easiness=2.5),
        Card(top="c", bottom="d", last_repeat_time=_time, repetitions=0, interval=1.0,
             easiness=2.5),
        Card(top="e", bottom="f", last_repeat_time=_time, repetitions=1, interval=1.0,
             easiness=2.36),
    ]

    got_reviews, make_review_card = _make_review_tracker()
    def show_batch(_batch):
        pass

    del got_reviews[:]
    review_cards_batched(
        deck,
        _time + _day,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(4, 5, 5),
        max_new=0,
    )
    assert len(got_reviews) == 1
    assert [c.repetitions for c in deck] == [0, 0, 2]

    del got_reviews[:]
    review_cards_batched(
        deck,
        _time + _day,
        batch_size=2,
        show_batch=show_batch,
        review_card=make_review_card(4, 5, 5),
        max_new=1,
    )
    assert len(got_reviews) == 1
    assert [c.repetitions for c in deck] == [1, 0, 2]

def test_batch_review_randomize():
    rng = random.Random(0)

    def make_deck():
        return [
            Card(top="a", bottom="b", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="e", bottom="f", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="g", bottom="h", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="i", bottom="j", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
        ]

    qualities = (3, 4, 5, 3, 4)

    got_reviews, make_review_card = _make_review_tracker()
    def show_batch(_batch):
        pass

    with patch.object(random, 'shuffle', rng.shuffle):
        del got_reviews[:]
        deck = make_deck()
        review_cards_batched(
            deck,
            _time + _day,
            batch_size=2,
            show_batch=show_batch,
            review_card=make_review_card(*qualities),
            randomize=True,
            randomize_batch=False,
        )
        got0 = [(c.top, c.bottom) for c in got_reviews]
        del got_reviews[:]
        deck = make_deck()
        review_cards_batched(
            deck,
            _time + _day,
            batch_size=2,
            show_batch=show_batch,
            review_card=make_review_card(*qualities),
            randomize=True,
            randomize_batch=False,
        )
        got1 = [(c.top, c.bottom) for c in got_reviews]
        assert len(got0) > 0
        assert len(got1) > 0
        assert got0 != got1

def test_batch_review_randomize_batch():
    rng = random.Random(4)

    def make_deck():
        return [
            Card(top="a", bottom="b", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="c", bottom="d", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
            Card(top="i", bottom="j", last_repeat_time=_time, repetitions=1, interval=1.0,
                 easiness=2.5),
        ]

    qualities = (3, 4, 5, 3, 4)

    _got_reviews, make_review_card = _make_review_tracker()
    got_batches = []
    def show_batch(batch):
        got_batches.append(batch)

    with patch.object(random, 'shuffle', rng.shuffle):
        del got_batches[:]
        deck = make_deck()
        review_cards_batched(
            deck,
            _time + _day,
            batch_size=2,
            show_batch=show_batch,
            review_card=make_review_card(*qualities),
            randomize_batch=True,
        )
        got0 = [[(c.top, c.bottom) for c in b] for b in got_batches]
        del got_batches[:]
        deck = make_deck()
        review_cards_batched(
            deck,
            _time + _day,
            batch_size=2,
            show_batch=show_batch,
            review_card=make_review_card(*qualities),
            randomize_batch=True,
        )
        got1 = [[(c.top, c.bottom) for c in b] for b in got_batches]
        assert len(got0) > 0
        assert len(got1) > 0
        assert got0 != got1
