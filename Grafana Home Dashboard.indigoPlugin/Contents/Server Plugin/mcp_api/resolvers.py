"""Turn the device references a tool receives (an integer id or an exact name)
into Indigo devices, with close-match suggestions for unknown names."""

import difflib

import indigo

from .errors import ToolError


def device_name(dev_id):
	try:
		return indigo.devices[int(dev_id)].name
	except (KeyError, TypeError, ValueError):
		return None


def suggestions(text, candidates, limit=5):
	text = str(text)
	lowered = {candidate.lower(): candidate for candidate in candidates}
	matches = difflib.get_close_matches(text.lower(), list(lowered), n=limit, cutoff=0.5)
	if len(matches) < limit:
		contains = [key for key in lowered if text.lower() in key and key not in matches]
		matches += sorted(contains)[:limit - len(matches)]
	return [lowered[m] for m in matches]


def resolve_device(ref, path="device"):
	"""An Indigo device from an id (int or numeric string) or an exact name."""
	if isinstance(ref, bool) or ref is None or (isinstance(ref, str) and not ref.strip()):
		raise ToolError("validation", f"{path}: give a device id or exact device name")

	if isinstance(ref, int) or (isinstance(ref, str) and ref.strip().isdigit()):
		dev_id = int(ref)
		if dev_id in indigo.devices:
			return indigo.devices[dev_id]
		raise ToolError("not_found", f"{path}: no device with id {dev_id}")

	name = str(ref).strip()
	for dev in indigo.devices:
		if dev.name == name:
			return dev
	close = suggestions(name, [dev.name for dev in indigo.devices])
	raise ToolError("not_found", f"{path}: no device named {name!r}",
					{"errors": [{"path": path, "message": f"unknown device {name!r}"}], "did_you_mean": close})


def resolve_devices(refs, path="devices", limit=None):
	if not isinstance(refs, list) or not refs:
		raise ToolError("validation", f"{path}: give a non-empty list of device ids or names")
	if limit is not None and len(refs) > limit:
		raise ToolError("validation", f"{path}: at most {limit} devices per call (got {len(refs)})")

	devices, errors, did_you_mean = [], [], {}
	for index, ref in enumerate(refs):
		try:
			dev = resolve_device(ref, f"{path}[{index}]")
		except ToolError as e:
			errors.append({"path": f"{path}[{index}]", "message": e.message})
			if e.details and e.details.get("did_you_mean"):
				did_you_mean[str(ref)] = e.details["did_you_mean"]
			continue
		if dev.id not in [d.id for d in devices]:
			devices.append(dev)
	if errors:
		details = {"errors": errors}
		if did_you_mean:
			details["did_you_mean"] = did_you_mean
		raise ToolError("validation", f"{len(errors)} of the devices could not be found", details)
	return devices


def device_ref(dev_id):
	"""{id, name} for output - the name next to every id."""
	return {"id": int(dev_id), "name": device_name(dev_id)}
