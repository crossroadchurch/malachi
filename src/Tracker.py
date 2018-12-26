import sqlite3, datetime, json

class Tracker():

    def __init__(self):
        pass

    def log(self, song_id):
        # Only log each song once per day
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            SELECT id
            FROM tracking
            WHERE song_id = {id} AND tracked_date = \"{dt}\"
        '''.format(id=song_id, dt=str(datetime.date.today())))
        results = cursor.fetchall()
        if len(results) == 0:
            # No tracking record for this song today, so add one
            cursor.execute('''
                INSERT INTO tracking(song_id, tracked_date)
                VALUES(?, ?)
            ''', (song_id, str(datetime.date.today())))
            db.commit()
        db.close()

    def query_usage(self, start_date, end_date):
        if end_date < start_date:
            s_date, e_date = end_date, start_date
        else:
            s_date, e_date = start_date, end_date
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
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
        db.close()
        return json.dumps(results_dict, indent=2)

    def clear_usage(self, start_date, end_date):
        if end_date < start_date:
            s_date, e_date = end_date, start_date
        else:
            s_date, e_date = start_date, end_date
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            DELETE
            FROM tracking
            WHERE tracked_date >= ? AND tracked_date <= ?
        ''', (s_date, e_date))
        db.commit()
        db.close()

    def clear_all_usage(self):
        db = sqlite3.connect('./data/songs.sqlite')
        cursor = db.cursor()
        cursor.execute('''
            DELETE FROM tracking
        ''')
        db.commit()
        db.close()

# TESTING ONLY
if __name__ == "__main__":
    pass