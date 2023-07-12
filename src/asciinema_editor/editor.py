from __future__ import annotations

import copy
import json
import random
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Iterator


__all__ = ["Colors", "Record", "Recording", "generate_prompt", "wait", "end", "type_text"]


class Colors:
    """Short hands for ASCII sequences to set colours"""
    sep = "|"
    gry = "\033[2m"
    bld = "\033[1m"
    blu = "\033[1;34m"
    grn = "\033[1;32m"
    ylw = "\033[1;33m"
    red = "\033[1;31m"
    rst = "\033[0m"


sub_rules = {"\n": "\\n", "\r": "\\r", "\t": "\\t", "\u001b": "\\u001b"}
"""Substitution rules for ASCII special characters. Use JSON load instead?"""


@dataclass
class Record:
    """A single record (line) of a asciinema .cast file. Holds the time stamp,
    second column (probably the output stream?) and the text with special
    characters in ASCII representation (see sub_rules)."""

    time: float
    """The time stamp."""
    text: str
    """The text associated with the time stamp."""
    terminal: str = field(default="o")
    """The output stream the text was written to."""

    def __lt__(self, other: Record) -> bool:
        return self.time < other.time

    @classmethod
    def from_line(cls, line: str) -> Record:
        """Build an instance from a line of a .cast file."""
        # parse the data
        content = line[1:-2]
        time_stamp, term, text = content.split(", ", 2)
        # parse the text
        text = text[1:-1]
        for _to, _from in sub_rules.items():
            text = text.replace(_from, _to)
        # compute the time delta
        t = float(time_stamp)
        return cls(t, text, terminal=term.strip('"'))

    def to_line(self) -> str:
        """Build a string that can be written to a .cast file, includes a
        trailing new line character."""
        text = self.text
        for _from, _to in sub_rules.items():
            text = text.replace(_from, _to)
        return f'[{self.time:.6f}, "{self.terminal}", "{text}"]\n'

    def copy(self) -> Record:
        """Make a copy of the instance"""
        return copy.copy(self)


@dataclass(repr=False, eq=False)
class Recording(Sequence):
    """A asciinema recording. A sequence of strings with an attached time stamp
    that indicates when the string appears in the output stream. Represented as
    a list of Records and a header. Recordings can be concatenated with the
    .append method or by inplace addition (+=)."""

    header: dict[str, str]
    """Header information from asciinema."""
    records: list[Record]
    """A list of Records with time stamps and strings."""
    start: float = field(default=0.0)
    """The start time, defaults to 0.0, must be positive."""

    def __post_init__(self) -> None:
        self._check_bounds(self.start, self.end)

    @staticmethod
    def _check_bounds(start: float, end: float) -> None:
        """Check that start and end times are positive."""
        if start < 0.0:
            raise ValueError(f"start={start} < 0.0")
        if end < 0.0:
            raise ValueError(f"end={end} < 0.0")
        if start > end:
            raise ValueError(f"start={start} > end={end}")

    @classmethod
    def empty_from(cls, recordig: Recording, start: float = 0.0) -> Recording:
        """Create an empty recording using the header from a different
        recording."""
        return cls(recordig.header, [], start)

    @classmethod
    def from_file(cls, path: str) -> Recording:
        """Construct a new Recording instance from a asciinema .cast file."""
        with open(path) as f:
            lines = f.readlines()
        header = json.loads(lines[0])
        records = [Record.from_line(line) for line in lines[1:]]
        return cls(header=header, records=records)

    @classmethod
    def from_record(cls, record: Record, duration: float = 0.0) -> Recording:
        """Create a Recording from a single Record with a given duration. The
        Record will be rendered after the given duration has passed."""
        rec = Record(duration, record.text, record.terminal)
        return cls(dict(), [rec], start=0.0)

    def __repr__(self) -> str:
        string = self.__class__.__name__
        n_records = len(self)
        start = self.start
        end = self.end
        duration = self.duration
        string += f"({n_records=}, {start=}, {end=}, {duration=})"
        return string

    def __contains__(self, record: Record) -> bool:
        return record in self.records

    def __iter__(self) -> Iterator[Record]:
        return iter(self.records)

    def __reversed__(self) -> Iterator:
        return reversed(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, item) -> Record:
        return self.records[item]

    def __radd__(self, recording: Recording) -> Recording:
        self.append(recording)

    @property
    def end(self) -> float:
        """The end time of the Recording, relative to an absolute time=0.0."""
        return self.records[-1].time
    
    @property
    def duration(self) -> float:
        """The duration of the Recording"""
        return self.end - self.start

    def copy(self) -> Recording:
        """Create a copy of the instance"""
        new = Recording(
            copy.copy(self.header), [rec.copy() for rec in self.records],
            start=self.start
        )
        return new

    def replace(self, phrase: str, substitute: str) -> Recording:
        """Run a simple string replace on all stored records."""
        new = self.copy()
        for record in new:
            record.text = record.text.replace(phrase, substitute)
        return new

    def apply_offset(self, offset: float) -> None:
        """Apply an offset to all time stamps. The starting time must be remain
        >=0.0."""
        start = self.start + offset
        self._check_bounds(start, self.end + offset)
        # apply offset
        self.start = start
        for record in self.records:
            record.time += offset

    def trim(self) -> None:
        """Remove any time offset, i.e. display the first Record with no delay.
        """
        self.apply_offset(-self.start)

    def split_before(self, record_index: int) -> tuple[Recording, Recording]:
        """Split the recording into two new recordings before the given index in
        the list of records, i.e. valid values for loc are 0...len(recording).
        """
        a = Recording(self.header, self.records[:record_index], self.start)
        b = Recording(self.header, self.records[record_index:], a.end)
        return a, b

    def append(self, recording: Recording) -> None:
        """Append another recording to the end of this one."""
        recording = recording.copy()
        recording.apply_offset(self.end)
        self.records.extend(recording.records)

    def format(self) -> str:
        """Render the recording instantly into a single string."""
        string = ""
        for record in self.records:
            string += record.text
        return string

    def replay(self, speed=1.0):
        """Replay the recording to standard output at a given speed, defaults to
        real time playback."""
        try:
            t_last = 0.0
            for record in self.records:
                t_delta = record.time - t_last
                time.sleep(t_delta / speed)
                if record.terminal == "o":
                    _file = sys.stdout
                else:
                    _file = sys.stderr
                _file.write(record.text)
                _file.flush()
                t_last = record.time
        except KeyboardInterrupt:
            print("\n", end="\r")
            exit()

    def write(self, path: str) -> None:
        """Write a new asciinema-compatible .cast file."""
        with open(path, "w") as f:
            f.write(json.dumps(self.header) + "\n")
            for record in self.records:
                f.write(record.to_line())


def generate_prompt(
    user: str, machine: str, *, dir: str = "~", prompt: str = " $ ",
    env: str | None = None, c1: str = Colors.red, c2: str = Colors.blu,
    duration: float = 0.0,
) -> Recording:
    """Generate a commandline prompt '(env) user@machine [dir][prompt]', with
    the default style 'user@machine ~ $ ', coloured red and blue.
    """
    rst = Colors.rst
    string = f"{c1}{user}@{machine}{rst} {c2}{dir}{prompt}{rst}"
    if env is not None:
        string = f"({env}) {string}"
    return Recording.from_record(Record(0.0, string), duration)


def wait(duration) -> Recording:
    """Wait for a given period."""
    return Recording.from_record(Record(0, ""), duration)


def end(wait) -> Recording:
    """Produce an "end-frame" after a given time."""
    return Recording.from_record(Record(0, "\r\r\n"), wait)


def type_text(text: str, speed: float = 0.04, term: str = "o") -> Recording:
    """Type a sequence of characters at the given speed"""
    variance = 0.3*speed
    time_cul = 0.0
    records = []
    for char in text:
        time_cul += speed + random.uniform(-variance, variance)
        records.append(Record(time_cul, char, term))
    rec = Recording(dict(), records=records, start=0.0)
    return rec