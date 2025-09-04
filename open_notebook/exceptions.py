class OpenNotebookError(Exception):
  """Base exception class for Open Notebook errors."""


class DatabaseOperationError(OpenNotebookError):
  """Raised when a database operation fails."""


class UnsupportedTypeException(OpenNotebookError):
  """Raised when an unsupported type is provided."""


class InvalidInputError(OpenNotebookError):
  """Raised when invalid input is provided."""


class NotFoundError(OpenNotebookError):
  """Raised when a requested resource is not found."""


class AuthenticationError(OpenNotebookError):
  """Raised when there's an authentication problem."""


class ConfigurationError(OpenNotebookError):
  """Raised when there's a configuration problem."""


class ExternalServiceError(OpenNotebookError):
  """Raised when an external service (e.g., AI model) fails."""


class RateLimitError(OpenNotebookError):
  """Raised when a rate limit is exceeded."""


class FileOperationError(OpenNotebookError):
  """Raised when a file operation fails."""


class NetworkError(OpenNotebookError):
  """Raised when a network operation fails."""


class NoTranscriptFound(OpenNotebookError):
  """Raised when no transcript is found for a video."""
