import sqlite3, json
import xml.etree.ElementTree as ET

# Pre-condition: songs.sqlite is an OpenLP songs database used in Paul
db = sqlite3.connect('./data/songs.sqlite')
cursor = db.cursor()

# REMOVE TOPICS
print("Removing topics...")
cursor.execute('''DROP TABLE songs_topics''')
cursor.execute('''DROP INDEX ix_topics_name''')
cursor.execute('''DROP TABLE topics''')
db.commit()
print("...done")


# REMOVE METADATA AND MEDIA_FILES
print("Removing metadata and media files...")
cursor.execute('''DROP TABLE metadata''')
cursor.execute('''DROP TABLE media_files''')
db.commit()
print("...done")


# REMOVE SONG_BOOKS AFTER INCLUDING DATA INTO SONGS TABLE
print("Incorporating song books into songs table...")
cursor.execute('''
    SELECT b.id, b.name
    FROM song_books AS b
    ''')
song_books = cursor.fetchall()
book_dict = dict(song_books)  # i.e. book_dict[id] = name
cursor.execute('''
    ALTER TABLE songs
    ADD COLUMN song_book_name VARCHAR(128)
    ''')
cursor.execute('''
    SELECT s.id, s.song_book_id
    FROM songs AS s
    WHERE s.song_book_id IS NOT NULL
    ''')
songs = cursor.fetchall()
for song in songs:
    cursor.execute('''
        UPDATE songs
        SET song_book_name = \"{bn}\"
        WHERE id = {id}
        '''.format(bn=book_dict[song[1]], id=song[0]))
cursor.execute('''DROP TABLE song_books''')
db.commit()
print("...done")

# REMOVE AUTHORS AFTER INCLUDING DATA IN SONGS TABLE
print("Incorporating authors into songs table...")
cursor.execute('''
    ALTER TABLE songs
    ADD COLUMN author VARCHAR(255)
    ''')
cursor.execute('''SELECT s.id FROM songs AS s''')
songs = cursor.fetchall()
for song in songs:
    cursor.execute('''
        SELECT a.display_name
        FROM authors AS a INNER JOIN authors_songs AS a_s ON a_s.author_id = a.id
        WHERE a_s.song_id = {id}
        '''.format(id=song[0]))
    authors = cursor.fetchall()
    authors_str = ', '.join([x[0] for x in authors])
    cursor.execute('''
        UPDATE songs
        SET author = \"{a_str}\"
        WHERE id = {id}
    '''.format(a_str=authors_str, id=song[0]))
cursor.execute('''DROP INDEX ix_authors_display_name''')
cursor.execute('''DROP TABLE authors_songs''')
cursor.execute('''DROP TABLE authors''')
db.commit()
print("...done")

# Merge alternate_title with title
print("Merging title and alternate title...")
cursor.execute('''
    SELECT s.id, s.title, s.alternate_title
    FROM songs AS s
    WHERE s.alternate_title IS NOT NULL AND s.alternate_title <> ""
''')
songs = cursor.fetchall()
for song in songs:
    title_str = song[1] + " (" + song[2] + ")"
    cursor.execute('''
        UPDATE songs
        SET title = \"{t_s}\"
        WHERE id = {id}
    '''.format(t_s=title_str, id=song[0]))
db.commit()
print("...done")

# Create lyrics_chords - for now just copy chords if it exists, else use lyrics
# Then convert to JSON formatting
print("Creating lyrics_chords...")
cursor.execute('''
    ALTER TABLE songs
    ADD COLUMN lyrics_chords
''')
cursor.execute('''
    SELECT s.id, s.chords, s.lyrics
    FROM songs AS s
''')
songs = cursor.fetchall()
for song in songs:
    if song[1] == None:
        l_c_str = song[2]
    else:
        l_c_str = song[1]

    root = ET.fromstring(l_c_str)
    l_c_data = []

    for child in root[0]:
        if child.tag == "verse":
            part = child.attrib["type"] + child.attrib["label"]
            data = child.text
            data = data.replace("<chord name = \"", "[")
            data = data.replace("\" />", "]")
            l_c_data.append({"part": part, "data": data})

    cursor.execute('''
        UPDATE songs
        SET lyrics_chords = ?
        WHERE id = ?
    ''',(json.dumps(l_c_data), song[0]))
db.commit()
print("...done")

# Remove unnecessary columns from songs table
print("Removing unused columns from songs table...")

cursor.execute('''
    ALTER TABLE songs
    RENAME TO temp_songs
''')
cursor.execute('''
    CREATE TABLE songs (
        id INTEGER NOT NULL, 
        song_book_name VARCHAR(128), 
        title VARCHAR(255) NOT NULL, 
        author VARCHAR(255),
        song_key VARCHAR(3), 
        transpose_by INTEGER, 
        lyrics_chords TEXT, 
        verse_order VARCHAR(128), 
        copyright VARCHAR(255), 
        song_number VARCHAR(64), 
        search_title VARCHAR(255) NOT NULL, 
        search_lyrics TEXT NOT NULL, 
        PRIMARY KEY (id) 
    )
''')
cursor.execute('''
    INSERT INTO songs(song_book_name, title, author, song_key, transpose_by, lyrics_chords, verse_order, copyright, song_number, search_title, search_lyrics)
        SELECT song_book_name, title, author, song_key, transpose_by, lyrics_chords, verse_order, copyright, song_number, search_title, search_lyrics
        FROM temp_songs
''')
cursor.execute('''DROP TABLE temp_songs''')
db.commit()
print("...done")

# Create tracking table for song usage
print("Creating tracking table for song usage...")
cursor.execute('''
    CREATE TABLE tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        song_id INTEGER,
        tracked_date` TEXT
    )
''')
db.commit()
print("...done")

db.execute("VACUUM")
db.close()
print("Migration complete!")