class Error(Exception):
    pass


class WrongCredsError(Error):
    pass


class NotRegisteredError(Error):
    pass


class MultiDevicesError(Error):
    pass


class NoClientPeopleError(Error):
    pass


class NoDataInTheFileError(Error):
    pass


class NotBelongsToClientError(Error):
    pass


class NoSiteError(Error):
    pass


class FileSizeMisMatchError(Error):
    pass


class TotalRecordsMisMatchError(Error):
    pass


class NoDbError(Error):
    pass


class RecordsAlreadyExist(Error):
    pass


class NoRecordsFound(Error):
    pass


class NotBelongsToTheClient(Error):
    pass