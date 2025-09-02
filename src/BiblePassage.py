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
import pickle
from PIL import ImageFont
from MalachiExceptions import InvalidVersionError, InvalidVerseIdError,\
    MalformedReferenceError, MissingStyleParameterError, MatchingVerseIdError,\
    UnknownReferenceError


class BiblePassage():
    """
    Represent a Bible verse or range of verses in Malachi and provide
    utility methods for searching within Bible versions.
    """

    version_length_data = dict()

    def __init__(self, version, start_id, end_id, cur_style, versions):
        if not version in versions:
            raise InvalidVersionError(version)
        self.version = version
        if not self.is_valid_verse_id(start_id):
            raise InvalidVerseIdError(start_id, version)
        if not self.is_valid_verse_id(end_id):
            raise InvalidVerseIdError(end_id, version)
        self.start_id = int(start_id)
        self.end_id = int(end_id)
        if self.start_id > self.end_id:
            temp = self.end_id
            self.end_id = self.start_id
            self.start_id = temp
        bible_db, cursor = BiblePassage.db_connect(self.version)
        cursor.execute('''
            SELECT v.text, v.id, v.chapter, v.verse FROM Verse AS v
            WHERE v.id>={s_id} AND v.id<={e_id}
        '''.format(s_id=self.start_id, e_id=self.end_id))
        verses = cursor.fetchall()
        self.slides = []
        self.parallel_slides = []
        self.parallel_version = ""
        self.parts = []
        for verse in verses:
            self.parts.append({
                "part": verse[1],
                "data": verse[0],
                "short_ref": str(verse[3])
            })
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
        bible_db, cursor = BiblePassage.db_connect(self.version)
        cursor.execute('''
            SELECT v.id FROM Verse AS v
            WHERE v.id = {v_id}
        '''.format(v_id=v_id))
        result = cursor.fetchall()
        bible_db.close()
        if result == []:
            return False
        return True


    def get_title(self):
        """
        Return the title of this BiblePassage, consisting of the verse or range of
        verses, followed by the Bible version e.g. John 3:16-17 (NIV)
        """
        bible_db, cursor = BiblePassage.db_connect(self.version)

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
        if self.parallel_version != "":
            ref = ref[:-1] + " + " + self.parallel_version + ")"
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
            "version":self.version,
            "slides":self.slides,
            "parallel_slides":self.parallel_slides,
            "parallel_version":self.parallel_version}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this BiblePassage for saving in a service plan."""
        return json.dumps({
            "type": "bible",
            "version": self.version,
            "parallel_version": self.parallel_version,
            "start_id": self.start_id,
            "end_id": self.end_id})

    def export_to_JSON(self, export_zip):
        """
        Return a JSON object representing this BiblePassage for exporting to another
        instance of Malachi.
        """
        return json.dumps({
            "type": "bible",
            "version": self.version,
            "ref": self.get_title()[:-(len(self.version)+3)]
        })

    @classmethod
    def import_from_JSON(cls, json_data, cur_style, versions):
        """
        Return a BiblePassage object corresponding to the passage stored in json_data,
        which has been exported (possibly from another instance of Malachi) using the
        export_to_JSON method.

        Precondition: json_data["type"] == "bible"
        """
        try:
            verses = json.loads(BiblePassage.ref_search(json_data["version"], json_data["ref"], versions))
            start_verse = verses[0][0]
            end_verse = verses[-1][0]
            passage = BiblePassage(json_data["version"], start_verse, end_verse, cur_style, versions)
            if "parallel_version" in json_data and json_data["parallel_version"] != "":
                passage.parallel_paginate_from_style(cur_style, json_data["parallel_version"], versions)
            return passage
        except InvalidVersionError as e:
            raise InvalidVersionError(json_data["version"])
        except MalformedReferenceError as e:
            raise MalformedReferenceError(json_data["ref"])
        except UnknownReferenceError as e:
            raise UnknownReferenceError(json_data["ref"])
            

    def paginate_from_style(self, style):
        """Paginate the current BiblePassage based on the specified style.

        Arguments:
        style -- the style options to be used (see paginate_to_lines() for items required in this dict).

        Possible exceptions:
        MissingStyleParameterError - raised if one or more style parameters have not been specified.
        """
        # Test for existance of necessary formatting keys within params
        missing_params = []
        for param in ["aspect-ratio", "font-size-vh", "div-width-vw", "max-bible-lines", "font-file"]:
            if param not in style:
                missing_params.append(param)
        if missing_params:
            raise MissingStyleParameterError(', '.join(missing_params))
        lines = BiblePassage.paginate_to_lines(self, 
            style["aspect-ratio"], style["font-size-vh"], style["div-width-vw"], style["font-file"])
        capacity = int(style["max-bible-lines"])
        self.slides = []
        self.parallel_slides = []
        self.parallel_version = ""
        for i in range(math.ceil(len(lines)/capacity)):
            self.slides.append(' '.join(lines[capacity*i:capacity*(i+1)]))

    @classmethod
    def paginate_to_lines(cls, passage, aspect_ratio, font_size_vh, div_width_vw, font_file):
        """Paginate a BiblePassage based on the specified style options into an array of lines of text.

        Arguments:
        passage -- the BiblePassage being paginated
        aspect_ratio -- the output Screen aspect ratio (width / height).
        font_size_vh -- the font size in vh units.
        div_width_vw -- the width of the div containing the BiblePassage in vw units.
        font_file -- the URL of the font being used, relative to the root of Malachi.
        """
        # Max width of div based on font size of 32 (used in size calculations stored in pickle)
        MAX_WIDTH = 32 * float(aspect_ratio) * int(div_width_vw) / int(font_size_vh)
        SPACE_WIDTH = 7.9375
        font = ImageFont.truetype(font_file, 32)
        lines = []
        parts_refs_tags = ["<sup>" + v["short_ref"] + "</sup>" + v["data"] for v in passage.parts]
        parts_refs_simple = [v["short_ref"] + v["data"] for v in passage.parts]
        passage_tags = ' '.join(parts_refs_tags)
        passage_tags_simple = ' '.join(parts_refs_simple)
        verse_words = passage_tags_simple.split(" ")
        verse_words_tags = passage_tags.split(" ")
        line_start = 0
        line_length = -1 * SPACE_WIDTH
        for idx, tagged_word in enumerate(verse_words_tags):
            tagged_sections = re.split(r"(<sup>[0-9]+</sup>)", tagged_word)
            for section in tagged_sections:
                line_length += SPACE_WIDTH
                if section in BiblePassage.version_length_data[passage.version]:
                    section_length = BiblePassage.version_length_data[passage.version][section]
                elif section != "":
                    print("Not found in dict: {s}".format(s=section))
                    if section[0:5] == "<sup>":
                        # Processing a verse tag <sup>N</sup>, at 0.5em, with 0.5em right spacing
                        section_length = 0.5*font.getlength(section[5:-6]) + 16
                    else:
                        section_length = font.getlength(section)
                else: # section == "", so negate the addition of the space
                    section_length = SPACE_WIDTH
                line_length += section_length
                if line_length > MAX_WIDTH:
                    lines.append(' '.join(verse_words_tags[line_start:idx]))
                    line_start = idx
                    line_length = section_length
        # Add on remaining bit of passage
        if line_start < (len(verse_words)):
            lines.append(' '.join(verse_words_tags[line_start:len(verse_words)]))
        return lines

    @classmethod
    def find_verse_starts(cls, lines):
        """
        Return a list of the line indices in "lines" that contain the start of a verse.

        Arguments:
        lines -- a BiblePassage split into a list, each element being a paginated line of text.
        """
        starts = []
        for count, line in enumerate(lines):
            if line.count("<sup>") > 0:
                starts.extend([count]*line.count("<sup>"))
        starts.append(len(lines))
        return starts

    def parallel_paginate_from_style(self, style, version2, versions):
        """Parallel paginate the current BiblePassage based on the specified style.

        Arguments:
        style -- the style options to be used (see parallel_paginate() for items required in this dict).
        version2 -- the version to be used for the parallel translation
        versions -- a list of the available Bible versions

        Possible exceptions:
        MissingStyleParameterError - raised if one or more style parameters have not been specified.
        InvalidVersionError - raised if version2 is not a valid Bible version
        InvalidVerseId - raised if either the start or end verse of the passage is invalid
        MatchingVerseIdError - raised if either the start or end verse of the passage cannot be determined
          in the new version.
        """
        missing_params = []
        for param in ["aspect-ratio", "pl-font-size-vh", "pl-width-vw", "pl-max-lines", "font-file"]:
            if param not in style:
                missing_params.append(param)
        if missing_params:
            raise MissingStyleParameterError(', '.join(missing_params))
        # Create BiblePassage for version2
        try:
            start_id2 = BiblePassage.translate_verse_id(self.start_id, self.version, version2, versions)
            end_id2 = BiblePassage.translate_verse_id(self.end_id, self.version, version2, versions)
            passage2 = BiblePassage(version2, start_id2, end_id2, style, versions)
            self.parallel_paginate(passage2, version2, style["aspect-ratio"], style["pl-font-size-vh"], 
            style["pl-width-vw"], style["pl-max-lines"], style["font-file"])
        except InvalidVersionError as e:
            raise InvalidVersionError(e.msg[40:]) from e
        except InvalidVerseIdError as e:
            raise InvalidVerseIdError(e.msg[53:].split(", ")[0], e.msg[53:].split(", ")[1]) from e
        except MatchingVerseIdError as e:
            raise MatchingVerseIdError(e.msg[55:].split(", ")[0], 
                e.msg[55:].split(", ")[1], e.msg[55:].split(", ")[2]) from e

    def process_overflow(self, s_lines1, s_lines2, s_needed, need1, need2, capacity):
        # Process slides where at least one translation overflows.
        # The translation that needs the most slides is the first one (s_lines1, s_needed, need1)
        # Process translation that uses the most slides
        # Initial slide
        need1 -= (capacity - s_lines1[-1])
        s_lines1[-1] = capacity
        # Full slides
        while need1 >= capacity:
            s_lines1.append(capacity)
            need1 -= capacity
        # Final slide, might be empty
        s_lines1.append(need1)
        # Now process translation using partial slides
        if math.ceil(need2 / s_needed) <= (capacity - s_lines2[-1]):
            # Can fit verse partition into first slide without overflow
            verse_partition = [need2 // s_needed] * s_needed
            for i in range(need2 % s_needed):
                verse_partition[i] = verse_partition[i]+1
        else:
            # Default verse partition would overflow first slide
            first2 = capacity - s_lines2[-1]
            need2 -= (capacity - s_lines2[-1])
            s_needed_a  = s_needed - 1
            verse_partition = [need2 // s_needed_a] * s_needed_a
            for i in range(need2 % s_needed_a):
                verse_partition[i] += 1
            # Prepend initial slide, which uses all available capacity
            verse_partition.insert(0, first2)
        # Add partitioned verse to slides
        s_lines2[-1] += verse_partition[0]
        for i in range(1, len(verse_partition)):
            s_lines2.append(verse_partition[i])

    def parallel_paginate(self, passage2, version2, aspect_ratio, font_size_vh, div_width_vw, max_lines, font_file):
        """Parallel paginate a BiblePassage based on the specified style options, updating self.slides and
        self.parallel_slides with the paginated main and parallel translations respectively..

        Arguments:
        passage2 -- the parallel BiblePassage (self translated into version "version2")
        version2 -- the Bible version used for passage2
        aspect_ratio -- the output Screen aspect ratio (width / height).
        font_size_vh -- the font size used for the parallel divs, given in vh units.
        div_width_vw -- the width of the parallel divs in vw units.
        font_file -- the URL of the font being used, relative to the root of Malachi.
        """
        lines1 = BiblePassage.paginate_to_lines(self, aspect_ratio, font_size_vh, div_width_vw, font_file)
        lines2 = BiblePassage.paginate_to_lines(passage2, aspect_ratio, font_size_vh, div_width_vw, font_file)
        l_starts1 = BiblePassage.find_verse_starts(lines1)
        l_starts2 = BiblePassage.find_verse_starts(lines2)
        capacity = int(max_lines)
        slide_lines1, slide_lines2 = [0], [0] # Stores number of lines held on each slide
        for v in range(len(l_starts1) - 1):
            needed1 = l_starts1[v+1] - l_starts1[v]
            needed2 = l_starts2[v+1] - l_starts2[v]
            if needed1 <= capacity-slide_lines1[-1] and needed2 <= capacity-slide_lines2[-1]:
                # Both verses fit completely on the current slide
                slide_lines1[-1] += needed1
                slide_lines2[-1] += needed2
            else:
                # One or both verses overflow the current slide
                slides_needed1 = math.ceil((needed1+slide_lines1[-1])/capacity)
                slides_needed2 = math.ceil((needed2+slide_lines2[-1])/capacity)
                if slides_needed1 >= slides_needed2:
                    self.process_overflow(slide_lines1, slide_lines2, 
                        slides_needed1, needed1, needed2, capacity)
                else:
                    self.process_overflow(slide_lines2, slide_lines1, 
                        slides_needed2, needed2, needed1, capacity)
                # Sync check: slide_lines1 and slide_lines2 have same length
                if len(slide_lines1) < len(slide_lines2):
                    while len(slide_lines1) < len(slide_lines2):
                        slide_lines1.append(0)
                if len(slide_lines2) < len(slide_lines1):
                    while len(slide_lines2) < len(slide_lines1):
                        slide_lines2.append(0)
            # End of slide encountered?
            if slide_lines1[-1] == capacity or slide_lines2[-1] == capacity:
                # Put start of next verse on new slide
                slide_lines1.append(0)
                slide_lines2.append(0)
        slides1 = []
        slide_idx1 = 0
        for i in slide_lines1:
            slides1.append(' '.join(lines1[slide_idx1:slide_idx1+i]))
            slide_idx1 += i
        slides2 = []
        slide_idx2 = 0
        for i in slide_lines2:
            slides2.append(' '.join(lines2[slide_idx2:slide_idx2+i]))
            slide_idx2 += i
        self.slides = slides1
        self.parallel_slides = slides2
        self.parallel_version = version2

    @classmethod
    def get_books(cls, version, versions):
        """
        Return a list of the books in the specified version of the Bible

        Arguments:
        version -- the Bible version to use.

        Possible exceptions:
        InvalidVersionError -- raised if the specified version is not available.
        """
        if not version in versions:
            raise InvalidVersionError(version)
        bible_db, cursor = BiblePassage.db_connect(version)
        cursor.execute('''
            SELECT b.name FROM book AS b
            ORDER BY b.id ASC
        ''')
        books = cursor.fetchall()
        bible_db.close()
        return [x[0] for x in books]

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
        if not version in versions:
            raise InvalidVersionError(version)
        bible_db, cursor = BiblePassage.db_connect(version)
        cursor.execute('''
            SELECT b.name, MAX(v.chapter)
            FROM book AS b INNER JOIN verse AS v ON v.book_id = b.id
            GROUP BY b.name
            ORDER BY b.id ASC
        ''')
        books = cursor.fetchall()
        bible_db.close()
        return [[x[0], x[1]] for x in books]

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
        if not version in versions:
            raise InvalidVersionError(version)
        bible_db, cursor = BiblePassage.db_connect(version)
        cursor.execute('''
            SELECT v.id, b.name, v.chapter, v.verse, v.text
            FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
            WHERE v.text LIKE "%{txt}%"
            ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
        '''.format(txt=search_text))
        verses = cursor.fetchall()
        bible_db.close()
        return json.dumps(verses, indent=2)

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
        UnknownReferenceError -- raised if search_ref is not found in the current version.
        """
        if not version in versions:
            raise InvalidVersionError(version)
        # Result groups of regex are:
        #   0: Book
        #   1,2,3,4: Chapter_1, Verse_1, Chapter_2, Verse_2 for multi chapter reference e.g. Eph 3:1-4:5
        #   5,6,7: Chapter, Verse_1, Verse_2 for single chapter reference e.g. Eph 3:1-5
        #   8,9: Chapter, Verse for single verse reference e.g. Eph 3:1
        #   10: Chapter for complete chapter reference e.g. Eph 3
        #   1-4,5-7,8-9,10 are mutually exclusive, 0 appears in all results
        ref_regex = r"([123 ]{0,2}\D+)(?:(?:(\d+):(\d+)\s*-\s*(\d+):(\d+))|(?:(\d+):(\d+)\s*-\s*(\d+))|(?:(\d+):(\d+))|(\d+)|$)"
        result = re.search(ref_regex, search_ref)
        groups = result.groups()
        book = groups[0].strip()
        where_clause2 = ''
        if groups[1]: # Multi chapter reference e.g. Eph 3:1-4:5
            if int(groups[1]) > int(groups[3]): # Error e.g Eph 4:1-3:1
                raise MalformedReferenceError(search_ref)
            elif int(groups[1]) == int(groups[3]) and int(groups[2])>int(groups[4]): # Error e.g. Eph 3:5-3:1
                raise MalformedReferenceError(search_ref)
            where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} '\
                'AND v.verse={vs}'.format(bk=book, ch=groups[1], vs=groups[2])
            where_clause2 = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} '\
                'AND v.verse={vs}'.format(bk=book, ch=groups[3], vs=groups[4])
        elif groups[5]: # Single chapter reference e.g. Eph 3:1-5
            if int(groups[6]) > int(groups[7]): # Error e.g. Eph 3:5-1
                raise MalformedReferenceError(search_ref)
            where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} '\
                'AND v.verse={vs}'.format(bk=book, ch=groups[5], vs=groups[6])
            where_clause2 = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} '\
                'AND v.verse={vs}'.format(bk=book, ch=groups[5], vs=groups[7])
        elif groups[8]: # Single verse reference e.g. Eph 3:1
            where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch} '\
                'AND v.verse={vs}'.format(bk=book, ch=groups[8], vs=groups[9])
        elif groups[10]: # Complete chapter reference e.g. Eph 3
            where_clause = 'WHERE b.name LIKE "{bk}%" AND v.chapter={ch}'\
                .format(bk=book, ch=groups[10])
        else:
            where_clause = 'WHERE b.name LIKE "{bk}%"'.format(bk=book)
        # Now to do the actual searching!
        bible_db, cursor = BiblePassage.db_connect(version)
        if where_clause2 == '':
            cursor.execute('''
                SELECT v.id, b.name, v.chapter, v.verse, v.text
                FROM verse AS v INNER JOIN book AS b on b.id = v.book_id
                {where}
                ORDER BY b.id ASC, v.chapter ASC, v.verse ASC
            '''.format(where=where_clause))
            verses = cursor.fetchall()
            if verses == []:
                raise UnknownReferenceError(search_ref)        
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
            '''.format(where=where_clause2))
            verse2 = cursor.fetchone()
            if (verse1 is None or verse2 is None):
                raise UnknownReferenceError(search_ref)
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
    
    @classmethod
    def translate_verse_id(cls, src_id, src_version, dest_version, bible_versions):
        """
        Find a verse in a different version of the Bible and return its id.

        Arguments:
        src_id -- the verse id in the source version
        src_version -- the Bible version to use for src_id
        dest_version -- the Bible version to use for the returned id
        bible_versions -- a list of the available Bible versions

        Possible exceptions:
        InvalidVersionError -- raised if either of the versions are not available.
        InvalidVerseIdError -- raised if src_id is not a valid id in src_version.
        MatchingVerseIdError -- raised if a corresponding verse cannot be found in dest_version.
        """
        if src_version not in bible_versions:
            raise InvalidVersionError(src_version)
        if dest_version not in bible_versions:
            raise InvalidVersionError(dest_version)
        bible_db, cursor = BiblePassage.db_connect(src_version)
        cursor.execute('''
            SELECT v.id, b.name, v.chapter, v.verse
            FROM verse AS v INNER JOIN book AS b ON v.book_id = b.id
            WHERE v.id = {id}
        '''.format(id=src_id))
        old_verse = cursor.fetchone()
        if not old_verse:
            raise InvalidVerseIdError(src_id, src_version)
        bible_db.close()
        bible_db, cursor = BiblePassage.db_connect(dest_version)
        cursor.execute('''
            SELECT v.id
            FROM verse AS v INNER JOIN book AS b ON v.book_id = b.id
            WHERE b.name LIKE "{bk}" AND v.chapter = {ch} AND v.verse = {vs}
        '''.format(bk=old_verse[1], ch=old_verse[2], vs=old_verse[3]))
        new_result = cursor.fetchone()
        if not new_result:
            raise MatchingVerseIdError(src_id, src_version, dest_version)
        bible_db.close()
        return new_result[0]

    @classmethod
    def db_connect(cls, version):
        bible_db = sqlite3.connect('./data/' + version + '.sqlite')
        cursor = bible_db.cursor()
        return bible_db, cursor

    @classmethod
    def generate_word_sizes(cls, version, font_file):
        # TODO: Add exception handling if version or font don't exist
        bible_db, cursor = BiblePassage.db_connect(version)
        
        cursor.execute('''
            SELECT v.id, v.text
            FROM verse AS v
            ORDER BY v.id
        ''')
        verses = cursor.fetchall()
        words = set()
        word_count = 0
        for verse in verses:
            word_count += len(verse[1].split(' '))
            words.update(verse[1].split(' '))
        print('{u} unique words detected in {v} ({t} total)'.format(u=len(words),t=word_count,v=version))
        print('Saving word sizes...')
        bible_db.close()
        # Store sizes of (unique) words found in Bible version
        font = ImageFont.truetype(font_file, 32)
        word_sizes = dict()
        for word in words:
            word_sizes[word] = font.getlength(word)
        # Store sizes of verse numbers, displayed at 0.5em with right spacing
        ref_font = ImageFont.truetype(font_file, 16)
        for v_num in range(1,177):
            word_sizes["<sup>{v}</sup>".format(v=v_num)] = ref_font.getlength(str(v_num)) + 16
        # Store size dict
        font_name = font_file[(font_file.rindex('/')+1):].split(".")[0]
        pickle_file = './data/{vs}_{fn}.pkl'.format(vs=version, fn=font_name)
        with open(pickle_file, 'wb') as out:
            pickle.dump(word_sizes, out)
        print("Word sizes saved to {p}".format(p=pickle_file))

    @classmethod
    def load_length_data(cls, font_name, versions):
        for version in versions:
            pickle_file = './data/{vs}_{fn}.pkl'.format(vs=version, fn=font_name)
            print("Loading version data for {v} version...".format(v=version))
            with open(pickle_file, 'rb') as pkf:
                BiblePassage.version_length_data[version] = pickle.load(pkf)

### TESTING ONLY ###
if __name__ == "__main__":
    pass
