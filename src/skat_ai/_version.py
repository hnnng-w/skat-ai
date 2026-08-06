from importlib import metadata


def _get_version() -> str:
    try:
        return metadata.version("skat-ai")
    except metadata.PackageNotFoundError:
        return "0+unknown"


__version__ = _get_version()
