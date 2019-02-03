import functools
import re


class _BaseInt:
    '''
    Base class for int like values
    '''

    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return f'{self.__class__.__name__}({self._value})'

    def __int__(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, [int, self.__class__]):
            return int(self) == int(other)
        else:
            raise TypeError(f'Invalid type {type(other)} for other')

    def __ne__(self, other):
        return not self == other


class Note(_BaseInt):
    '''
    Represents a note without the octave information. Effectively 
    the same as Z/12Z.

    Intervals are represented as integers and can be add substracted to a
    note. Two notes can be substracted to obtain an interval.

    One can cast to int to obtain the numerical value.
    '''
    NOTE_PATTERN = r'([A-Ga-g])([#b]?)'
    NOTE_RE = re.compile(f'^{NOTE_PATTERN}$')
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(self, value):
        '''
        Args:
            value (int): 0 represents C, then everything is modulo 12.
        '''
        super(Note, self).__init__(value % len(self.NOTES))

    def __str__(self):
        return self.NOTES[int(self)]

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        if isinstance(other, int):
            return Note(int(self) + other)
        else:
            raise ValueError(f'Impossible to add {other} to {self}')

    def __sub__(self, other):
        if isinstance(other, int):
            return Note(int(self) - other)
        elif isinstance(other, Note):
            return (int(self) - int(other)) % len(Note.NOTES)
        else:
            raise ValueError(f'Impossible to remove {other} to {self}')

    @staticmethod
    def from_str(note):
        '''
        Parse a note from its string representations.

        >>> int(Note.from_str('C#'))
        1

        '''

        match = Note.NOTE_RE.match(note)
        if match is None:
            return None

        name = match.group(1).upper()
        modifier = match.group(2)

        value = Note.NOTES.index(name)
        if modifier == '#':
            value += 1
        elif modifier == 'b':
            value -= 1
        return Note(value)


def note(note):
    '''
    Same as Note.from_str
    '''
    return Note.from_str(note)


class PNote(_BaseInt):
    '''
    Represents a note with octave information. For instance B1 and B2
    are one octave appart.
    '''
    PNOTE_PATTERN = f'(?P<note>{Note.NOTE_PATTERN})' r'(?P<octave>-?\d+)?'
    PNOTE_RE = re.compile(f'^{PNOTE_PATTERN}$')

    def __init__(self, value):
        '''
        Arguments:
            value (int): 0 represents C0
        '''
        super(PNote, self).__init__(value)

    @property
    def note(self):
        '''
        Return the :class:`Note` obtained by ignoring octave information.
        '''
        return Note(int(self))

    @property
    def octave(self):
        '''
        Ret urn the octave of the note.
        '''
        return int(self) // OCTAVE

    def __str__(self):
        return f'{self.note}{self.octave}'

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        if isinstance(other, int):
            return PNote(int(self) + other)
        else:
            raise ValueError(f'Impossible to add {other} to {self}')

    def __sub__(self, other):
        if isinstance(other, int):
            return PNote(int(self) - other)
        elif isinstance(other, PNote):
            return int(self) - int(other)
        else:
            raise ValueError(f'Impossible to remove {other} to {self}')

    @staticmethod
    def from_note(note, octave=0):
        return PNote(int(note) + octave * OCTAVE)

    @staticmethod
    def from_str(pnote):
        match = PNote.PNOTE_RE.match(pnote)
        if match is None:
            return None

        note = Note.from_str(match.group('note'))
        octave = match.group('octave')
        octave = 0 if octave is None else int(octave)

        return PNote.from_note(note, octave)

    @property
    def midi(self):
        '''
        Return the midi code for the note. Does not check for overflow or
        underflow.
        '''
        midi_c0 = 12
        return int(self) + midi_c0

    @property
    def frequency(self):
        '''
        Return the standard frequency for this note. A4 frequency
        is taken to be 440 Hz and half tone to be 2**(1/12).
        '''
        a4 = PNote.from_str('A4')
        a4_frequency = 440
        return a4_frequency * 2**(int(self - a4) / 12)


def pnote(pnote):
    return PNote.from_str(pnote)


class Scale:
    SCALE_RE = re.compile(f'^({Note.NOTE_PATTERN})(M|maj|min|m)$')
    TRAKTOR_RE = re.compile(r'^(\d{1,2})(m|d)$')
    TRAKTOR_START = {'min': Note.from_str('A'), 'maj': Note.from_str('C')}

    TONES = {'maj': [2, 2, 1, 2, 2, 2, 1], 'min': [2, 1, 2, 2, 1, 3, 1]}

    def __init__(self, note, mode='maj'):
        self.note = note
        self.mode = mode

    @staticmethod
    def from_str(scale):
        match = Scale.SCALE_RE.match(scale)
        if match is None:
            return None
        note = Note.from_str(match.group(1))
        mode = match.group(4)
        if mode == 'm':
            mode = 'min'
        elif mode == 'M':
            mode = 'maj'
        return Scale(note, mode)

    def __str__(self):
        return f'{self.note}{self.mode}'

    def __repr__(self):
        return str(self)

    @staticmethod
    def from_traktor(scale):
        match = Scale.TRAKTOR_RE.match(scale)
        if match is None:
            return None

        index = int(match.group(1)) - 1
        mode = {'m': 'min', 'd': 'maj'}[match.group(2)]
        return Scale(Note(int(Scale.TRAKTOR_START[mode]) + 7 * index), mode)

    @property
    def traktor(self):
        mode = {'min': 'm', 'maj': 'd'}[self.mode]
        note = (7 *
                (int(self.note) - int(Scale.TRAKTOR_START[self.mode]))) % len(
                    Note.NOTES) + 1
        return '{}{}'.format(note, mode)

    def notes(self, octave=None):
        start = self.note if octave is None else PNote.from_note(
            self.note, octave)
        return functools.reduce(lambda a, n: a + [a[-1] + n],
                                Scale.TONES[self.mode][:-1], [start])


OCTAVE = len(Note.NOTES)
