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