# Changelog

## 1.3.1

- API key no longer exposed in exceptions
- `DesearchAPIError` now subclasses `aiohttp.ClientResponseError`, but its constructor signature differs (`status` is the first positional argument), so code constructing it directly must use the new signature.
