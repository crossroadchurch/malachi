# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=R1705 # Unnecessary "else" after "return".  Disabled for code readability

"""Provide methods for formatting and transposing chords"""

class Chords():
    """Provide methods for formatting and transposing chords"""

    # List of valid keys
    key_list = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')
    # List of all recognised keys, including enharmonic equivalents
    all_key_list = key_list + ('C#', 'D#', 'Gb', 'G#', 'A#', 'Cb', 'B#', 'E#', 'Fb')

    # Dictionary of enharmonically equivalent notes
    notes_replacements = {'C#':'Db', 'Db':'C#',
                          'D#':'Eb', 'Eb':'D#',
                          'F#':'Gb', 'Gb':'F#',
                          'G#':'Ab', 'Ab':'G#',
                          'A#':'Bb', 'Bb':'A#'}

    # Dictionary of invalid note names for each key
    # For each of the five notes C#, D#, F#, G# and A# the dictionary states which
    #  enharmonic equivalent note is invalid in the given key
    invalid_note_names = {'C' :  ['C#', 'D#', 'Gb', 'G#', 'A#'],
                          'C#' : ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'Db' : ['C#', 'D#', 'F#', 'G#', 'A#'],
                          'D' :  ['Db', 'Eb', 'Gb', 'Ab', 'A#'],
                          'D#' : ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'Eb' : ['C#', 'D#', 'F#', 'G#', 'A#'],
                          'E' :  ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'F' :  ['C#', 'D#', 'F#', 'G#', 'A#'],
                          'F#' : ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'Gb' : ['C#', 'D#', 'F#', 'G#', 'A#'],
                          'G' :  ['Db', 'D#', 'Gb', 'G#', 'A#'],
                          'G#' : ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'Ab' : ['C#', 'D#', 'F#', 'G#', 'A#'],
                          'A' :  ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'A#' : ['Db', 'Eb', 'Gb', 'Ab', 'Bb'],
                          'Bb' : ['C#', 'D#', 'F#', 'G#', 'A#'],
                          'B' :  ['Db', 'Eb', 'Gb', 'Ab', 'Bb']}

    @classmethod
    def validate_note(cls, note):
        """
        Checks validity of a note, updating where necessary (e.g. Cb -> B).
        Precondition: note is in Chords.all_key_list
        """
        note = note.replace("B#", 'C')
        note = note.replace('Cb', 'B')
        note = note.replace('E#', 'F')
        note = note.replace('Fb', 'E')
        return note

    @classmethod
    def parse(cls, chord):
        """
        Parse a chord into a dict {root, modifiers, bass}.  If a bass note is
        used, modifiers includes the '/'.  Modifiers and bass can be an empty string. If 
        either the root or bass notes are invalid (e.g. H# or +) then they will be merged
        with modifiers and root/bass will be set as the empty string.

        Key arguments:
        chord -- the chord to be parsed
        """
        parsed_chord = {'root':'', 'modifiers':'', 'bass':'' }
        # Split out bass note, if valid
        if '/' in chord:
            bass = chord[chord.rindex('/')+1:].capitalize()
            if bass in Chords.all_key_list:
                parsed_chord['bass'] = Chords.validate_note(bass)
                bassless_chord = chord[:chord.rindex('/')+1]
            else:
                bassless_chord = chord
        else:
            bassless_chord = chord
        # Split out root note, if valid
        if len(bassless_chord)>1 and bassless_chord[1] in ['b', '#']: # Lazy 'and' prevents exceptions
            root = bassless_chord[:2].capitalize()
            modifiers = bassless_chord[2:]
        else:
            root = bassless_chord[0].capitalize()
            modifiers = bassless_chord[1:]
        if root in Chords.all_key_list:
            parsed_chord['root'] = Chords.validate_note(root)
            parsed_chord['modifiers'] = modifiers
        else:
            parsed_chord['modifiers'] = bassless_chord
        return parsed_chord

    @classmethod
    def sanitize_chord(cls, chord, song_key):
        """
        Format and return a chord, using notes that are appropriate to the specified key.
        If the root note or bass note is not in the range [A-G] then it will not be changed,
        and no error will be thrown.
        If song_key is not a valid key then chord will be returned unchanged.

        Key arguments:
        chord -- the chord to be sanitized.
        song_key -- the key to be used for sanitizing the chord.
        """

        if song_key not in Chords.key_list:
            return chord
        chord_parsed = Chords.parse(chord)
        # Adjust root note, if necessary, to be a valid note in the song key
        if chord_parsed["root"] in Chords.invalid_note_names[song_key]:
            chord_parsed["root"] = Chords.notes_replacements[chord_parsed["root"]]
        # Adjust bass note, if necessary, to be a valid note in the root_note key
        # e.g. if we are in C we would want Abmaj7 to be used instead of G#maj7
        #      but E/G# instead of E/Ab (as G# is valid in the key of E)
        if chord_parsed["bass"] != "" and chord_parsed["root"] != "":
            if chord_parsed["bass"] in Chords.invalid_note_names[chord_parsed["root"]]:
                chord_parsed["bass"] = Chords.notes_replacements[chord_parsed["bass"]]
        elif chord_parsed["bass"] != "" and chord_parsed["root"] == "":
            if chord_parsed["bass"] in Chords.invalid_note_names[song_key]:
                chord_parsed["bass"] = Chords.notes_replacements[chord_parsed["bass"]]
        # Re-form chord
        return chord_parsed["root"] + chord_parsed["modifiers"] + chord_parsed["bass"]

    @classmethod
    def transpose_chord_tag(cls, chord_tag, root_key, transpose_amount):
        """
        Transpose and return a chord in a given root key by a specified number of semitones.
        The returned chord tag will be a valid chord in the transposed key.
        If root_key is not a member of key_list, chord_tag will be returned, untransposed.

        Key arguments:
        chord_tag -- the chord tag to be transposed.
        root_key -- the key that chord_tag is written in.
        transpose_amount -- the number of semitones to transpose chord_tag by.
        """
        chord_part = chord_tag[1:-1]
        if root_key in Chords.key_list:
            return '[' +  Chords.transpose_chord(chord_part, root_key, transpose_amount) + ']'
        else:
            return chord_tag

    @classmethod
    def transpose_chord(cls, chord, root_key, transpose_amount):
        """
        Transpose and return a chord in a given root_key by a specified number of semitones.
        The returned chord will be a valid chord in the transposed key.
        If root_key is not a member of key_list the chord will be returned, untransposed.

        Key arguments:
        chord -- the chord to be transposed.
        root_key -- the key that chord is written in.
        transpose_amount -- the number of semitones to transpose chord by.
        """

        if root_key not in Chords.key_list:
            return chord

        transposed_key = Chords.key_list[(Chords.key_list.index(root_key) + \
            int(transpose_amount)) % 12]

        p_chord = Chords.parse(chord)
        # Exit if either root or bass note are invalid
        if p_chord["root"] != "" and p_chord["root"] not in Chords.all_key_list:
            return chord
        if p_chord["bass"] != "" and p_chord["bass"] not in Chords.all_key_list:
            return chord

        # Assume we are in C major and get the valid names for root_note and bass_note
        # Then transpose root_note and bass_note by transpose_amount in C major
        if p_chord["root"] != "":
            if p_chord["root"] in Chords.invalid_note_names['C']:
                p_chord["root"] = Chords.notes_replacements[p_chord["root"]]
            p_chord["root"] = Chords.key_list[(Chords.key_list.index(p_chord["root"]) + int(transpose_amount)) % 12]

        if p_chord["bass"] != "":
            if p_chord["bass"] in Chords.invalid_note_names['C']:
                p_chord["bass"] = Chords.notes_replacements[p_chord["bass"]]
            p_chord["bass"] = Chords.key_list[(Chords.key_list.index(p_chord["bass"]) + \
                int(transpose_amount)) % 12]

        # Reform chord and sanitize in transposed key
        transposed_chord = p_chord["root"] + p_chord["modifiers"] + p_chord["bass"]
        return Chords.sanitize_chord(transposed_chord, transposed_key)

    @classmethod
    def combine_chords_and_lyrics(cls, chord_line, lyric_line, key):
        """
        Combine a line of chords with a corresponding line of lyrics.

        e.g.  chord_line =        A7sus4        Bm
              lyric_line = Be the reason that I live
              output = Be the [A7sus4]reason that I [Bm]live

        Any '#' in lyric_line are ignored - these are used to pad out the lyrics to fit the chords.
        All chords will be sanitized to ensure they are valid chords in the specified key.

        Arguments:
        chord_line -- the line of chords corresponding to lyric_line
        lyric_line -- the line of lyrics
        key -- the key that the chords are written in

        Return value:
        line_out -- string, the combined lyric and chord line
        """

        char_buffer, line_out = "", ""
        i, j = 0, 0

        # Pad strings to size
        if len(chord_line) < len(lyric_line):
            while len(chord_line) < len(lyric_line):
                chord_line += " "
        elif len(lyric_line) < len(chord_line):
            while len(lyric_line) < len(chord_line):
                lyric_line += "#"

        while i < len(chord_line):
            if chord_line[i] == " ":
                if lyric_line[i] != "#":
                    line_out += lyric_line[i]
                i += 1
                j += 1
            else:
                while (i < len(chord_line) and chord_line[i] != " "):
                    char_buffer += chord_line[i]
                    i += 1
                line_out = line_out + "[" + Chords.sanitize_chord(char_buffer, key) + "]"
                char_buffer = ""
                line_out += lyric_line[j:i].replace("#", "")
                j = i

        return line_out

    @classmethod
    def extract_chords_and_lyrics(cls, in_line):
        """
        Turn a combined line of lyrics and chords into a line of chords and the corresponding
        line of lyrics.

        e.g.  in_line = Be the [A7sus4]reason that I [Bm]live
              output =        A7sus4        Bm,
                       Be the reason that I live
        The lyrics line will be padded with #, if necessary, to ensure lyrics line up with chords.

        Pre-condition: in_line has valid syntax.

        Arguments:
        in_line -- the line of combined lyrics and chords.

        Return values:
        chord_line, lyric_line -- both strings
        """

        chord_line, lyric_line, char_buffer = "", "", ""
        i = 0

        while i < len(in_line):

            if in_line[i] != "[":
                lyric_line += in_line[i]
                chord_line += " "
                i += 1
            else:
                # Read in entire chord tag
                char_buffer = ""

                while in_line[i] != "]":
                    char_buffer += in_line[i]
                    i += 1

                # Also get closing ]
                char_buffer += in_line[i]
                i += 1

                # Get chord from char_buffer
                chord_line += char_buffer[1:-1]

                # Read in lyric characters to go below chord, pad with # if necessary
                j = 0
                while j < len(char_buffer[1:-1]):
                    # No problem with i being out of bounds due to lazy 'and' evaluation
                    if (i < len(in_line) and in_line[i] != "["):
                        lyric_line += in_line[i]
                        i += 1
                        j += 1
                    else:
                        lyric_line += "#"
                        j += 1

                # Need at least one space between chords
                if i < len(in_line) and in_line[i] == "[":
                    chord_line += " "
                    lyric_line += "#"

        return chord_line, lyric_line

    @classmethod
    def transpose_section(cls, in_str, root_key, transpose_amount):
        """
        Transpose and return a string containing lyrics and chord tags.

        Arguments:
        in_str -- the string of lyrics with chord tags
        root_key -- the key that the chords are written in
        transpose_amount -- the number of semitones to transpose the chords by

        """
        out_str = ""
        i = 0
        while i < len(in_str):
            if in_str[i] != "[":
                out_str += in_str[i]
                i += 1
            else:
                # Read in entire chord tag
                char_buffer = ""
                while in_str[i] != "]":
                    char_buffer += in_str[i]
                    i += 1
                # Include closing ]
                char_buffer += in_str[i]
                i += 1
                # Add transposed chord to out_str
                out_str += Chords.transpose_chord_tag(char_buffer, root_key, transpose_amount)
        return out_str

# Testing only
if __name__ == "__main__":
    pass