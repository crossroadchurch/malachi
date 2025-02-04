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
import os
import binascii
import pickle
import re
from datetime import datetime
from PIL import ImageFont
from zipfile import ZipFile
from Chords import Chords
from MalachiExceptions import InvalidSongIdError, InvalidSongFieldError, MissingStyleParameterError

class Song():
    """Represent a Song object in Malachi."""

    STR_FIELDS = ['song_book_name', 'title', 'author', 'song_key',
                  'verse_order', 'copyright', 'song_number', 'search_title', 'audio']
    INT_FIELDS = ['transpose_by', 'remote', 'deleted']
    length_data = dict()

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
        self.uses_chords = False
        self.parts = {}
        self.verse_order = ""
        self.part_slide_count = []
        self.get_nonslide_data()  # Must call before paginating slides
        try:
            self.paginate_from_style(cur_style)
        except MissingStyleParameterError as style_error:
            raise MissingStyleParameterError(
                style_error.msg[42:]) from style_error
        self.add_fills()

    @classmethod
    def is_valid_song_id(cls, song_id):
        """Check whether a specified Song id exists in the songs database.

        Arguments:
        song_id -- the Song id to check.

        Return value:
        Boolean
        """
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=song_id))
        result = cursor.fetchall()
        song_db.close()
        return bool(result)

    def get_nonslide_data(self):
        """Retrieve non-lyric Song data from the songs database."""
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.title, s.author, s.song_key, s.transpose_by, s.copyright, s.song_book_name, s.song_number, s.audio, s.deleted
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
        self.audio = result[7]
        self.deleted = result[8]

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
            "audio": self.audio,
            "slides": c_slides,
            "played-key": p_key,
            "non-capo-key": o_key,
            "verse-order": self.verse_order,
            "fills": self.fills,
            "part-counts": self.part_slide_count,
            "uses-chords": self.uses_chords}, indent=2)

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
            "parts": tr_parts, "verse-order": self.full_verse_order, "copyright": self.copyright,
            "song-book-name": self.song_book_name, "song-number": self.song_number,
            "audio": self.audio, "fills": self.fills, "deleted": self.deleted })

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this Song for saving in a service plan."""
        return json.dumps({"type": "song", "song_id": self.song_id})

    def export_to_JSON(self, export_zip):
        """
        Return a JSON object representing this Song for exporting to another
        instance of Malachi, adding the attached audio (if present) to export_zip.
        """
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.lyrics_chords, s.verse_order, s.search_title, s.search_lyrics, s.fills
            FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()
        song_db.close()
        if self.audio:
            with ZipFile(export_zip, 'a') as out_zip:
                # Test if audio has already been written to out_zip
                if 'audio/{f}'.format(f=self.audio) not in out_zip.namelist():
                    out_zip.write('./audio/{f}'.format(f=self.audio))
        return json.dumps({
            "type": "song",
            "id": self.song_id,
            "title": self.title,
            "author": self.author,
            "song_key": self.song_key,
            "transpose_by": self.transpose_by,
            "copyright": self.copyright,
            "song_book_name": self.song_book_name,
            "song_number": self.song_number,
            "lyrics_chords": result[0],
            "verse_order": result[1],
            "search_title": result[2],
            "search_lyrics": result[3],
            "fills": result[4],
            "audio": self.audio
        })

    @classmethod
    def import_attached_audio(cls, audio_filename, export_zip):
        audio_url = './audio/{f}'.format(f=audio_filename)
        with ZipFile(export_zip, 'a') as out_zip: # mode must be 'a' in case we need to modify filename in zip
            if not os.path.exists(audio_url):
                out_zip.extract(audio_url[2:])
            else:
                # An audio file with that name exists.  Use CRC32 to test if it is the same
                # as the one stored in out_zip
                idx = [index for index, element in enumerate(out_zip.infolist()) 
                    if element.filename == audio_url[2:]][0]
                crc_zip = out_zip.infolist()[idx].CRC
                disk_pres = open(audio_url, 'rb').read()
                crc_disk = binascii.crc32(disk_pres)
                if crc_zip != crc_disk:
                    # Audio file on disk is different to one stored in zip file.
                    # Append timestamp to audio file in zip file before extracting and
                    #  update url used in Malachi accordingly
                    path_parts = os.path.splitext(audio_url)
                    timestamp = datetime.now().strftime('_%Y%m%d_%H%M%S')
                    audio_url = path_parts[0] + timestamp + path_parts[1]
                    audio_filename = audio_url[8:]
                    out_zip.infolist()[idx].filename = audio_url[2:]
                    out_zip.extract(out_zip.infolist()[idx])
        return audio_filename

    @classmethod
    def make_unique_title(cls, title):
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.title
            FROM songs AS s
            WHERE (s.title LIKE "{txt}%")
            AND (s.deleted = 0)
            ORDER BY s.title ASC
        '''.format(txt=title))
        title_tuples = cursor.fetchall()
        titles = [x[0] for x in title_tuples]
        if title not in titles:
            unique_title = title
        else:
            prefix_len = len(title) + 2
            filtered_titles = [int(x[prefix_len:-1]) for x in titles if x.startswith(title + " [") and x[prefix_len:-1].isdigit()]
            if filtered_titles:
                unique_title = "{t} [{n}]".format(t=title, n=str(max(filtered_titles)+1))
            else:
                unique_title = "{t} [1]".format(t=title)
        song_db.close()
        return unique_title

    @classmethod
    def import_from_JSON(cls, json_data, export_zip, cur_style):
        """
        Return a Song object corresponding to the song stored in json_data, which
        has been exported (possibly from another instance of Malachi) using the
        export_to_JSON method.

        Precondition: json_data["type"] == "song"
        """
        # See whether the song exists in the songs database (based on lyrics and chords)
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id, s.lyrics_chords, s.verse_order, s.transpose_by, s.audio
            FROM songs AS s
            WHERE s.lyrics_chords = ?
        ''', [json_data["lyrics_chords"]])
        result = cursor.fetchone()
        if result:
            print("Song match found in database, not importing")
            # Song match found in database
            s_id = result[0]
            # Update verse_order and transpose_by based on values in json_data
            cursor.execute('''
                UPDATE songs
                SET verse_order = ?, transpose_by = ?
                WHERE id = ? 
            ''', (json_data["verse_order"], json_data["transpose_by"], s_id))
            song_db.commit()
            # Add attached audio (won't replace existing attached audio)
            if not result[4] and json_data["audio"]: # No attached audio in database, attached audio in zip
                audio_file = Song.import_attached_audio(json_data["audio"], export_zip)
                print("Attaching audio [{f}] to existing song (without existing audio)".format(f=audio_file))
                cursor.execute('''
                    UPDATE songs
                    SET audio = ?
                    WHERE id = ?
                ''', (audio_file, s_id))
                song_db.commit()
        else:
            print("Song match not found, importing song into database")
            # Song match not found, import song into database
            # First deal with any attached audio in case we need to change the audio url
            if json_data["audio"]:
                audio_file = Song.import_attached_audio(json_data["audio"], export_zip)
            else:
                audio_file = "" 
            print("Song has [{f}] as audio".format(f=audio_file))
            # Get unique title for song - by adding [n] if needed
            song_title = Song.make_unique_title(json_data["title"])
            # Now insert song into database
            cursor.execute('''
                INSERT INTO songs(title, author, song_key, transpose_by, copyright, song_book_name, song_number, lyrics_chords, verse_order, search_title, search_lyrics, fills, audio)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                song_title, 
                json_data["author"], 
                json_data["song_key"], 
                json_data["transpose_by"],
                json_data["copyright"],
                json_data["song_book_name"],
                json_data["song_number"],
                json_data["lyrics_chords"],
                json_data["verse_order"],
                json_data["search_title"],
                json_data["search_lyrics"],
                json_data["fills"],
                audio_file))
            song_db.commit()
            s_id = cursor.lastrowid
        song_db.close()
        return Song(s_id, cur_style)


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
        # Max width of div based on font size of 32 (used in size calculations stored in pickle)
        MAX_WIDTH = 32 * float(aspect_ratio) * int(div_width_vw) / int(font_size_vh)
        SPACE_WIDTH = 7.9375
        font = ImageFont.truetype(font_file, 32)
        
        # Need to track chords along with words, but not include chords in width calculations
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.lyrics_chords, s.verse_order, s.fills FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()

        self.parts = dict([x["part"], x["data"]]
                          for x in json.loads(result[0]))
        self.saved_verse_order = result[1]

        self.fills = json.loads(result[2])
        self.fill_dict = {}
        for idx, fill in enumerate(self.fills):
            self.fill_dict[":" + str(idx+1)] = fill

        # Create verse order if it is missing
        if self.saved_verse_order is None:
            self.saved_verse_order = ' '.join([x for x in self.parts])
        elif self.saved_verse_order.strip() == "":
            self.saved_verse_order = ' '.join([x for x in self.parts])

        if self.parts != {}:
            slide_temp = [self.parts[x] for x in self.saved_verse_order.split(" ") if x in self.parts]
            self.full_verse_order = ' '.join([x for x in self.saved_verse_order.split(" ") 
                                              if x in self.parts or x in self.fill_dict])
            self.verse_order = ' '.join([x for x in self.saved_verse_order.split(" ") if x in self.parts])
            if self.verse_order == "":
                # Fix completely invalid verse order
                slide_temp = [self.parts[x] for x in self.parts]
                self.verse_order = ' '.join([x for x in self.parts])
                self.full_verse_order = ' '.join([x for x in self.parts])
        else:
            slide_temp = []
            self.verse_order = self.saved_verse_order
            self.full_verse_order = self.saved_verse_order

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
                    line_count, slide_start = 0, 0
                    line_length = -1 * SPACE_WIDTH
                    for idx, word_and_chords in enumerate(line_words):
                        word = re.sub(r'\[[\w\+|#\/]*\]', '', word_and_chords)
                        if word != "":
                            if word in Song.length_data:
                                word_length = Song.length_data[word]
                            else:
                                print("Not found in dict: {w}".format(w=word))
                                word_length = font.getlength(word)
                            line_length += SPACE_WIDTH
                            line_length += word_length
                        if line_length > MAX_WIDTH:
                            line_count += 1
                            line_length = word_length
                            # Line is longer than an entire slide, so break over two slides
                            # This is a very unlikely case...!
                            if line_count == int(max_lines):
                                self.slides.append(' '.join(line_words[slide_start:idx]))
                                section_length += 1
                                slide_start, line_count = idx, 0
                                line_length = -1 * SPACE_WIDTH
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
        # Determine if song uses chords
        for slide in self.slides:
            if "[" in slide:
                self.uses_chords = True
        song_db.close()

    def package_fill(self, fill):
        # Package fill in correct key, transposing if necessary
        packaged_fill = "[¬]" + ''.join("[" + x + "]" for x in fill.split(" ")) + "[¬]"
        if self.resultant_key != "" and self.transpose_by != 0:
            actual_fill = Chords.transpose_section(packaged_fill, self.song_key, self.transpose_by)
        else:
            actual_fill = packaged_fill
        return actual_fill

    def add_fills(self):
        # Pre-condition - Song has already been paginated => self.fill_dict is populated and self.full_verse_order exists
        order_with_fills = self.full_verse_order.split(" ")
        order_no_fills = self.verse_order.split(" ")

        offset = 0
        cur_slide = 0
        for idx, part in enumerate(order_with_fills):
            if (idx-offset) < len(order_no_fills) and part != order_no_fills[idx - offset]:
                # Fill detected
                if idx == 0: # Intro
                    # Intro
                    self.slides[0] = self.package_fill(self.fill_dict[part]) + self.slides[0]
                else: # Fill
                    link_fill = self.package_fill(self.fill_dict[part])
                    self.slides[cur_slide-1] = self.slides[cur_slide-1] + link_fill
                    self.slides[cur_slide] = link_fill + self.slides[cur_slide]
                offset += 1
            elif (idx-offset) == len(order_no_fills): # Outro
                self.slides[-1] = self.slides[-1] + self.package_fill(self.fill_dict[part])
            else:
                # Non-fill match found
                cur_slide += self.part_slide_count[idx-offset]

    @classmethod
    def text_search(cls, search_text):
        """Perform a text search on the Song database.
        Return all matching non-deleted Songs (id and title) in a JSON array.

        Arguments:
        search_text -- the text to search for, in either the song's title, lyrics or song number.
        """
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id, s.title
            FROM songs AS s
            WHERE (s.search_title LIKE "%{txt}%" OR s.search_lyrics LIKE "%{txt}%" OR s.song_number LIKE "{txt}")
            AND (s.deleted = 0)
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
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            INSERT INTO songs(song_book_name, title, author, song_key, transpose_by, lyrics_chords, verse_order, copyright, song_number, search_title, search_lyrics, audio)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("", "", "", "C", 0, "", "", "", "", "", "", ""))
        song_db.commit()
        song_id = cursor.lastrowid
        song_db.close()
        fields["title"] = title
        try:
            # Edit song performs all of the field validation for us
            Song.edit_song(song_id, fields)
        except InvalidSongFieldError as song_error:
            # Revert changes by deleting Song(song_id)
            song_db, cursor = Song.db_connect()
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
    def delete_song(cls, song_id):
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=song_id))
        result = cursor.fetchone()
        if result == []:
            raise InvalidSongIdError(song_id)
        cursor.execute('''
            UPDATE songs
            SET deleted = 1
            WHERE id = {s_id}
        '''.format(s_id=song_id))
        song_db.commit()
        song_db.close()

    @classmethod
    def restore_song(cls, song_id):
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=song_id))
        result = cursor.fetchone()
        if result == []:
            raise InvalidSongIdError(song_id)
        cursor.execute('''
            UPDATE songs
            SET deleted = 0
            WHERE id = {s_id}
        '''.format(s_id=song_id))
        song_db.commit()
        song_db.close()

    @classmethod
    def get_recycle_bin(cls):
        """
        Returns a list of all songs that have been marked as deleted.
        """
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id, s.title
            FROM songs AS s
            WHERE s.deleted = 1
            ORDER BY s.title ASC
        ''')
        songs = cursor.fetchall()
        song_db.close()
        return json.dumps(songs, indent=2)
    
    @classmethod
    def empty_recycle_bin(cls):
        """
        Permanently deletes all songs that have been marked as deleted.
        """
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            DELETE FROM songs AS s
            WHERE s.deleted = 1
        ''')
        song_db.commit()
        song_db.close()

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
        song_db, cursor = Song.db_connect()
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

            for section in fields["lyrics_chords"]:
                section_data = ""
                # e.g. section = { "part": "c1", "lines": [line_1, ..., line_N] }
                if "part" in section and "lines" in section:
                    prev_line = ""

                    # Process section and combine chords and lyrics
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
        song_db, cursor = Song.db_connect()
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

        # Update fills
        if "fills" in fields:
            cursor.execute('''
                UPDATE songs
                SET fills = ?
                WHERE id = ?
            ''', (json.dumps(fields["fills"]), song_id))
            song_db.commit()

        song_db.close()

    @classmethod
    def db_connect(cls):
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        return song_db, cursor

    @classmethod
    def update_schema(cls):
        """
        Check schema of songs.sqlite and add additional columns if necessary
        """
        song_db, cursor = Song.db_connect()
        cursor.execute('PRAGMA table_info("songs")')
        song_rows = cursor.fetchall()
        
        if len([x for x in song_rows if x[1]=='remote']) == 0:
            # Add remote song column to songs table
            cursor.execute('ALTER TABLE songs ADD COLUMN remote INTEGER DEFAULT 0')

        if len([x for x in song_rows if x[1]=='audio']) == 0:
            # Add audio recording column to songs table
            cursor.execute('ALTER TABLE songs ADD COLUMN audio TEXT NOT NULL DEFAULT ""')

        if len([x for x in song_rows if x[1]=='fills']) == 0:
            # Add fills column to songs table
            cursor.execute('ALTER TABLE songs ADD COLUMN fills TEXT NOT NULL DEFAULT "[]"')

        # Add mandatory key to each song, converting existing NULLs into 'C'
        song_key_row = [x for x in song_rows if x[1]=='song_key'][0]
        if song_key_row[3] == 0: # songs(song_key) NOT NULL flag set to false, so hasn't been updated yet
            cursor.execute('ALTER TABLE songs RENAME song_key TO old_song_key')
            cursor.execute('ALTER TABLE songs ADD COLUMN song_key VARCHAR(3) NOT NULL DEFAULT "C"')
            cursor.execute('UPDATE songs SET song_key = old_song_key WHERE old_song_key IS NOT NULL AND old_song_key IS NOT ""')
            song_db.commit()
            cursor.execute('ALTER TABLE songs DROP COLUMN old_song_key')

        if len([x for x in song_rows if x[1]=='deleted']) == 0:
            # Add deleted flag column to songs table
            cursor.execute('ALTER TABLE songs ADD COLUMN deleted INTEGER DEFAULT 0')
            
        cursor.close()
        song_db.close()

    @classmethod
    def generate_word_sizes(cls, font_file):
        song_db, cursor = Song.db_connect()
        cursor.execute('''
            SELECT s.id, s.lyrics_chords
            FROM songs AS s
        ''')
        results = cursor.fetchall()
        song_db.close()

        all_words = set()
        for idx, song in enumerate(results):
            song_json = json.loads(song[1])
            for part in song_json:
                part_words = part["data"].split()
                for word in part_words:
                    no_chord_word = re.sub(r'\[.*?\]', '', word)
                    all_words.add(no_chord_word)
        # Remove excess empty string
        all_words.remove("")
        print('{u} unique words detected in songs'.format(u=len(all_words)))
        print('Saving word sizes...')
        # Update dict of song word lengths and store as pickle
        all_lengths = dict()
        font_file = "./html/fonts/Inter-SemiBold.otf" # Becomes parameter to function
        font_name = font_file[(font_file.rindex('/')+1):].split(".")[0]
        pickle_file = './data/songs_{fn}.pkl'.format(fn=font_name)
        font = ImageFont.truetype(font_file, 32)
        if os.path.isfile(pickle_file):
            with open(pickle_file, 'rb') as pkf:
                all_lengths = pickle.load(pkf)
        for word in all_words:
            if not word in all_lengths:
                all_lengths[word] = font.getlength(word)
        with open(pickle_file, 'wb') as out:
            pickle.dump(all_lengths, out)
        print("Word sizes saved to {p}".format(p=pickle_file))

    @classmethod
    def load_length_data(cls, font_name):
        pickle_file = './data/songs_{fn}.pkl'.format(fn=font_name)
        print("Loading data for songs...")
        with open(pickle_file, 'rb') as pkf:
            Song.length_data = pickle.load(pkf)

### TESTING ONLY ###
if __name__ == "__main__":
    pass
