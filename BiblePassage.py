import sqlite3, json
from BibleReference import BibleReference

class InvalidVersionError(Exception):
    def __init__(self, version):
        msg = "%s is not a recognised Bible version" % version
        super(InvalidVersionError, self).__init__(msg)

class InvalidReferenceError(Exception):
    def __init__(self, ref, version):
        msg = "%s is not a valid verse in the %s Bible version" % (ref, version)
        super(InvalidReferenceError, self).__init__(msg)


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

### TESTING ONLY ###
if __name__ == "__main__":
    #print(BiblePassage.get_chapter_structure('NIV'))
    pass
    # b = BiblePassage('NIV', BibleReference(1, 3, 2), BibleReference(1,2,20))
    # print(b.to_JSON())
    #print(b.is_valid_reference(BibleReference(64,1,21)))