"""In-band tool failure, mapped to the provider reply envelope."""


class ToolError(Exception):
	"""error_type is one of validation | not_found | conflict | internal."""

	def __init__(self, error_type, message, details=None):
		super().__init__(message)
		self.error_type = error_type
		self.message = message
		self.details = details
