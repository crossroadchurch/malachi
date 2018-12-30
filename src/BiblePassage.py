# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=R0912 # Too many branches
# pylint: disable=R0913 # Too many arguments
# pylint: disable=R0914 # Too many local variables
# pylint: disable=R0915 # Too many statements
# pylint: disable=R1705 # Unnecessary "else" after "return".  Disabled for code readability

"""
Represent a Bible verse or range of verses in Malachi and provide
utility methods for searching within Bible versions.
"""

import sqlite3
import json
import re
import math
from PIL import ImageFont
from MalachiExceptions import InvalidVersionError, InvalidVerseIdError,\
    MalformedReferenceError, MissingStyleParameterError


class BiblePassage():
    """
    Represent a Bible verse or range of verses in Malachi and provide
    utility methods for searching within Bible versions.
    """

    def __init__(self, version, start_id, end_id, cur_style, versions):
        if version in versions:
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
        if self.start_id > self.end_id:
            temp = self.end_id
            self.end_id = self.start_id
            self.start_id = temp
        bible_db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = bible_db.cursor()
        cursor.execute('''
            SELECT v.text, v.id FROM Verse AS v
            WHERE v.id>={s_id} AND v.id<={e_id}
        '''.format(s_id=self.start_id, e_id=self.end_id))
        verses = cursor.fetchall()
        self.slides = []
        self.parts = []
        for verse in verses:
            self.parts.append({"part":verse[1], "data":verse[0]})
        bible_db.close()
        try:
            self.paginate_from_style(cur_style)
        except MissingStyleParameterError as style_error:
            raise MissingStyleParameterError(style_error.msg[42:]) from style_error


    def is_valid_verse_id(self, v_id):
        """Check whether a specified verse id exists in the current version of the Bible.

        Arguments:
        v_id -- the verse id to check.

        Return value:
        Boolean
        """
        bible_db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = bible_db.cursor()
        cursor.execute('''
            SELECT v.id FROM Verse AS v
            WHERE v.id = {v_id}
        '''.format(v_id=v_id))
        result = cursor.fetchall()
        bible_db.close()
        if result == []:
            return False
        else:
            return True


    def get_title(self):
        """
        Return the title of this BiblePassage, consisting of the verse or range of
        verses, followed by the Bible version e.g. John 3:16-17 (NIV)
        """
        bible_db = sqlite3.connect('./data/' + self.version + '.sqlite')
        cursor = bible_db.cursor()

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
        bible_db.close()
        return ref

    # pylint: disable=W0613 # capo is unused due to OOP coding of to_JSON method
    def to_JSON(self, capo):
        """
        Return a JSON object containing all the data needed to display this BiblePassage
        to a client.
        """
        return json.dumps({
            "type":"bible",
            "title":self.get_title(),
            "slides":self.slides}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this BiblePassage for saving in a service plan."""
        return json.dumps({
            "type": "bible",
            "version": self.version,
            "start_id": self.start_id,
            "end_id": self.end_id})

    def paginate_from_style(self, style):
        """Paginate the current BiblePassage based on the specified style.

        Arguments:
        style -- the style options to be used (see paginate() for items required in this dict).

        Possible exceptions:
        MissingStyleParameterError - raised if one or more style parameters have not been specified.
        """
        # Test for existance of necessary formatting keys within params
        missing_params = []
        for param in ["aspect-ratio", "font-size-vh", "div-width-vw", "max-lines", "font-file"]:
            if param not in style["params"]:
                missing_params.append(param)
        if missing_params:
            raise MissingStyleParameterError(', '.join(missing_params))
        self.paginate(
            style["params"]["aspect-ratio"],
            style["params"]["font-size-vh"],
            style["params"]["div-width-vw"],
            style["params"]["max-lines"],
            style["params"]["font-file"])

    def paginate(self, aspect_ratio, font_size_vh, div_width_vw, max_lines, font_file):
        """Paginate the current BiblePassage based on the specified style options.

        Arguments:
        aspect_ratio -- the output Screen aspect ratio (width / height).
        font_size_vh -- the font size in vh units.
        div_width_vw -- the width of the div containing the BiblePassage in vw units.
        max_lines -- the maximum number of lines to be displayed at any one time.
        font_file -- the URL of the font being used, relative to the root of Malachi.
        """
        window_height = 800 # Arbitrary value chosen
        window_width = window_height * aspect_ratio
        font_size_px = window_height * font_size_vh / 100
        div_width_px = window_width * div_width_vw / 100
        font = ImageFont.truetype(font_file, math.ceil(font_size_px))
        self.slides = []
        for verse in self.parts:
            verse_words = verse["data"].split(" ")
            line_count, line_start, slide_start = 0, 0, 0
            for i in range(len(verse_words)):
                line_part = ' '.join(verse_words[line_start:i+1])
                size = font.getsize(line_part)
                if size[0] > div_width_px:
                    line_count += 1
                    line_start = i
                    if line_count == max_lines:
                        self.slides.append(' '.join(verse_words[slide_start:i]))
                        slide_start, line_count = i, 0
            # Add on remaining bit of verse
            if slide_start < (len(verse_words)):
                self.slides.append(' '.join(verse_words[slide_start:len(verse_words)]))


    @classmethod
    def get_books(cls, version, versions):
        """
        Return a list of the books in the specified version of the Bible

        Arguments:
        version -- the Bible version to use.

        Possible exceptions:
        InvalidVersionError -- raised if the specified version is not available.
        """
        if version in versions:
            bible_db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = bible_db.cursor()
            cursor.execute('''
                SELECT b.name FROM book AS b
                ORDER BY b.id ASC
            ''')
            books = cursor.fetchall()
            bible_db.close()
            return [x[0] for x in books]
        else:
            raise InvalidVersionError(version)

    @classmethod
    def get_chapter_structure(cls, version, versions):
        """
        Return the chapter structure of the specified version of the Bible.
        The structure is returned as a list of tuples, each tuple of the form
        [book name, number of chapters]

        Arguments:
        version -- the Bible version to use.

        Possible exceptions:
        InvalidVersionError -- raised if the specified version is not available.
        """
        if version in versions:
            bible_db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = bible_db.cursor()
            cursor.execute('''
                SELECT b.name, MAX(v.chapter)
                FROM book AS b INNER JOIN verse AS v ON v.book_id = b.id
                GROUP BY b.name
                ORDER BY b.id ASC
            ''')
            books = cursor.fetchall()
            bible_db.close()
            return [[x[0], x[1]] for x in books]
        else:
            raise InvalidVersionError(version)

    @classmethod
    def text_search(cls, version, search_text, versions):
        """
        Perform a text search on the specified Bible version.
        Return all matching verses in a JSON array.  Each item in the array has the form
        [verse id, book name, chapter number, verse number, verse text]

        Arguments:
        version -- the Bible version to use.
        search_text -- the text to search for.

        Possible exceptions:
        InvalidVersionError -- raised if the specified version is not available.
        """
        if version in versions:
            bible_db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = bible_db.cursor()
            cursor.execute('''
                SELECT v.id, b.name, v.chapter, v.verse, v.text
                FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                WHERE v.text LIKE "%{txt}%"
                ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
            '''.format(txt=search_text))
            verses = cursor.fetchall()
            bible_db.close()
            return json.dumps(verses, indent=2)
        else:
            raise InvalidVersionError(version)

    @classmethod
    def ref_search(cls, version, search_ref, versions):
        """
        Search the specified Bible version for a verse or range of verses.
        Return all matching verses in a JSON array.  Each item in the array has the form
        [verse id, book name, chapter number, verse number, verse text]

        Arguments:
        version -- the Bible version to use.
        search_ref -- the reference to search for (either a single verse or range of verses).

        Possible exceptions:
        InvalidVersionError -- raised if the specified version is not available.
        MalformedReferenceError -- raised if search_ref is not a valid verse reference.
        """
        if version in versions:
            # Determine if this search if for a range of verses or a single verse
            dash_split = search_ref.split("-")
            if len(dash_split) > 2:
                raise MalformedReferenceError(search_ref) # Too many dashes in reference

            # Process part of reference before dash
            # Split into book | (chapter verse)
            ref1 = ' '.join(re.split(r"\s+", dash_split[0]))
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
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch}'\
                            .format(bk=book, ch=verse_split[0]) # e.g. 1 John 2
                    elif len(verse_split) == 2 and verse_split[0].isdigit() \
                        and verse_split[1].isdigit():
                        # e.g. 1 John 2:1
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} \
                            AND v.verse={vs}'.format(bk=book, ch=verse_split[0], vs=verse_split[1])
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
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch}'\
                            .format(bk=book, ch=verse_split[0]) # e.g. Acts 2
                    elif len(verse_split) == 2 and verse_split[0].isdigit() \
                        and verse_split[1].isdigit():
                        # e.g. Acts 2:1
                        where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} \
                            AND v.verse={vs}'.format(bk=book, ch=verse_split[0], vs=verse_split[1])
                    else:
                        raise MalformedReferenceError(search_ref)
            else:
                # Just digits
                raise MalformedReferenceError(search_ref)

            where2_clause = ''
            if len(dash_split) == 2:
                # Process end of reference and add to where_clause
                # If specifying a second reference then the first reference
                #  must be of the form book chapter verse
                if not("b.name" in where_clause and "v.chapter" in where_clause \
                    and "v.verse" in where_clause):
                    raise MalformedReferenceError(search_ref)

                # Only allowing references within the same book
                verse2_split = dash_split[1].replace(' ', '').split(":")
                if len(verse2_split) == 1 and verse2_split[0].isdigit():
                    # Second reference is just a verse in the same chapter
                    if verse2_split[0] > verse_split[1]:
                        # e.g. (1 )John 2:1-5
                        where2_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} \
                            AND v.verse={vs}'.format(bk=book, ch=verse_split[0], vs=verse2_split[0])
                    elif verse2_split[0] == verse_split[1]:
                        where2_clause = '' # e.g. (1 )John 2:1-1
                    else:
                        # Second verse comes before first verse
                        raise MalformedReferenceError(search_ref)
                elif len(verse2_split) == 2 and verse2_split[0].isdigit() \
                    and verse2_split[1].isdigit():
                    # Second reference is a chapter and verse
                    if verse2_split[0] > verse_split[0]:
                        # Second chapter is strictly after first chapter
                        # e.g. (1 )John 2:1-3:1
                        where2_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND \
                            v.verse={vs}'.format(bk=book, ch=verse2_split[0], vs=verse2_split[1])
                    elif verse2_split[0] == verse_split[0]:
                        # Second chapter is same as first chapter
                        if verse2_split[1] > verse_split[1]:
                            # e.g. (1 )John 2:1-2:5
                            where2_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} AND \
                            v.verse={vs}'.format(bk=book, ch=verse2_split[0], vs=verse2_split[1])
                        elif verse2_split[1] == verse_split[1]:
                            where2_clause = '' # e.g. (1 )John 2:1-2:1
                        else:
                            # Second verse comes before first verse
                            raise MalformedReferenceError(search_ref)
                    else:
                        # Second chapter comes before first chapter
                        raise MalformedReferenceError(search_ref)
                else:
                    raise MalformedReferenceError(search_ref)
            # Now to do the actual searching!
            bible_db = sqlite3.connect('./data/' + version + '.sqlite')
            cursor = bible_db.cursor()
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
                if (verse1 is None or verse2 is None):
                    verses = []
                else:
                    cursor.execute('''
                        SELECT v.id, b.name, v.chapter, v.verse, v.text
                        FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                        WHERE v.id >= {v1} AND v.id <= {v2}
                        ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
                    '''.format(v1=verse1[0], v2=verse2[0]))
                    verses = cursor.fetchall()
            bible_db.close()
            return json.dumps(verses, indent=2)
        else:
            raise InvalidVersionError(version)

### TESTING ONLY ###
if __name__ == "__main__":
    pass
