class EndpointRequestError(Exception):
    def __init__(self, msg):
        super().__init__()


class HTTPConnectionError(Exception):
    def __init__(self, msg):
        super().__init__()


class ResponseKeyError(KeyError):
    def __init__(self, message):
        super().__init__(message)


class UnexpectedStatusError(Exception):
    def __init__(self, msg):
        super().__init__()


class InvalidJSONError(Exception):
    def __init__(self, msg):
        super().__init__()
