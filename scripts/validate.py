"""Validate the supported schema subset, source paths, and generated metadata."""
from sync import sync

if __name__ == "__main__":
    try:
        sync(check=True)
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error
    print("PASS: catalog, platforms, paths, skills, Claude hooks/Mods structure, generation consistency")
