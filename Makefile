CXX ?= c++
PYTHON ?= .venv/bin/python
CXXFLAGS := -std=c++11 -O2 -Wall -Wextra -Werror -pedantic -fsanitize=undefined
.PHONY: check build preview
check: build/core-test
	$(PYTHON) tools/protocol_fixture.py
	./build/core-test
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
	node --check preview/app.js
	node --check extension/content.js
	node --check extension/popup.js
	node tests/extension_test.cjs
build/core-test: tests/core_test.cpp firmware/DigitalVinyl/Record.h firmware/DigitalVinyl/Protocol.h
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@
build:
	python3 tools/project.py build
preview:
	$(PYTHON) bridge/server.py
