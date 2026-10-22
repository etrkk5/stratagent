"""Bounded CI test runner with diagnostic thread dumps, never a silent hang."""
import argparse
import faulthandler
import sys
import unittest


def run(suite, timeout):
    if type(timeout) is not int or not 5 <= timeout <= 1800:
        raise ValueError("Suite timeout must be 5–1800 seconds.")
    faulthandler.dump_traceback_later(timeout, file=sys.__stderr__, exit=True)
    try:
        return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
    finally:
        faulthandler.cancel_dump_traceback_later()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=600, help="Hard suite deadline with thread traceback and failure exit")
    arguments = parser.parse_args()
    if not 5 <= arguments.timeout <= 1800:
        parser.error("--timeout must be 5–1800 seconds")
    suite = unittest.defaultTestLoader.discover("tests")
    return 0 if run(suite, arguments.timeout) else 1


if __name__ == "__main__":
    raise SystemExit(main())
