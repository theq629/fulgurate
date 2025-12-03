"""
Flashcard data and core operations.
"""

from typing import TypeVar, Optional, Generic, overload, cast
import datetime
import math

S = TypeVar('S')

_DEFAULT_REPETITIONS = 0
_DEFAULT_INTERVAL = 1
_DEFAULT_EASINESS = 2.5

class Card(Generic[S]):
    """
    Flash card.
    """

    @overload
    def __init__(
        self: "Card[None]",
        *,
        top: str,
        bottom: str,
        last_repeat_time: datetime.datetime,
        repetitions: int = _DEFAULT_REPETITIONS,
        interval: float = _DEFAULT_INTERVAL,
        easiness: float = _DEFAULT_EASINESS,
    ):
        ...

    @overload
    def __init__(
        self: "Card[S]",
        *,
        top: str,
        bottom: str,
        last_repeat_time: datetime.datetime,
        source: S,
        repetitions: int = _DEFAULT_REPETITIONS,
        interval: float = _DEFAULT_INTERVAL,
        easiness: float = _DEFAULT_EASINESS,
    ):
        ...

    def __init__(
        self,
        *,
        top: str,
        bottom: str,
        last_repeat_time: datetime.datetime,
        source: Optional[S] = None,
        repetitions: int = _DEFAULT_REPETITIONS,
        interval: float = _DEFAULT_INTERVAL,
        easiness: float = _DEFAULT_EASINESS,
    ):
        self._top = top
        self._bottom = bottom
        self._last_repeat_time = last_repeat_time.replace(second=0, microsecond=0)
        self._repetitions = repetitions
        self._interval = interval
        self._easiness = easiness
        self._source = cast(S, source)

    @property
    def top(self) -> str:
        return self._top

    @property
    def bottom(self) -> str:
        return self._bottom

    @property
    def last_repeat_time(self) -> datetime.datetime:
        return self._last_repeat_time

    @property
    def repetitions(self) -> int:
        return self._repetitions

    @property
    def interval(self) -> float:
        return self._interval

    @property
    def easiness(self) -> float:
        return self._easiness

    @property
    def source(self) -> S:
        return self._source

    @property
    def is_new(self) -> bool:
        """
        Is this a new card (ie has no repetitions).
        """
        return self.repetitions == 0

    @property
    def next_time(self) -> datetime.datetime:
        """
        The time this card is currently scheduled for.
        """
        return self._last_repeat_time + datetime.timedelta(days=math.ceil(self._interval))

    def repeat(self, quality: int, now: datetime.datetime) -> None:
        """
        Do a repeatition of this card using SM-2.
        """
        if not 0 <= quality <= 5:
            raise ValueError("quality must be in 0-5")
        self._easiness = max(
            1.3,
            self._easiness + 0.1 - (5.0 - quality) * (0.08 + (5.0 - quality) * 0.02)
        )
        if quality < 3:
            self._repetitions = 0
        else:
            self._repetitions += 1
        if self._repetitions == 1:
            self._interval = 1
        elif self._repetitions == 2:
            self._interval = 6
        elif self._repetitions > 2:
            self._interval *= self._easiness
        self._last_repeat_time = now
