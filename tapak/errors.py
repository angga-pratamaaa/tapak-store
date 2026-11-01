class ApiError(Exception):
    """Galat yang dikirim ke klien sebagai JSON {error: pesan} dengan status HTTP tertentu."""

    def __init__(self, status, msg):
        super().__init__(msg)
        self.status, self.msg = status, msg
