# Four Irish Typefaces: build, check and package.  `make help` lists the targets.
PY      ?= .venv/bin/python
FACES   ?= kilfane tuam carrick ceili

.PHONY: help setup fonts release test validate specimen audit package site showcase serve trace clean

help:
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/'

setup:  ## a Python 3.13 venv with the pinned tools
	python3.13 -m venv .venv && $(PY) -m pip install -q -r requirements.txt

fonts:  ## build every style of every face into build/fonts
	$(PY) scripts/build2.py $(FACES)

release: fonts  ## copy the built fonts into fonts/, regenerate css/ and index.html
	$(PY) scripts/release.py

test:  ## the release checks (on fonts/; FONTDIR=build/fonts to check a fresh build)
	$(PY) -m pytest -q tests

validate:  ## OTS, Font Bakery per family and the flyer audit, into docs/validation
	$(PY) scripts/validate.py

specimen:  ## the PDF and PNG specimen, into docs/specimen
	SPECIMEN=docs/specimen OUT=$(CURDIR)/build/fonts $(PY) scripts/specimen2.py

package:  ## the release ZIPs, into build/dist
	$(PY) scripts/package.py

site: package  ## the test page app, into build/app
	$(PY) scripts/site.py build/app build/fonts

showcase:  ## the showcase website, into build/showcase (and build/showcase-artifact)
	$(PY) scripts/showcase.py --artifact

serve: showcase  ## build the showcase and serve it at http://localhost:8377
	cd build/showcase && python3 -m http.server 8377

trace:  ## re-trace sources/traced/*.json from the scan (slow; only for a new scan)
	$(PY) scripts/trace3.py $(FACES)

clean:
	rm -rf build
