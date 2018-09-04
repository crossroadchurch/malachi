import sqlite3, json
from Chords import Chords
from MalachiExceptions import InvalidSongIdError

class Song():

    def __init__(self, song_id):
        if self.is_valid_song_id(song_id):
            self.song_id = song_id
        else:
            raise InvalidSongIdError(song_id)
        self.slides = []
        self.parts = {}
        self.verse_order = ""
        self.part_slide_count = []
        self.get_nonslide_data() # Must call before updating slides
        self.update_slides()
        return


    def is_valid_song_id(self, id):
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


    def update_slides(self):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT s.lyrics_chords, s.verse_order FROM songs AS s
            WHERE s.id={s_id}
        '''.format(s_id=self.song_id))
        result = cursor.fetchone()

        self.parts = dict([x["part"],x["data"]] for x in json.loads(result[0]))
        self.verse_order = result[1]

        if self.verse_order.strip() == "":
            # Song with no verse order
            slide_temp = list(self.parts)
        else:
            slide_temp = [self.parts[x] for x in self.verse_order.split(" ")]
        self.part_slide_count = []
        for slide in slide_temp:
            slide_sections = slide.split("[br]")
            self.part_slide_count.append(len(slide_sections))
            for slide_section in slide_sections:
                # Transpose slide_section if appropriate:
                if self.resultant_key != "" and self.transpose_by != 0:
                    self.slides.append(Chords.transpose_section(slide_section.strip(), self.song_key, self.transpose_by))
                else:
                    self.slides.append(slide_section.strip())
            
        db.close()


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
       
### TESTING ONLY ###
if __name__ == "__main__":
    pass