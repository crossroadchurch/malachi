import sqlite3, json, re, math
from PIL import ImageFont
from .Chords import Chords
from .MalachiExceptions import InvalidSongIdError, InvalidSongFieldError, MissingStyleParameterError

class Song():

    STR_FIELDS = ['song_book_name', 'title', 'author', 'song_key', 
        'verse_order', 'copyright', 'song_number', 'search_title', 'search_lyrics']
    INT_FIELDS = ['transpose_by']

    def __init__(self, song_id, cur_style):
        if Song.is_valid_song_id(song_id):
            self.song_id = song_id
        else:
            raise InvalidSongIdError(song_id)
        self.slides = []
        self.parts = {}
        self.verse_order = ""
        self.part_slide_count = []
        self.get_nonslide_data() # Must call before paginating slides
        self.paginate_from_style(cur_style)
        return

    @classmethod
    def is_valid_song_id(cls, id):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT s.id FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=id))
        result = cursor.fetchall()
        db.close()
        if result == []:
            return False
        else:
            return True


    def get_nonslide_data(self):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT s.title, s.author, s.song_key, s.transpose_by, s.copyright, s.song_book_name, s.song_number
            FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()
        db.close()
        self.title = result[0]
        self.author = result[1]
        self.song_key = result[2]
        self.transpose_by = result[3]
        if self.song_key != None:
            if self.transpose_by == 0:
                self.resultant_key = self.song_key
            else:
                self.resultant_key = Chords.transpose_chord(self.song_key, self.song_key, self.transpose_by)
        else:
            self.resultant_key = ""
        self.copyright = result[4]
        self.song_book_name = result[5]
        self.song_number = result[6]

    def get_title(self):
        return self.title

    def to_JSON(self, capo):
        # Need to return song transposed by -capo, plus the new key - if the song has chords!
        if self.resultant_key != "":
            if capo == 0:
                p_key = self.resultant_key
                c_slides = self.slides
            else:
                capo_key = Chords.transpose_chord(self.resultant_key, self.resultant_key, -int(capo))
                p_key = "Capo {n} ({c})".format(n=capo, c=capo_key)
                c_slides = []
                for slide in self.slides:
                    c_slides.append(Chords.transpose_section(slide, self.resultant_key, -int(capo)))
        else:
            p_key = ""
            c_slides = self.slides
        return json.dumps({"type":"song", "title":self.title, "slides":c_slides, "played-key": p_key, "verse-order": self.verse_order, "part-counts": self.part_slide_count}, indent=2)

    def to_JSON_full_data(self):
        # Need to transform self.parts to match grammar specified in Malachi Wiki
        tr_parts = []
        for p in self.parts:
            lc_raw = self.parts[p]
            lc_data = ""
            for combined_line in lc_raw.split("\n"):
                if combined_line == "[br]":
                    lc_data = lc_data + "[br]\n"
                else:
                    chords, lyrics = Chords.extract_chords_and_lyrics(combined_line)
                    if chords.strip() == "":
                        lc_data = lc_data + lyrics + "\n"
                    else:
                        lc_data = lc_data + chords + "@\n" + lyrics + "\n"
            part = {"part": p, "data": lc_data}
            tr_parts.append(part)

        return json.dumps({"song-id": self.song_id, "title": self.title, "author": self.author,
                           "song-key": self.song_key, "transpose-by": self.transpose_by,
                           "parts": tr_parts, "verse-order": self.verse_order, "copyright": self.copyright,
                           "song-book-name": self.song_book_name, "song-number": self.song_number})

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        return json.dumps({"type": "song", "song_id": self.song_id})

    def paginate_from_style(self, style):
        # Test for existance of necessary formatting keys within params
        missing_params = []
        for param in ["aspect-ratio", "font-size-vh", "div-width-vw", "max-lines", "font-file"]:
            if param not in style["params"]:
                missing_params.append(param)
        if len(missing_params) > 0:
            raise MissingStyleParameterError(', '.join(missing_params))
        self.paginate(style["params"]["aspect-ratio"],
            style["params"]["font-size-vh"], 
            style["params"]["div-width-vw"],
            style["params"]["max-lines"],
            style["params"]["font-file"])

    def paginate(self, aspect_ratio, font_size_vh, div_width_vw, max_lines, font_file):
        window_height = 800 # Arbitrary value chosen
        window_width = window_height * aspect_ratio
        font_size_px = window_height * font_size_vh / 100
        div_width_px = window_width * div_width_vw / 100
        font = ImageFont.truetype(font_file, math.ceil(font_size_px))
        # print("--fsp: " + str(font_size_px))
        # print("--dwp: " + str(div_width_px))

        # Need to track chords along with words, but not include chords in width calculations
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT s.lyrics_chords, s.verse_order FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()

        self.parts = dict([x["part"],x["data"]] for x in json.loads(result[0]))
        self.verse_order = result[1]

        if self.verse_order is None:
            # Song with no verse order
            slide_temp = list(self.parts)
        else:
            if self.verse_order.strip() == "":
                # Song with no verse order
                slide_temp = list(self.parts)
            else:
                slide_temp = [self.parts[x] for x in self.verse_order.split(" ")]
        
        self.slides = []
        self.part_slide_count = []

        ### FOR EACH V1, C1 etc IN SONG ORDER:
        for slide in slide_temp:
            m_slide_sections = slide.split("[br]") # Mandatory slide breaks
            section_length = 0
            ### FOR EACH MANDATORY SLIDE SECTION
            for m_slide_section in m_slide_sections:
                # Transpose m_slide_section if appropriate:
                if self.resultant_key != "" and self.transpose_by != 0:
                    m_section = Chords.transpose_section(m_slide_section.strip(), self.song_key, self.transpose_by)
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
                        line_part_chorded = ' '.join(line_words[line_start:i+1])
                        line_part = re.sub(r'\[[\w\+#\/]*\]', '', line_part_chorded)
                        size = font.getsize(line_part)
                        # print("  line_part: " + line_part + "  size: " + str(size[0]))
                        if size[0] > div_width_px:
                            # print("  NEW LINE!")
                            line_count += 1
                            line_start = i
                            # Line is longer than an entire slide, so break over two slides
                            # This is a very unlikely case...!
                            if line_count == max_lines:
                                self.slides.append(' '.join(line_words[slide_start:i]))
                                section_length += 1
                                # print("  ADDING SLIDE: " + ' '.join(line_words[slide_start:i]))
                                slide_start, line_count = i, 0
                                pass
                    line_count += 1
                    # print("  Line takes up " + str(line_count) + " display lines")
                    # print("  cur_slide_lines + line_count = " + str(cur_slide_lines+line_count))
                    if (cur_slide_lines + line_count) <= max_lines:
                        # Add current line to current slide
                        if cur_slide_text == "":
                            cur_slide_text = ' '.join(line_words[slide_start:])
                        else:
                            cur_slide_text = cur_slide_text + "\n" + ' '.join(line_words[slide_start:])
                        # print("  cur_slide_text now is: " + cur_slide_text)
                        cur_slide_lines += line_count
                    else:
                        # Start new slide for current line after writing out previous slide
                        self.slides.append(cur_slide_text)
                        # print("  NEW SLIDE: " + cur_slide_text)
                        section_length += 1
                        cur_slide_text = ' '.join(line_words[slide_start:])
                        # print("  cur_slide_text now is: " + cur_slide_text)
                        cur_slide_lines = line_count
                # Add on final slide of section
                self.slides.append(cur_slide_text)
                section_length += 1
            # Update parts length
            self.part_slide_count.append(section_length)
        db.close()
        return

    @classmethod
    def text_search(cls, search_text):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT s.id, s.title
            FROM songs AS s
            WHERE s.search_title LIKE "%{txt}%" OR s.search_lyrics LIKE "%{txt}%"
            ORDER BY s.title ASC
        '''.format(txt=search_text))
        songs = cursor.fetchall()
        db.close()
        return json.dumps(songs, indent=2)
    
    @classmethod
    def create_song(cls, title, fields):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO songs(song_book_name, title, author, song_key, transpose_by, lyrics_chords, verse_order, copyright, song_number, search_title, search_lyrics)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("", "", "", "", 0, "", "", "", "", "", ""))
        db.commit()
        song_id = cursor.lastrowid
        db.close()
        fields["title"] = title
        try:
            # Edit song performs all of the field validation for us
            Song.edit_song(song_id, fields)
        except InvalidSongFieldError as e:
            # Revert changes by deleting Song(song_id)
            db = sqlite3.connect('./data/songs.sqlite')
            cursor = db.cursor()
            cursor.execute('''
                DELETE FROM songs
                WHERE id = {id}
            '''.format(id=song_id))
            db.commit()
            db.close()
            # Raise error with server
            raise InvalidSongFieldError(e.msg[29:]) from e
        return song_id

    @classmethod
    def edit_song(cls, song_id, fields):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT s.id, s.song_key FROM songs AS s
            WHERE s.id = {s_id}
        '''.format(s_id=song_id))
        result = cursor.fetchone()
        db.close()
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
                fields["search_title"] = ''.join(re.findall(r'[\w\s]*', fields["title"].lower()))
        if "song_key" in fields:
            if fields["song_key"] not in Chords.key_list:
                raise InvalidSongFieldError("Unrecognised song key: " + fields["song_key"])
        if "transpose_by" in fields:
            if type(fields["transpose_by"]) is int:
                fields["transpose_by"] = fields["transpose_by"] % 12
            else:
                if fields["transpose_by"].isdigit() == False:
                    raise InvalidSongFieldError("Unrecognised transpose amount: " + fields["transpose_by"])
                else:
                    fields["transpose_by"] = int(fields["transpose_by"]) % 12
        if "lyrics_chords" in fields:
            search_lyrics = ""
            uses_chords = False
            for section in fields["lyrics_chords"]:
                # e.g. section = { "part": "c1", "data": "some [C] lyrics" }
                if "part" in section and "data" in section:
                    # Add data to search_lyrics, less anything in []
                    search_lyrics = search_lyrics + re.sub(r'\[.*?\]', '', section["data"].lower().replace('\n',' ')) + " "
                    # Detect whether chords have been used
                    if uses_chords == False:
                        chord_br_tags = re.findall(r'\[.*?\]', section["data"])
                        if chord_br_tags.count("[br]") < len(chord_br_tags):
                            # Some of the tags are chords
                            uses_chords = True
                            # Check a key has been specified, either in saved record or fields["song_key"]
                            # If fields["song_key"] exists then it is already verified as a valid key
                            if "song_key" not in fields and saved_song_key not in Chords.key_list:
                                raise InvalidSongFieldError("No key specified for a song with chords")
                else:
                    raise InvalidSongFieldError("lyrics_chords is not correctly formatted")
            fields["search_lyrics"] = search_lyrics
        # Once checks complete, create update query for all valid fields in param["fields"] and update song
        update_str = "UPDATE songs SET "
        for field in fields:
            if field in Song.STR_FIELDS:
                update_str = update_str + field + "=\'" + str(fields[field]) + "\', "
            if field in Song.INT_FIELDS:
                update_str = update_str + field + "=" + str(fields[field]) + ", "
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        if len(update_str) > 17:
            if update_str[-2] == ",":
                update_str = update_str[:-2] # Remove trailing comma, if it exists
            update_str = update_str + " WHERE id=" + str(song_id)
            cursor.execute(update_str)
            db.commit()
        if "lyrics_chords" in fields:
            cursor.execute('''
                UPDATE songs
                SET lyrics_chords = ?
                WHERE id = ?
            ''',(json.dumps(fields["lyrics_chords"]), song_id))
            db.commit()
        db.close()
        return


### TESTING ONLY ###
if __name__ == "__main__":
    # Song.edit_song(1759,{"title": "A new hope", "song_key": "D", "transpose_by": 3, "author": "AN Other",
    #     "lyrics_chords": [
    #         {"part":"v1", "data": "It's a[br] verse\nwith some lyrics"},
    #         {"part":"c1", "data": "This is a [A/C#sus4]chorus"}
    #     ]})
    Song.create_song("", {"song_key":"E"})
    pass