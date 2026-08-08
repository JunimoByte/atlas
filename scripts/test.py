"""Print the browser names configured in configs/browsers.json."""

import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "browsers.json"


def main() -> None:
    """Print each configured browser in configuration order."""
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        browsers = json.load(config_file)

    for number, browser_name in enumerate(browsers, start=1):
        print("{}. {}".format(number, browser_name))


if __name__ == "__main__":
    main()