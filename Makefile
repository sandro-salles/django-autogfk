# Makefile — requires GNU Make

.PHONY: help clean verify build check tag testpypi pypi release

# helper: require VERSION on targets that need it
req_version = $(if $(strip $(VERSION)),,$(error VERSION is required, e.g., make $@ VERSION=0.2.0))

help:
	@echo "Targets:"
	@echo "  tag VERSION=X.Y.Z    - commit (if needed), create and push git tag vX.Y.Z"
	@echo "  build                - build sdist+wheel into dist/"
	@echo "  check                - twine check dist/*"
	@echo "  testpypi             - upload to TestPyPI (uses ~/.pypirc)"
	@echo "  pypi                 - upload to PyPI (uses ~/.pypirc)"
	@echo "  release VERSION=X.Y.Z- tag + build + check + upload to PyPI"

clean:
	rm -rf dist build *.egg-info

# verify the version in your files matches VERSION (pyproject is required; __init__ optional)
verify:
	$(call req_version)
	@grep -q 'version = "$(VERSION)"' pyproject.toml || \
	  (echo "pyproject.toml version mismatch (expected $(VERSION))"; exit 1)
	@([ ! -f src/autogfk/__init__.py ] || \
	  grep -q '__version__ = "$(VERSION)"' src/autogfk/__init__.py) || \
	  (echo "src/autogfk/__init__.py __version__ mismatch (expected $(VERSION))"; exit 1)
	@echo "✓ version verified: $(VERSION)"

build: clean
	python -m pip install -U build twine
	python -m build

check:
	python -m twine check dist/*

tag:
	$(call req_version)
	git add pyproject.toml src/autogfk/__init__.py 2>/dev/null || true
	git commit -m "chore(release): bump to $(VERSION)" || true
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin --tags

# Uses ~/.pypirc entries: [testpypi] and [pypi]
testpypi:
	python -m twine upload --repository testpypi dist/*

pypi:
	python -m twine upload dist/*

# full release to PyPI (fails early if version mismatch)
release: verify tag build check pypi
