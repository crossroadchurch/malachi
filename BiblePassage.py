import sqlite3, json, re
from BibleReference import BibleReference

class InvalidVersionError(Exception):
    def __init__(self, version):
        msg = "%s is not a recognised Bible version" % version
        super(InvalidVersionError, self).__init__(msg)

class InvalidReferenceError(Exception):
    def __init__(self, ref, version):
        msg = "%s is not a valid verse in the %s Bible version" % (ref, version)
        super(InvalidReferenceError, self).__init__(msg)

class MalformedReferenceError(Exception):
    def __init__(self, ref):
        msg = "%s is not a valid form for a Bible reference" % ref
        super(MalformedReferenceError, self).__init__(msg)


class BiblePassage():

    BIBLE_VERSIONS = ['NIV', 'KJV']

    def __init__(self, version, start_ref:BibleReference, end_ref:BibleReference):
        if version in BiblePassage.BIBLE_VERSIONS:
            self.version = version
        else:
            raise InvalidVersionError(version)
        if self.is_valid_reference(start_ref):
            self.start_ref = start_ref
        else:
            raise InvalidReferenceError(start_ref, version)
        if self.is_valid_reference(end_ref):
            self.end_ref = end_ref
        else:
            raise InvalidReferenceError(end_ref, version)
        self.check_ref_order()
        self.slides = []
        self.update_slides()
        return

    def check_ref_order(self):

        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT v.id FROM Verse AS v INNER JOIN Book AS b ON b.id = v.book_id
            WHERE b.id = {bk} AND v.chapter = {cp} AND v.verse = {vs}
        '''.format(bk=self.start_ref.book, cp=self.start_ref.chapter, vs=self.start_ref.verse))
        start_id = cursor.fetchone()[0]
        cursor.execute('''
            SELECT v.id FROM Verse AS v INNER JOIN Book AS b ON b.id = v.book_id
            WHERE b.id = {bk} AND v.chapter = {cp} AND v.verse = {vs}
        '''.format(bk=self.end_ref.book, cp=self.end_ref.chapter, vs=self.end_ref.verse))
        end_id = cursor.fetchone()[0]
        db.close()
        if (start_id > end_id):
            temp = self.end_ref
            self.end_ref = self.start_ref
            self.start_ref = temp
        return
        

    def is_valid_reference(self, ref):
        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        cursor.execute('''SELECT v.id FROM Verse AS v INNER JOIN Book AS b ON b.id = v.book_id
            WHERE b.id = {bk} AND v.chapter = {cp} AND v.verse = {vs}
        '''.format(bk=ref.book, cp=ref.chapter, vs=ref.verse))
        result = cursor.fetchall()
        if result == []:
            return False
        else:
            return True


    def update_slides(self):
        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT v.id FROM Verse AS v INNER JOIN Book AS b ON b.id = v.book_id
            WHERE b.id = {bk} AND v.chapter = {cp} AND v.verse = {vs}
        '''.format(bk=self.start_ref.book, cp=self.start_ref.chapter, vs=self.start_ref.verse))
        start_id = cursor.fetchone()[0]
        cursor.execute('''
            SELECT v.id FROM Verse AS v INNER JOIN Book AS b ON b.id = v.book_id
            WHERE b.id = {bk} AND v.chapter = {cp} AND v.verse = {vs}
        '''.format(bk=self.end_ref.book, cp=self.end_ref.chapter, vs=self.end_ref.verse))
        end_id = cursor.fetchone()[0]
        cursor.execute('''
            SELECT v.text FROM Verse AS v
            WHERE v.id>={s_id} AND v.id<={e_id}
        '''.format(s_id=start_id, e_id=end_id))
        verses = cursor.fetchall()
        self.slides = []
        for verse in verses:
            self.slides.append(verse[0])
        db.close()
        return

    def get_title(self):
        db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = db.cursor()
        
        if self.start_ref.equals(self.end_ref):
            cursor.execute('''
                SELECT b.name FROM book AS b
                WHERE b.id = {bk}
            '''.format(bk=self.start_ref.book))
            book_name = cursor.fetchone()[0]
            ref = "{bk} {ch}:{vs} ({ver})".format(
                bk=book_name, 
                ch=self.start_ref.chapter,
                vs=self.start_ref.verse,
                ver=self.version)
        else:
            if self.start_ref.book == self.end_ref.book:
                cursor.execute('''
                    SELECT b.name FROM book AS b
                    WHERE b.id = {bk}
                '''.format(bk=self.start_ref.book))
                book_name = cursor.fetchone()[0]
                if self.start_ref.chapter == self.end_ref.chapter:
                    ref = "{bk} {ch}:{vs1}-{vs2} ({ver})".format(
                        bk=book_name, 
                        ch=self.start_ref.chapter,
                        vs1=self.start_ref.verse,
                        vs2=self.end_ref.verse,
                        ver=self.version)
                else:
                    ref = "{bk} {ch1}:{vs1}-{ch2}:{vs2} ({ver})".format(
                        bk=book_name, 
                        ch1=self.start_ref.chapter,
                        vs1=self.start_ref.verse,
                        ch2=self.end_ref.chapter,
                        vs2=self.end_ref.verse,
                        ver=self.version)
            else:
                cursor.execute('''
                    SELECT b.name FROM book AS b
                    WHERE b.id = {bk}
                '''.format(bk=self.start_ref.book))
                book1_name = cursor.fetchone()[0]
                cursor.execute('''
                    SELECT b.name FROM book AS b
                    WHERE b.id = {bk}
                '''.format(bk=self.end_ref.book))
                book2_name = cursor.fetchone()[0]
                ref = "{bk1} {ch1}:{vs1} - {bk2} {ch2}:{vs2} ({ver})".format(
                        bk1=book1_name, 
                        ch1=self.start_ref.chapter,
                        vs1=self.start_ref.verse,
                        bk2=book2_name,
                        ch2=self.end_ref.chapter,
                        vs2=self.end_ref.verse,
                        ver=self.version)
        db.close()
        return ref

    def to_JSON(self):
        return json.dumps({"type":"bible", "title":self.get_title(), "slides":self.slides}, indent=2)

    def __str__(self):
        return self.get_title()
    
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
    # BiblePassage.ref_search('NIV', 'Jude')
    # BiblePassage.ref_search('NIV', '3   John')
    # BiblePassage.ref_search('NIV', 'Psalm 117')
    # BiblePassage.ref_search('NIV', '3    John   1')
    # BiblePassage.ref_search('NIV', 'John 12 : 21')
    # BiblePassage.ref_search('NIV', '1 John 2:2')
    print(BiblePassage.ref_search('NIV', '1 Jo 2:2-4'))
    # BiblePassage.ref_search('NIV', '1 John 2:2-6:1')
    # BiblePassage.ref_search('NIV', '1 John 6:2-7:21')
    
    pass