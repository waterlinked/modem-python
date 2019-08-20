# Developemnt of Python library for Water Linked underwater modems

## About

This document contains notes on how to develop and maintain the repository.

## Development

When developing locally the easiest way to test multiple Python versions is to use `tox`.

Unit tests are automatically run on Python 2 and Python 3 using [Travis](https://travis-ci.org/waterlinked/modem-python) when code is pushed to the repository.
If unit-tests are succesful the code coverage is pushed to [Coveralls](https://coveralls.io/github/waterlinked/modem-python?branch=master)

## Releasing to PyPI

* Update the version number in `setup.py` as specified by [Semantic versioning](https://semver.org/)
* Add information on what is changed in [CHANGELOG.md](CHANGELOG.md)
* Push to `master`
* Verify that unit-tests builds successfully on Travis
* Add tag: `git tag -a v1.5.3 -m "Release the 1.5.3 release` (change 1.5.3 to the correct version number)
* Push tag to github: `git push origin --tags`
* Dring some coffe while Travis builds and pushes to PyPI
