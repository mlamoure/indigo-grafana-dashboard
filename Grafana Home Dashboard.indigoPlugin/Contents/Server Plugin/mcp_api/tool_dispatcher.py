"""
Dispatcher for the `mcp_tool_invoke` hidden action.

The MCP Advanced Tools plugin calls
executeAction("mcp_tool_invoke", props={"tool": <name>, "arguments": <JSON string>})
and receives a JSON string back. Arguments cross the boundary as a JSON
string because indigo.Dict cannot carry None values or $-prefixed keys.

Reply envelope (always a JSON string, never an exception):
  {"status": "ok", "result": <any JSON>}
  {"status": "error", "error": {"type": "validation|not_found|conflict|internal",
								"message": str, "details": <optional JSON>}}
"""

import inspect
import json
import logging

from config_store import ConfigError

from .errors import ToolError

logger = logging.getLogger("Plugin")


class AsyncResult:
	"""Returned by a tool whose work needs the network; the plugin runs work()
	on a worker thread and hands the envelope back through Indigo's callback
	completion handler."""

	def __init__(self, work):
		self.work = work


class ToolDispatcher:
	def __init__(self, service):
		self._service = service
		self._tools = {name: getattr(service, name) for name in service.TOOLS}

	def tool_names(self):
		return sorted(self._tools)

	def dispatch(self, tool_name, arguments_json):
		try:
			handler = self._tools.get(tool_name)
			if handler is None:
				return self._error(
					"not_found",
					f"Unknown tool {tool_name!r}; available: {', '.join(self.tool_names())}",
				)

			try:
				arguments = json.loads(arguments_json or "{}")
			except (TypeError, ValueError) as e:
				return self._error("validation", f"arguments is not valid JSON: {e}")
			if not isinstance(arguments, dict):
				return self._error("validation", "arguments must be a JSON object")

			try:
				inspect.signature(handler).bind(**arguments)
			except TypeError as e:
				return self._error("validation", f"bad arguments for {tool_name}: {e}")

			logger.debug(f"MCP tool invoked: {tool_name}")
			return self.envelope(handler(**arguments))
		except Exception as e:
			return self.failure(tool_name, e)

	@staticmethod
	def envelope(result):
		if isinstance(result, AsyncResult):
			return result  # finished on a worker thread: see complete()
		return json.dumps({"status": "ok", "result": result}, default=str)

	def complete(self, tool_name, pending):
		"""Run an AsyncResult's work and return the envelope (on a worker thread)."""
		try:
			return json.dumps({"status": "ok", "result": pending.work()}, default=str)
		except Exception as e:
			return self.failure(tool_name, e)

	def failure(self, tool_name, error):
		if isinstance(error, ToolError):
			return self._error(error.error_type, error.message, error.details)
		if isinstance(error, ConfigError):
			details = error.details if error.details is not None else ({"errors": error.errors} if error.errors else None)
			return self._error(error.kind, error.message, details)
		logger.exception(f"MCP tool {tool_name!r} failed")
		return self._error("internal", f"{type(error).__name__}: {error}")

	@staticmethod
	def _error(error_type, message, details=None):
		error = {"type": error_type, "message": message}
		if details is not None:
			error["details"] = details
		logger.debug(f"MCP tool error ({error_type}): {message}")
		return json.dumps({"status": "error", "error": error}, default=str)
