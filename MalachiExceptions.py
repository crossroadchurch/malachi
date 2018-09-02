# Presentations
class InvalidPresentationUrlError(Exception):
    def __init__(self, url):
        self.msg = "Could not find a presentation at the url {url}".format(url=url)
        super(InvalidPresentationUrlError, self).__init__(self.msg)

# Bible
class InvalidVersionError(Exception):
    def __init__(self, version):
        self.msg = "%s is not a recognised Bible version" % version
        super(InvalidVersionError, self).__init__(self.msg)

class InvalidVerseIdError(Exception):
    def __init__(self, id, version):
        self.msg = "Could not find a verse with id {id} in the {vs} version of the Bible".format(id=id, vs=version)
        super(InvalidVerseIdError, self).__init__(self.msg)

class MalformedReferenceError(Exception):
    def __init__(self, ref):
        self.msg = "%s is not a valid form for a Bible reference" % ref
        super(MalformedReferenceError, self).__init__(self.msg)

# Service
class InvalidServiceUrlError(Exception):
    def __init__(self, url):
        self.msg = "Could not find a service file at the url {url}".format(url=url)
        super(InvalidServiceUrlError, self).__init__(self.msg)

class MalformedServiceFileError(Exception):
    def __init__(self, url, details):
        self.msg = "The service file {url} is not correctly formatted: {details}".format(url=url,details=details)
        super(MalformedServiceFileError, self).__init__(self.msg)

# Song
class InvalidSongIdError(Exception):
    def __init__(self, id):
        self.msg = "Could not find a song that has id {id}".format(id=id)
        super(InvalidSongIdError, self).__init__(self.msg)

# Service
class UnspecifiedServiceUrl(Exception):
    def __init__(self):
        self.msg = "No file location was specified for saving the Service."
        super(UnspecifiedServiceUrl, self).__init__(self.msg)