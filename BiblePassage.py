import sqlite3, json, re
from MalachiExceptions import InvalidVersionError, InvalidVerseIdError, MalformedReferenceError

class BiblePassage():

    BIBLE_VERSIONS = ['NIV', 'KJV']

    def __init__(self, version, start_id, end_id):
        if version in BiblePassage.BIBLE_VERSIONS:
            self.version = version
        else:
            raise InvalidVersionError(version)
        if self.is_valid_verse_id(start_id):
            self.start_id = start_id
        else:
            raise InvalidVerseIdError(start_id, version)
        if self.is_valid_verse_id(end_id):
            self.end_id = end_id
        else:
            raise InvalidVerseIdError(end_id, version)
        if (self.start_id > self.end_id):
            temp = self.end_id
            self.end_id = self.start_id
            self.start_id = temp
        self.slides = []
        self.update_slides()
        return


    def is_valid_verse_id(self, id):
        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT v.id FROM Verse AS v
            WHERE v.id = {v_id}
        '''.format(v_id=id))
        result = cursor.fetchall()
        db.close()
        if result == []:
            return False
        else:
            return True


    def update_slides(self):
        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT v.text, v.id FROM Verse AS v
            WHERE v.id>={s_id} AND v.id<={e_id}
        '''.format(s_id=self.start_id, e_id=self.end_id))
        verses = cursor.fetchall()
        self.slides = []
        self.parts = []
        for verse in verses:
            self.slides.append(verse[0])
            self.parts.append({"part":verse[1], "data":verse[0]})
        db.close()

    
    def get_title(self):
        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        
        if self.start_id == self.end_id:
            cursor.execute('''
                SELECT b.name, v.chapter, v.verse FROM book AS b INNER JOIN verse AS v on v.book_id = b.id
                WHERE v.id = {v_id}
            '''.format(v_id=self.start_id))
            result = cursor.fetchone()
            ref = "{bk} {ch}:{vs} ({ver})".format(
                bk=result[0], 
                ch=result[1],
                vs=result[2],
                ver=self.version)
        else:
            # Get book, chapter, verse data for start and end ids
            cursor.execute('''
                SELECT b.name, v.chapter, v.verse FROM book AS b INNER JOIN verse AS v on v.book_id = b.id
                WHERE v.id = {v_id}
            '''.format(v_id=self.start_id))
            start_result = cursor.fetchone()

            cursor.execute('''
                SELECT b.name, v.chapter, v.verse FROM book AS b INNER JOIN verse AS v on v.book_id = b.id
                WHERE v.id = {v_id}
            '''.format(v_id=self.end_id))
            end_result = cursor.fetchone()

            start_book = start_result[0]
            end_book = end_result[0]
            start_chapter = start_result[1]
            end_chapter = end_result[1]
            start_verse = start_result[2]
            end_verse = end_result[2]

            if start_book == end_book:
                if start_chapter == end_chapter:
                    ref = "{bk} {ch}:{vs1}-{vs2} ({ver})".format(
                        bk=start_book, 
                        ch=start_chapter,
                        vs1=start_verse,
                        vs2=end_verse,
                        ver=self.version)
                else:
                    ref = "{bk} {ch1}:{vs1}-{ch2}:{vs2} ({ver})".format(
                        bk=start_book, 
                        ch1=start_chapter,
                        vs1=start_verse,
                        ch2=end_chapter,
                        vs2=end_verse,
                        ver=self.version)
            else:
                ref = "{bk1} {ch1}:{vs1} - {bk2} {ch2}:{vs2} ({ver})".format(
                        bk1=start_book, 
                        ch1=start_chapter,
                        vs1=start_verse,
                        bk2=end_book,
                        ch2=end_chapter,
                        vs2=end_verse,
                        ver=self.version)
        db.close()
        return ref


    def to_JSON(self, capo):
        return json.dumps({"type":"bible", "title":self.get_title(), "slides":self.slides}, indent=2)

    def to_JSON_raw_pagination(self):
        return json.dumps({"parts":self.parts}, indent=2)

    def __str__(self):
        return self.get_title()
    
    def save_to_JSON(self):
        return json.dumps({"type": "bible", "version": self.version, "start_id": self.start_id, "end_id": self.end_id})

    @classmethod
    def get_versions(cls):
        return cls.BIBLE_VERSIONS

    @classmethod
    def get_books(cls, version):
        if version in BiblePassage.BIBLE_VERSIONS:
            db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = db.cursor()
            cursor.execute('''
                SELECT b.name FROM book AS b
                ORDER BY b.id ASC
            ''')
            books = cursor.fetchall()
            db.close()
            return [x[0] for x in books]
        else:
            raise InvalidVersionError(version)

    @classmethod
    def get_chapter_structure(cls, version):
        if version in BiblePassage.BIBLE_VERSIONS:
            db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = db.cursor()
            cursor.execute('''
                SELECT b.name, MAX(v.chapter)
                FROM book AS b INNER JOIN verse AS v ON v.book_id = b.id
                GROUP BY b.name
                ORDER BY b.id ASC
            ''')
            books = cursor.fetchall()
            db.close()
            return [[x[0], x[1]] for x in books]
        else:
            raise InvalidVersionError(version)

    @classmethod
    def text_search(cls, version, search_text):
        if version in BiblePassage.BIBLE_VERSIONS:
            db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = db.cursor()
            cursor.execute('''
                SELECT v.id, b.name, v.chapter, v.verse, v.text
                FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                WHERE v.text LIKE "%{txt}%"
                ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
            '''.format(txt=search_text))
            verses = cursor.fetchall()
            db.close()
            return json.dumps(verses, indent=2)
        else:
            raise InvalidVersionError(version)

    @classmethod
    def ref_search(cls, version, search_ref):
        if version in BiblePassage.BIBLE_VERSIONS:
            # Determine if this search if for a range of verses or a single verse
            dash_split = search_ref.split("-")
            if len(dash_split) > 2:
                raise MalformedReferenceError(search_ref) # Too many dashes in reference

            # Process part of reference before dash
            # Split into book | (chapter verse)
            ref1 = ' '.join(re.split("\s+", dash_split[0]))
            word_split = ref1.split(" ")
            if word_split[0].isdigit() and len(word_split) >= 2:
                # Book that starts with a digit
                book = word_split[0] + " " + word_split[1]
                if len(word_split) == 2:
                    # Just a book that starts with a digit
                    where_clause = 'WHERE b.name LIKE "{bk}%"'.format(bk=book) # e.g. 1 John
                else:
                    ch_verse_part = (''.join(word_split[2:])).replace(' ', '')
                    verse_split = ch_verse_part.split(":")
                    if len(verse_split) == 1 and verse_split[0].isdigit():
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch}'.format(bk=book, ch=verse_split[0]) # e.g. 1 John 2
                    elif len(verse_split) == 2 and verse_split[0].isdigit() and verse_split[1].isdigit():
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND v.verse={vs}'.format(bk=book, ch=verse_split[0], vs=verse_split[1]) # e.g. 1 John 2:1
                    else:
                        raise MalformedReferenceError(search_ref)
                    
            elif not word_split[0].isdigit(): 
                # Book that does not start with a digit
                book = word_split[0]
                if len(word_split) == 1:
                    # Just a book
                    where_clause = 'WHERE b.name LIKE "{bk}%"'.format(bk=book) # e.g. Acts
                else:
                    ch_verse_part = (''.join(word_split[1:])).replace(' ', '')
                    verse_split = ch_verse_part.split(":")
                    if len(verse_split) == 1 and verse_split[0].isdigit():
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch}'.format(bk=book, ch=verse_split[0]) # e.g. Acts 2
                    elif len(verse_split) == 2 and verse_split[0].isdigit() and verse_split[1].isdigit():
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND v.verse={vs}'.format(bk=book, ch=verse_split[0], vs=verse_split[1]) # e.g. Acts 2:1
                    else:
                        raise MalformedReferenceError(search_ref)
            else:
                # Just digits
                raise MalformedReferenceError(search_ref)

            where2_clause = ''
            if len(dash_split) == 2:
                # Process end of reference and add to where_clause
                # If specifying a second reference then the first reference must be of the form book chapter verse
                if not("b.name" in where_clause and "v.chapter" in where_clause and "v.verse" in where_clause):
                    raise MalformedReferenceError(search_ref)
                
                # Only allowing references within the same book
                verse2_split = dash_split[1].replace(' ', '').split(":")
                if len(verse2_split) == 1 and verse2_split[0].isdigit():
                    # Second reference is just a verse in the same chapter
                    if verse2_split[0] > verse_split[1]:
                        where2_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND v.verse={vs}'.format(bk=book, ch=verse_split[0], vs=verse2_split[0]) # e.g. (1 )John 2:1-5
                    elif verse2_split[0] == verse_split[1]:
                        where2_clause = '' # e.g. (1 )John 2:1-1
                    else:
                        raise MalformedReferenceError(search_ref) # Second verse comes before first verse
                elif len(verse2_split) == 2 and verse2_split[0].isdigit() and verse2_split[1].isdigit():
                    # Second reference is a chapter and verse
                    if verse2_split[0] > verse_split[0]:
                        # Second chapter is strictly after first chapter
                        where2_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND v.verse={vs}'.format(bk=book, ch=verse2_split[0], vs=verse2_split[1]) # e.g. (1 )John 2:1-3:1
                    elif verse2_split[0] == verse_split[0]:
                        # Second chapter is same as first chapter
                        if verse2_split[1] > verse_split[1]:
                            where2_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND v.verse={vs}'.format(bk=book, ch=verse2_split[0], vs=verse2_split[1]) # e.g. (1 )John 2:1-2:5
                        elif verse2_split[1] == verse_split[1]:
                            where2_clause = '' # e.g. (1 )John 2:1-2:1
                        else:
                            raise MalformedReferenceError(search_ref) # Second verse comes before first verse
                    else:
                        raise MalformedReferenceError(search_ref) # Second chapter comes before first chapter
                else:
                    raise MalformedReferenceError(search_ref)
            
            # Now to do the actual searching!
            db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = db.cursor()
                
            if where2_clause == '':
                cursor.execute('''
                    SELECT v.id, b.name, v.chapter, v.verse, v.text
                    FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                    {where}
                    ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
                '''.format(where=where_clause))
                verses = cursor.fetchall()
            else:
                cursor.execute('''
                    SELECT v.id
                    FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                    {where}
                '''.format(where=where_clause))
                verse1 = cursor.fetchone()
                cursor.execute('''
                    SELECT v.id
                    FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                    {where}
                '''.format(where=where2_clause))
                verse2 = cursor.fetchone()
                if (verse1 == None or verse2 == None):
                    verses = []
                else:
                    cursor.execute('''
                        SELECT v.id, b.name, v.chapter, v.verse, v.text
                        FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                        WHERE v.id >= {v1} AND v.id <= {v2}
                        ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
                    '''.format(v1=verse1[0], v2=verse2[0]))
                    verses = cursor.fetchall()
            db.close()
            return json.dumps(verses, indent=2)
            
        else:
            raise InvalidVersionError(version)

### TESTING ONLY ###
if __name__ == "__main__":
    pass