from http import HTTPStatus


class BusinessException(Exception):
    def __init__(self, message: str, status_code: HTTPStatus = HTTPStatus.BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
