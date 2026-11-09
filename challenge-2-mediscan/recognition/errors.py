class RecognitionError(Exception):
    def __init__(self, status: int, category: str, message: str):
        self.status = status
        self.category = category
        self.message = message
        super().__init__(message)
