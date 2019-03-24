import re


class _BaseInt:
    """
    Base class for int like values
    """

    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return f"{self.__class__.__name__}({self._value})"

    def __int__(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, (int, self.__class__)):
            return int(self) == int(other)
        else:
            raise TypeError(f"Invalid type {type(other)} for other")

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._value)


class Note(_BaseInt):
    """
    Represents a note without the octave information. Effectively
    the same as Z/12Z.

    Intervals are represented as integers and can be add substracted to a
    note. Two notes can be substracted to obtain an interval.

    One can cast to int to obtain the numerical value.
    """

    NOTE_PATTERN = r"([A-Ga-g])([#b]?)"
    NOTE_RE = re.compile(f"^{NOTE_PATTERN}$")
    NOTES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

    def __init__(self, value):
        """
        Args:
            value (int): 0 represents C, then everything is modulo 12.
        """
        super(Note, self).__init__(value % len(self.NOTES))

    def __str__(self):
        return self.NOTES[int(self)].replace('b', '\u266d')

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        if isinstance(other, int):
            return Note(int(self) + other)
        else:
            raise ValueError(f"Impossible to add {other} to {self}")

    def __sub__(self, other):
        if isinstance(other, int):
            return Note(int(self) - other)
        elif isinstance(other, Note):
            return (int(self) - int(other)) % len(Note.NOTES)
        else:
            raise ValueError(f"Impossible to remove {other} to {self}")

    @staticmethod
    def from_str(note):
        """
        Parse a note from its string representations.

        >>> int(Note.from_str('C#'))
        1

        """

        match = Note.NOTE_RE.match(note)
        if match is None:
            return None

        name = match.group(1).upper()
        modifier = match.group(2)

        value = Note.NOTES.index(name)
        if modifier == "#":
            value += 1
        elif modifier == "b":
            value -= 1
        return Note(value)


A = Note(-3)


def iter_notes(start=A):
    for semitons in range(len(Note.NOTES)):
        yield start + semitons


class Pitch(_BaseInt):
    """
    Represents a note with octave information. For instance B1 and B2
    are one octave appart.
    """

    PITCH = f"(?P<note>{Note.NOTE_PATTERN})" r"(?P<octave>-?\d+)?"
    PITCH = re.compile(f"^{PITCH}$")

    def __init__(self, note, octave=0):
        super(Pitch, self).__init__(int(note) + octave * OCTAVE)

    @property
    def note(self):
        """
        Return the :class:`Note` obtained by ignoring octave information.
        """
        return Note(int(self))

    @property
    def octave(self):
        """
        Return the octave of the note.
        """
        return int(self) // OCTAVE

    def __str__(self):
        return f"{self.note}{self.octave}"

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        if isinstance(other, int):
            return Pitch(int(self) + other)
        else:
            raise ValueError(f"Impossible to add {other} to {self}")

    def __sub__(self, other):
        if isinstance(other, int):
            return Pitch(int(self) - other)
        elif isinstance(other, Pitch):
            return int(self) - int(other)
        else:
            raise ValueError(f"Impossible to remove {other} to {self}")

    @staticmethod
    def from_note(note, octave=0):
        return Pitch(int(note) + octave * OCTAVE)

    @staticmethod
    def from_str(pitch):
        match = Pitch.PITCH.match(pitch)
        if match is None:
            return None

        note = Note.from_str(match.group("note"))
        octave = match.group("octave")
        octave = 0 if octave is None else int(octave)

        return Pitch.from_note(note, octave)

    @property
    def midi(self):
        """
        Return the midi code for the note. Does not check for overflow or
        underflow.
        """
        midi_c0 = 12
        return int(self) + midi_c0

    @property
    def frequency(self):
        """
        Return the standard frequency for this note. A4 frequency
        is taken to be 440 Hz and half tone to be 2**(1/12).
        """
        a4 = Pitch.from_str("A4")
        a4_frequency = 440
        return a4_frequency * 2**(int(self - a4) / 12)


class Scale:
    SCALE_RE = re.compile(f"^({Note.NOTE_PATTERN})(M|maj|min|m)$")
    TRAKTOR_RE = re.compile(r"^(\d{1,2})(m|d)$")
    TRAKTOR_START = {"min": Note.from_str("A"), "maj": Note.from_str("C")}

    TONES = {"maj": [2, 2, 1, 2, 2, 2, 1], "min": [2, 1, 2, 2, 1, 3, 1]}

    def __init__(self, note, mode="maj"):
        self.note = note
        self.mode = mode

    @staticmethod
    def from_str(scale):
        match = Scale.SCALE_RE.match(scale)
        if match is None:
            return None
        note = Note.from_str(match.group(1))
        mode = match.group(4)
        if mode == "m":
            mode = "min"
        elif mode == "M":
            mode = "maj"
        return Scale(note, mode)

    def __str__(self):
        return f"{self.note}{self.mode}"

    def __repr__(self):
        return str(self)

    @staticmethod
    def from_traktor(scale):
        match = Scale.TRAKTOR_RE.match(scale)
        if match is None:
            return None

        index = int(match.group(1)) - 1
        mode = {"m": "min", "d": "maj"}[match.group(2)]
        return Scale(Note(int(Scale.TRAKTOR_START[mode]) + 7 * index), mode)

    @property
    def traktor(self):
        mode = {"min": "m", "maj": "d"}[self.mode]
        note = (7 *
                (int(self.note) - int(Scale.TRAKTOR_START[self.mode]))) % len(
                    Note.NOTES) + 1
        return "{}{}".format(note, mode)

    @property
    def notes(self):
        notes = [self.note]
        for delta in Scale.TONES[self.mode][:-1]:
            notes.append(notes[-1] + delta)
        return notes


def iter_scales(start=A, mode=None):
    if mode is None:
        modes = ['min', 'maj']
    else:
        modes = [mode]
    for note in iter_notes(start):
        for mode in modes:
            yield Scale(note, mode)


def scales_with(*notes, perfect=True):
    def _sort_key(pair):
        common, scale = pair
        return (len(common), str(scale))

    notes = set(notes)
    scales = list(iter_scales())
    commons = [[note for note in scale.notes if note in notes]
               for scale in scales]
    if perfect:
        return [
            scale for scale, commons in zip(scales, commons)
            if len(commons) == len(notes)
        ]
    return sorted(zip(commons, scales), key=_sort_key, reverse=True)


OCTAVE = len(Note.NOTES)
for note in iter_notes():
    globals()[f'{note}'] = note
    for octave in range(0, 10):
        globals()[f'{note}{octave}'] = Pitch(note, octave)
