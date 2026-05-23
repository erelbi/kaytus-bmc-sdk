class KaytusError(Exception):
    pass


class KaytusAuthError(KaytusError):
    pass


class KaytusConnectionError(KaytusError):
    pass


class KaytusHTTPError(KaytusError):
    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class KaytusETagError(KaytusError):
    pass


class KaytusNotFoundError(KaytusHTTPError):
    pass
