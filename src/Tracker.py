# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Track usage of Songs for CCLI returns."""

import sqlite3
import datetime
import json

class Tracker():
    """Track usage of Songs for CCLI returns."""

    @classmethod
    def log(cls, song_id):
        """Record usage of a song, up to a maximum of once per day.

        Arguments:
        song_id -- the id of the Song to be logged.
        """
        # Only log each song once per day
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT id
            FROM tracking
            WHERE song_id = {id} AND tracked_date = \"{dt}\"
        '''.format(id=song_id, dt=str(datetime.date.today())))
        results = cursor.fetchall()
        if not results:
            # No tracking record for this song today, so add one
            cursor.execute('''
                INSERT INTO tracking(song_id, tracked_date)
                VALUES(?, ?)
            ''', (song_id, str(datetime.date.today())))
            song_db.commit()
        song_db.close()

    @classmethod
    def query_usage(cls, start_date, end_date):
        """Return a JSON list of all song usage in an inclusive date range.

        Arguments:
        start_date -- the start date in the range (formatted as YYYY-MM-DD).
        end_date -- the end date in the range (formatted as YYYY-MM-DD).
        """
        if end_date < start_date:
            s_date, e_date = end_date, start_date
        else:
            s_date, e_date = start_date, end_date
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            SELECT s.title, s.author, s.song_book_name, s.song_number, s.copyright, t.tracked_date
            FROM songs AS s INNER JOIN tracking AS t ON s.id = t.song_id
            WHERE t.tracked_date >= ? AND t.tracked_date <= ?
        ''', (s_date, e_date))
        results = cursor.fetchall()
        results_dict = [{
            "title": result[0],
            "author": result[1],
            "song-book": result[2],
            "song-number": result[3],
            "copyright": result[4],
            "used-on": result[5]
        } for result in results]
        song_db.close()
        return json.dumps(results_dict, indent=2)

    @classmethod
    def clear_usage(cls, start_date, end_date):
        """Remove all usage data in an inclusive date range from the songs database.

        Arguments:
        start_date -- the start date in the range (formatted as YYYY-MM-DD).
        end_date -- the end date in the range (formatted as YYYY-MM-DD).
        """
        if end_date < start_date:
            s_date, e_date = end_date, start_date
        else:
            s_date, e_date = start_date, end_date
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            DELETE
            FROM tracking
            WHERE tracked_date >= ? AND tracked_date <= ?
        ''', (s_date, e_date))
        song_db.commit()
        song_db.close()

    @classmethod
    def clear_all_usage(cls):
        """Remove all usage data from songs database."""
        song_db = sqlite3.connect('./data/songs.sqlite')
        cursor = song_db.cursor()
        cursor.execute('''
            DELETE FROM tracking
        ''')
        song_db.commit()
        song_db.close()

# TESTING ONLY
if __name__ == "__main__":
    pass
