import sqlite3

class BibleReference(object):

    # book, chapter, verse are all ints
    def __init__(self, book:int, chapter:int, verse:int):
        self.book = book
        self.chapter = chapter
        self.verse = verse

    def equals(self, ref2):
        if (self.book==ref2.book and self.chapter==ref2.chapter and self.verse==ref2.verse):
            return True
        else:
            return False
    
    def __str__(self):
        return "[{bk}, {ch}, {vs}]".format(bk=self.book, ch=self.chapter, vs=self.verse)

    @classmethod
    def create_from_id(cls, version, verse_id):
        db = sqlite3.connect('./data/' + version + '.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT b.id, v.chapter, v.verse FROM Verse AS v INNER JOIN Book AS b ON b.id = v.book_id
            WHERE v.id = {vi}
        '''.format(vi=verse_id))
        verse_data = cursor.fetchone()
        db.close()
        return BibleReference(verse_data[0], verse_data[1], verse_data[2])