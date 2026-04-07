"""Entry point for `python -m pensieve`.

Equivalent to running the `pensieve` CLI directly. Provided so the
package can be invoked without relying on the installed console script,
which is useful for tests, CI, and environments where the console
script may not be on PATH.
"""

import sys

from pensieve.cli import main

if __name__ == "__main__":
    sys.exit(main())
