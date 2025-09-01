# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""
Provide custom Exception classes for Malachi.
"""

# Bible
class InvalidVersionError(Exception):
    """Indicate that a specified version of the Bible is not supported in Malachi"""
    def __init__(self, version):
        self.msg = "An unrecognised Bible version was used: %s" % version
        super(InvalidVersionError, self).__init__(self.msg)

class InvalidVerseIdError(Exception):
    """Indicate that a specified verse id does not exist in a version of the Bible"""
    def __init__(self, verse_id, version):
        self.msg = "Could not find a verse with this id in this version: {id}, {vs}"\
            .format(id=verse_id, vs=version)
        super(InvalidVerseIdError, self).__init__(self.msg)

class MatchingVerseIdError(Exception):
    """Indicate that a verse in one version of the Bible could not be found in another version."""
    def __init__(self, verse_id, old_version, new_version):
        self.msg = "Could not find a matching verse when changing version: {id}, {ov}, {nv}"\
            .format(id=verse_id, ov=old_version, nv=new_version)
        super(MatchingVerseIdError, self).__init__(self.msg)

class MalformedReferenceError(Exception):
    """Indicate that a Bible reference does not have the correct syntax"""
    def __init__(self, ref):
        self.msg = "An invalid format for a Bible reference was used: %s" % ref
        super(MalformedReferenceError, self).__init__(self.msg)

class UnknownReferenceError(Exception):
    """Indicate that a Bible reference does not exist in the current version of the Bible."""
    def __init__(self, verse_ref):
        self.msg = "An unknown reference for this version of the Bible was used: {ref}"\
            .format(ref=verse_ref)
        super(UnknownReferenceError, self).__init__(self.msg)

# Service
class InvalidServiceUrlError(Exception):
    """Indicate that a specified Service URL does not exist"""
    def __init__(self, url):
        self.msg = "Could not find a service file at the url {url}".format(url=url)
        super(InvalidServiceUrlError, self).__init__(self.msg)

class MalformedServiceFileError(Exception):
    """Indicate that a Service JSON file does not have the correct syntax"""
    def __init__(self, service_url, details):
        self.msg = "The service file {url} is not correctly formatted: {details}".\
            format(url=service_url, details=details)
        super(MalformedServiceFileError, self).__init__(self.msg)

class UnspecifiedServiceUrl(Exception):
    """Indicate that no save location has been specified when trying to save a Service"""
    def __init__(self):
        self.msg = "No file location was specified for saving the Service."
        super(UnspecifiedServiceUrl, self).__init__(self.msg)

# Song
class InvalidSongIdError(Exception):
    """Indicate that a specified song id does not exist in the songs database"""
    def __init__(self, song_id):
        self.msg = "Could not find a song that has id {id}".format(id=song_id)
        super(InvalidSongIdError, self).__init__(self.msg)

class InvalidSongFieldError(Exception):
    """Indicate that invalid data has been provided when editing a field of a Song"""
    def __init__(self, data):
        self.msg = "Invalid field data provided: {data}".format(data=data)
        super(InvalidSongFieldError, self).__init__(self.msg)

# Styles
class MissingStyleParameterError(Exception):
    """Indicate that a required style parameter is missing from the current style"""
    def __init__(self, data):
        self.msg = "The current style is missing a parameter: {data}".format(data=data)
        super(MissingStyleParameterError, self).__init__(self.msg)

# Videos
class InvalidVideoUrlError(Exception):
    """Indicate that a specified Video URL does not exist"""
    def __init__(self, url):
        self.msg = "Could not find a video at the url {url}".format(url=url)
        super(InvalidVideoUrlError, self).__init__(self.msg)

class InvalidVideoError(Exception):
    """Indicate that a specified URL does not contain a valid video file"""
    def __init__(self, url):
        self.msg = "The file at the url {url} is not a valid video".format(url=url)
        super(InvalidVideoError, self).__init__(self.msg)

# Backgrounds
class InvalidBackgroundUrlError(Exception):
    """Indicate that a specified Background URL does not exist"""
    def __init__(self, url):
        self.msg = "Could not find a background at the url {url}".format(url=url)
        super(InvalidBackgroundUrlError, self).__init__(self.msg)

# Presentations
class InvalidPresentationUrlError(Exception):
    """Indicate that a specified Presentation URL does not exist"""
    def __init__(self, url):
        self.msg = "Could not find a presentation at the url {url}".format(url=url)
        super(InvalidPresentationUrlError, self).__init__(self.msg)

# Malachi
class MissingDataFilesError(Exception):
    """Indicate that a specified data file(s) does not exist"""
    def __init__(self, files):
        self.msg = "The following essential data files were not found: {files}".format(files=files)
        super(MissingDataFilesError, self).__init__(self.msg)

class InkscapeVersionError(Exception):
    """Indicate that the wrong version of Inkscape is installed"""
    def __init__(self, version):
        self.msg = "The wrong version of Inkscape is installed ({version}), must be 1.0+".format(version=version)
        super(InkscapeVersionError, self).__init__(self.msg)
