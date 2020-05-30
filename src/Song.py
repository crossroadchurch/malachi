# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=R0902 # Limit on number of instance attributes
# pylint: disable=R0912 # Too many branches
# pylint: disable=R0913 # Too many arguments
# pylint: disable=R0914 # Too many local variables
# pylint: disable=R0915 # Too many statements
# pylint: disable=R1702 # Too many nested blocks

"""Represent a Song object in Malachi."""

import sqlite3
import json
import re
import math
from PIL import ImageFont
from Chords import Chords
from MalachiExceptions import InvalidSongIdError, InvalidSongFieldError, MissingStyleParameterError


class Song():
    """Represent a Song object in Malachi."""

    STR_FIELDS = ['song_book_name', 'title', 'author', 'song_key',
                  'verse_order', 'copyright', 'song_number', 'search_title']
    INT_FIELDS = ['transpose_by']

    def __init__(self, song_id, cur_style):
        """Initiate a Song object.

        Arguments:
        song_id -- the id of the Song in the songs database.
        cur_style -- the styling options used to render this Song

        Possible exceptions:
        InvalidSongIdError - raised if the Song doesn't exist in the songs database.
        """
        if Song.is_valid_song_id(song_id):
            self.song_id = song_id
        else:
            raise InvalidSongIdError(song_id)
        self.slides = []
        self.parts = {}
        self.verse_order = ""
        self.part_slide_count = []
        self.get_nonslide_data()  # Must call before paginating slides
        try:
            self.paginate_from_style(cur_style)
        except MissingStyleParameterError as style_error:
            raise MissingStyleParameterError(
                style_error.msg[42:]) from style_error

    @classmethod
    def is_valid_song_id(cls, song_id):
        """Check whether a specified Song id exists in the songs database.

        Arguments:
        song_id -- the Song id to check.

        Return value:
        Boolean
        """
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT s.id FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=song_id))
        result = cursor.fetchall()
        song_db.close()
        return bool(result)

    def get_nonslide_data(self):
        """Retrieve non-lyric Song data from the songs database."""
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT s.title, s.author, s.song_key, s.transpose_by, s.copyright, s.song_book_name, s.song_number
            FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()
        song_db.close()
        self.title = result[0]
        self.author = result[1]
        self.song_key = result[2]
        self.transpose_by = result[3]
        if self.song_key is not None:
            if self.transpose_by == 0:
                self.resultant_key = self.song_key
            else:
                self.resultant_key = Chords.transpose_chord(
                    self.song_key, self.song_key, self.transpose_by)
        else:
            self.resultant_key = ""
        self.copyright = result[4]
        self.song_book_name = result[5]
        self.song_number = result[6]

    def get_title(self):
        """Return the title of this Song."""
        return self.title

    def to_JSON(self, capo):
        """Return a JSON object containing all the data needed to display this song
        to a client (musician or singer).

        Arguments:
        capo -- the capo being used by the client.
        """
        # Need to return song transposed by -capo, plus the new key - if the song has chords!
        if self.resultant_key != "":
            o_key = self.resultant_key
            if capo == 0:
                p_key = self.resultant_key
                c_slides = self.slides
            else:
                capo_key = Chords.transpose_chord(
                    self.resultant_key, self.resultant_key, -int(capo))
                p_key = "Capo {n} ({c})".format(n=capo, c=capo_key)
                c_slides = []
                for slide in self.slides:
                    c_slides.append(Chords.transpose_section(
                        slide, self.resultant_key, -int(capo)))
        else:
            p_key, o_key = "", ""
            c_slides = self.slides
        return json.dumps({
            "type": "song",
            "song-id": self.song_id,
            "title": self.title,
            "copyright": self.copyright,
            "slides": c_slides,
            "played-key": p_key,
            "non-capo-key": o_key,
            "verse-order": self.verse_order,
            "part-counts": self.part_slide_count}, indent=2)

    def to_JSON_full_data(self):
        """Return a JSON object containing all the data in this Song."""
        # Transform self.parts to match grammar specified in Malachi Wiki
        tr_parts = []
        for part in self.parts:
            lc_raw = self.parts[part]
            lc_data = ""
            for combined_line in lc_raw.split("\n"):
                if combined_line == "[br]":
                    lc_data = lc_data + "[br]\n"
                else:
                    chords, lyrics = Chords.extract_chords_and_lyrics(
                        combined_line)
                    if chords.strip() == "":
                        lc_data = lc_data + lyrics + "\n"
                    else:
                        lc_data = lc_data + chords + "@\n" + lyrics + "\n"
            json_part = {"part": part, "data": lc_data}
            tr_parts.append(json_part)

        return json.dumps({
            "song-id": self.song_id, "title": self.title, "author": self.author,
            "song-key": self.song_key, "transpose-by": self.transpose_by,
            "parts": tr_parts, "verse-order": self.verse_order, "copyright": self.copyright,
            "song-book-name": self.song_book_name, "song-number": self.song_number})

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this Song for saving in a service plan."""
        return json.dumps({"type": "song", "song_id": self.song_id})

    def paginate_from_style(self, style):
        """Paginate the current Song based on the specified style.

        Arguments:
        style -- the style options to be used (see paginate() for items required in this dict).

        Possible exceptions:
        MissingStyleParameterError - raised if one or more style parameters have not be specified.
        """
        # Test for existance of necessary formatting keys within params
        missing_params = []
        for param in ["aspect-ratio", "font-size-vh", "div-width-vw", "max-lines", "font-file"]:
            if param not in style:
                missing_params.append(param)
        if missing_params:
            raise MissingStyleParameterError(', '.join(missing_params))
        self.paginate(
            style["aspect-ratio"],
            style["font-size-vh"],
            style["div-width-vw"],
            style["max-lines"],
            style["font-file"])

    def paginate(self, aspect_ratio, font_size_vh, div_width_vw, max_lines, font_file):
        """Paginate the current Song based on the specified style options.

        Arguments:
        aspect_ratio -- the output Screen aspect ratio (width / height).
        font_size_vh -- the font size in vh units.
        div_width_vw -- the width of the div containing the Song in vw units.
        max_lines -- the maximum number of lines to be displayed at any one time.
        font_file -- the URL of the font being used, relative to the root of Malachi.
        """
        window_height = 800  # Arbitrary value chosen
        window_width = window_height * float(aspect_ratio)
        font_size_px = window_height * int(font_size_vh) / 100
        div_width_px = window_width * int(div_width_vw) / 100
        font = ImageFont.truetype(font_file, math.ceil(font_size_px))

        # Need to track chords along with words, but not include chords in width calculations
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT s.lyrics_chords, s.verse_order FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()

        self.parts = dict([x["part"], x["data"]]
                          for x in json.loads(result[0]))
        self.verse_order = result[1]

        # Create verse order if it is missing
        if self.verse_order is None:
            self.verse_order = ' '.join([x for x in self.parts])
        elif self.verse_order.strip() == "":
            self.verse_order = ' '.join([x for x in self.parts])

        if self.parts != {}:
            slide_temp = [self.parts[x] for x in self.verse_order.split(" ")]
        else:
            slide_temp = []
        self.slides = []
        self.part_slide_count = []

        # FOR EACH V1, C1 etc IN SONG ORDER:
        for slide in slide_temp:
            m_slide_sections = slide.split("[br]")  # Mandatory slide breaks
            section_length = 0
            # FOR EACH MANDATORY SLIDE SECTION
            for m_slide_section in m_slide_sections:
                # Transpose m_slide_section if appropriate:
                if self.resultant_key != "" and self.transpose_by != 0:
                    m_section = Chords.transpose_section(
                        m_slide_section.strip(), self.song_key, self.transpose_by)
                else:
                    m_section = m_slide_section.strip()

                cur_slide_lines = 0
                cur_slide_text = ""
                section_lines = m_section.split("\n")
                for line in section_lines:
                    # Determine how many display lines are used for this line
                    line_words = line.split(" ")
                    line_count, line_start, slide_start = 0, 0, 0
                    for i in range(len(line_words)):
                        line_part_chorded = ' '.join(
                            line_words[line_start:i+1])
                        line_part = re.sub(
                            r'\[[\w\+#\/]*\]', '', line_part_chorded)
                        if line_part:
                            size = font.getsize(line_part)
                        else:  # Zero length line
                            size = [0, 0]
                        if size[0] > div_width_px:
                            line_count += 1
                            line_start = i
                            # Line is longer than an entire slide, so break over two slides
                            # This is a very unlikely case...!
                            if line_count == int(max_lines):
                                self.slides.append(
                                    ' '.join(line_words[slide_start:i]))
                                section_length += 1
                                slide_start, line_count = i, 0
                    line_count += 1
                    if (cur_slide_lines + line_count) <= int(max_lines):
                        # Add current line to current slide
                        if cur_slide_text == "":
                            cur_slide_text = ' '.join(line_words[slide_start:])
                        else:
                            cur_slide_text = cur_slide_text + "\n" + ' '.join(
                                line_words[slide_start:])
                        cur_slide_lines += line_count
                    else:
                        # Start new slide for current line after writing out previous slide
                        self.slides.append(cur_slide_text)
                        section_length += 1
                        cur_slide_text = ' '.join(line_words[slide_start:])
                        cur_slide_lines = line_count
                # Add on final slide of section
                self.slides.append(cur_slide_text)
                section_length += 1
            # Update parts length
            self.part_slide_count.append(section_length)
        song_db.close()

    @classmethod
    def text_search(cls, search_text):
        """Perform a text search on the Song database.
        Return all matching Songs (id and title) in a JSON array.

        Arguments:
        search_text -- the text to search for, in either the song's title and/or lyrics.
        """
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT s.id, s.title
            FROM songs AS s
            WHERE s.search_title LIKE "%{txt}%" OR s.search_lyrics LIKE "%{txt}%"
            ORDER BY s.title ASC
        '''.format(txt=search_text))
        songs = cursor.fetchall()
        song_db.close()
        return json.dumps(songs, indent=2)

    @classmethod
    def create_song(cls, title, fields):
        """Create a new Song in the song database.

        Arguments:
        title -- the title of the new Song, which cannot be blank.
        fields -- dict of other Song fields to set when creating the Song, which can be empty.

        Possible exceptions:
        InvalidSongFieldError - raised if validation checks on the Song's fields fail.
        """
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            INSERT INTO songs(song_book_name, title, author, song_key, transpose_by, lyrics_chords, verse_order, copyright, song_number, search_title, search_lyrics)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("", "", "", "", 0, "", "", "", "", "", ""))
        song_db.commit()
        song_id = cursor.lastrowid
        song_db.close()
        fields["title"] = title
        try:
            # Edit song performs all of the field validation for us
            Song.edit_song(song_id, fields)
        except InvalidSongFieldError as song_error:
            # Revert changes by deleting Song(song_id)
            song_db = sqlite3.connect('./data/songs.sqlite')
            cursor = song_db.cursor()
            cursor.execute('''
                DELETE FROM songs
                WHERE id = {id}
            '''.format(id=song_id))
            song_db.commit()
            song_db.close()
            # Raise error with server
            raise InvalidSongFieldError(song_error.msg[29:]) from song_error
        return song_id

    @classmethod
    def edit_song(cls, song_id, fields):
        """Edit a Song that exists in the song database.

        Arguments:
        song_id -- the id of the Song to be edited.
        fields -- dict of Song field values to be edited, not all fields need to be specified.

        Field validation:
        title -- cannot be blank
        song_key -- must be a valid key
        transpose_by -- must be an integer
        lyrics_chords -- must be a list of sections, each of the form:
            e.g. {"part": "v1", "lines": [line_1, ..., line_N]}
            If chords are used then song_key cannot be blank

        Possible exceptions:
        InvalidSongIdError - raised if Song doesn't exist in the songs database.
        InvalidSongFieldError - raised if validation checks on the song's fields fail.
        """
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT s.id, s.song_key FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=song_id))
        result = cursor.fetchone()
        song_db.close()
        if result == []:
            raise InvalidSongIdError(song_id)
        saved_song_key = str(result[1])
        # Field validation
        if "title" in fields:
            if fields["title"].strip() == "":
                raise InvalidSongFieldError("The title was blank")
            else:
                fields["title"] = fields["title"].strip()
                # search_title only has alphanumeric characters and spaces
                fields["search_title"] = ''.join(
                    re.findall(r'[\w\s]*', fields["title"].lower()))
        if "song_key" in fields:
            if fields["song_key"] not in Chords.key_list:
                raise InvalidSongFieldError(
                    "Unrecognised song key: " + fields["song_key"])
        if "transpose_by" in fields:
            if isinstance(fields["transpose_by"], int):
                fields["transpose_by"] = fields["transpose_by"] % 12
            else:
                if fields["transpose_by"].isdigit() is False:
                    raise InvalidSongFieldError(
                        "Unrecognised transpose amount: " + fields["transpose_by"])
                else:
                    fields["transpose_by"] = int(fields["transpose_by"]) % 12
        if "lyrics_chords" in fields:
            search_lyrics = ""
            lyrics_chords = []
            if "song_key" in fields:
                song_key = fields["song_key"]
            elif saved_song_key:
                song_key = saved_song_key

            uses_chords = False
            for section in fields["lyrics_chords"]:
                section_data = ""
                # e.g. section = { "part": "c1", "lines": [line_1, ..., line_N] }
                if "part" in section and "lines" in section:
                    prev_line = ""
                    # Do all chord checking here
                    for line in section["lines"]:
                        if line[-1] == "@" and uses_chords is False:
                            uses_chords = True
                            # Check there is a key, either in saved record or fields["song_key"]
                            # If fields["song_key"] exists then it has already been validated
                            if "song_key" not in fields and saved_song_key not in Chords.key_list:
                                raise InvalidSongFieldError(
                                    "No key specified for a song with chords")

                    # Now process section and combine chords and lyrics
                    for line in section["lines"]:
                        # Case 1: Line is chords
                        if line[-1] == "@":
                            if len(prev_line) >= 1 and prev_line[-1] == "@":
                                # Previous line is chords
                                section_data += Chords.combine_chords_and_lyrics(
                                    prev_line[:-1], "", song_key) + "\n"
                                prev_line = line
                            elif not prev_line:
                                # Previous line already processed
                                prev_line = line
                            else:
                                # Previous line is lyrics
                                section_data += prev_line + "\n"
                                prev_line = line

                        # Case 2: Line is [br]
                        elif line.strip() == "[br]":
                            if len(prev_line) >= 1 and prev_line[-1] == "@":
                                # Previous line is chords
                                section_data += Chords.combine_chords_and_lyrics(
                                    prev_line[:-1], "", song_key) + "\n[br]\n"
                                prev_line = ""
                            elif not prev_line:
                                # Previous line already processed
                                section_data += "[br]\n"
                                prev_line = ""
                            else:
                                # Previous line is lyrics
                                section_data += prev_line + "\n[br]\n"
                                prev_line = ""

                        # Case 3: Line is lyrics
                        else:
                            if len(prev_line) >= 1 and prev_line[-1] == "@":
                                # Previous line is chords
                                section_data += Chords.combine_chords_and_lyrics(
                                    prev_line[:-1], line, song_key) + "\n"
                                prev_line = ""
                            elif not prev_line:
                                # Previous line already processed
                                section_data += line + "\n"
                                prev_line = ""
                            else:
                                # Previous line is lyrics
                                section_data += prev_line + "\n" + line + "\n"
                                prev_line = ""

                    # Deal with final line, if necessary
                    if len(prev_line) >= 1 and prev_line[-1] == "@":
                        # Final line is chords
                        section_data += Chords.combine_chords_and_lyrics(
                            prev_line[:-1], "", song_key) + "\n"
                    elif prev_line:
                        # Final line is unprocesssed lyrics
                        section_data += prev_line + "\n"

                    # Remove final \n from section_data and add section to lyrics_chords
                    cur_section = {}
                    cur_section["part"] = section["part"]
                    cur_section["data"] = section_data[:-1]
                    lyrics_chords.append(cur_section)

                    # Add lyrics to search_lyrics
                    search_lyrics = search_lyrics + re.sub(
                        r'\[.*?\]', '', cur_section["data"].lower().replace('\n', ' ')) + " "
                else:
                    raise InvalidSongFieldError(
                        "lyrics_chords is not correctly formatted")
            search_lyrics = re.sub(r'[^a-zA-Z0-9\s]', '', search_lyrics)
            fields["search_lyrics"] = ' '.join(
                search_lyrics.lower().split())  # Remove extra spaces

        # Create update query for all valid fields in param["fields"] and update song
        update_str = "UPDATE songs SET "
        query_params = []
        for field in fields:
            if field in Song.STR_FIELDS + Song.INT_FIELDS:
                update_str = update_str + field + " = ?, "
                query_params.append(fields[field])
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        if len(update_str) > 17:
            if update_str[-2] == ",":
                # Remove trailing comma, if it exists
                update_str = update_str[:-2]
            update_str = update_str + " WHERE id = ?"
            query_params.append(song_id)
            cursor.execute(update_str, tuple(query_params))
            song_db.commit()

        # Update lyrics_chords and search_lyrics
        if "lyrics_chords" in fields:
            cursor.execute('''
                UPDATE songs
                SET lyrics_chords = ?, search_lyrics = ?
                WHERE id = ?
            ''', (json.dumps(lyrics_chords), fields["search_lyrics"], song_id))
            song_db.commit()
        song_db.close()


### TESTING ONLY ###
if __name__ == "__main__":
    pass
