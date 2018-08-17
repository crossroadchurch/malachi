class Chords():
    # List of valid keys
    key_list = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')

    # Dictionary of enharmonically equivalent notes
    notes_replacements = { 'C#':'Db', 'Db':'C#',
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

    def sanitize_chord(chord, song_key):
        """
        Method to properly format a chord, using notes that are appropriate to the specified key.
        If the root note or bass note is not in the range [A-G] then it will not be changed, and no error will be thrown.
        """

        chord = chord.replace("B#", 'C')
        chord = chord.replace('Cb', 'B')
        chord = chord.replace('E#', 'F')
        chord = chord.replace('Fb', 'E')

        # Chord = root_note {modifier} {/ bass_note}
        # Adjust root note, if necessary, to be a valid note in the song key
        # Adjust bass note, if necessary, to be a valid note in the key specified by root
        # e.g. if we are in C we would want Abmaj7 to be used instead of G#maj7
        #      but E/G# instead of E/Ab (as G# is valid in the key of E)

        # Split chord into root note and the rest of the chord
        if (len(chord) > 1) and (chord[1].lower() == "b" or chord[1] == "#"):
            root_note = chord[0].upper() + chord[1].lower()
            rem_chord = chord[2:]
        else:
            root_note = chord[0].upper()
            rem_chord = chord[1:]

        # Detect bass note, if any
        if rem_chord.find("/") != -1:
            chord_mod = rem_chord[0:rem_chord.find("/")].lower()
            bass_note = rem_chord[rem_chord.find("/") + 1:].capitalize()
        else:
            chord_mod = rem_chord.lower()
            bass_note = ""

        # Adjust root note, if necessary, to be a valid note in the song key
        if root_note in Chords.invalid_note_names[song_key]:
            root_note = Chords.notes_replacements[root_note]

        # Adjust bass note, if necessary, to be a valid note in the root_note key
        if bass_note != "":
            if bass_note in Chords.invalid_note_names[root_note]:
                bass_note = Chords.notes_replacements[bass_note]

        # Re-form chord
        chord = root_note + chord_mod
        if bass_note != "":
            chord = chord + "/" + bass_note

        return chord

    def transpose_chord_tag(chord_tag, root_key, transpose_amount):
        """
        Method to transpose and return a chord tag in a given root_key by a specified number of semitones.
        The returned chord tag will be a valid chord in the transposed key.
        Pre-condition: root_key is a member of key_list
        """
        chord_part = chord_tag[1,-1]
        return '[' +  Chords.transpose_chord(chord_part, root_key, transpose_amount) + ']'

    def transpose_chord(chord, root_key, transpose_amount):
        """
        Method to transpose and return a chord in a given root_key by a specified number of semitones.
        The returned chord will be a valid chord in the transposed key.
        Pre-condition: root_key is a member of key_list
        """

        transposed_key = Chords.key_list[(Chords.key_list.index(root_key) + int(transpose_amount)) % 12]

        # Split chord into root_note, modifier and bass_note
        if (len(chord) > 1) and (chord[1].lower() == "b" or chord[1] == "#"):
            root_note = chord[0].upper() + chord[1].lower()
            rem_chord = chord[2:]
        else:
            root_note = chord[0].upper()
            rem_chord = chord[1:]

        # Detect bass note, if any
        if rem_chord.find("/") != -1:
            chord_mod = rem_chord[0:rem_chord.find("/")].lower()
            bass_note = rem_chord[rem_chord.find("/") + 1:].capitalize()
        else:
            chord_mod = rem_chord.lower()
            bass_note = ""

        # Assume we are in C major and get the valid names for root_note and bass_note
        # Then transpose root_note and bass_note by transpose_amount in C major
        if root_note in Chords.invalid_note_names['C']:
            root_note = Chords.notes_replacements[root_note]
        root_note = Chords.key_list[(Chords.key_list.index(root_note) + int(transpose_amount)) % 12]

        if bass_note != "":
            if bass_note in Chords.invalid_note_names['C']:
                bass_note = Chords.notes_replacements[bass_note]
            bass_note = Chords.key_list[(Chords.key_list.index(bass_note) + int(transpose_amount)) % 12]

        # Reform chord and sanitize in transposed key
        transposed_chord = root_note + chord_mod
        if bass_note != "":
            transposed_chord = transposed_chord + "/" + bass_note

        return Chords.sanitize_chord(transposed_chord, transposed_key)

    def combine_chords_and_lyrics(chord_line, lyric_line, key):
        """
        Method to combine a line of chords with a corresponding line of lyrics.
        e.g.  chord_line =        A7sus4        Bm
              lyric_line = Be the reason that I live
              output = Be the [A7sus4]reason that I [Bm]live
        Any # characters in lyric_line are ignored - these are used to pad out the lyrics to fit the chords.
        All chords will be sanitized to ensure they are valid chords in the specified key.
        """

        char_buffer, line_out = "", ""
        i, j = 0, 0

        # Pad strings to size
        if len(chord_line) < len(lyric_line):
            while(len(chord_line)<len(lyric_line)):
                chord_line += " "
        elif len(lyric_line) < len(chord_line):
            while len(lyric_line) < len(chord_line):
                lyric_line += "#"

        while i < len(chord_line):
            if (chord_line[i] == " "):
                if (lyric_line[i] != "#"):
                    line_out += lyric_line[i]
                i += 1
                j += 1
            else:
                while (i < len(chord_line) and chord_line[i] != " "):
                    char_buffer += chord_line[i]
                    i += 1
                line_out = line_out + "[" + Chords.sanitize_chord(char_buffer, key) + "]"
                char_buffer = ""
                line_out +=  lyric_line[j:i].replace("#", "")
                j = i

        return line_out


    def extract_chords_and_lyrics(in_line):
        """
        Method to turn a valid string into a line of chords and the corresponding line of lyrics.
        e.g.  in_line = Be the [A7sus4]reason that I [Bm]live
              output =        A7sus4        Bm,
                       Be the reason that I live
        The lyrics line will be padded if necessary using # characters to ensure lyrics line up with chords.
        Pre-condition: in_line has valid syntax.
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

                while (in_line[i] != "]"):
                    char_buffer += in_line[i]
                    i += 1

                # Also get closing ]
                char_buffer += in_line[i]
                i += 1

                # Get chord from char_buffer
                chord_line += char_buffer[1:-1]

                # Read in lyric characters to go below chord, pad with # if necessary
                j = 0
                while (j < len(char_buffer[1:-1])):
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