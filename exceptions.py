from requests import RequestException, ConnectionError
from requests.exceptions import InvalidJSONError
# from telegram.error import TelegramError
#
#
# class TelegramDispatchError(TelegramError):
#     def __init__(self, message):
#         super().__init__(message)


class EndpointRequestError(RequestException):
    def __init__(self, message):
        super().__init__(message)


class HTTPConnectionError(ConnectionError):
    def __init__(self, message):
        super().__init__(message)


class ResponseKeyError(KeyError):
    def __init__(self, message):
        super().__init__(message)


class UnexpectedStatusError(KeyError):
    def __init__(self, message):
        super().__init__(message)


class JSONProcessingError(InvalidJSONError):
    def __init__(self, message):
        super().__init__(message)
