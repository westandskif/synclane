.PHONY: docs

PROJECT := synclane

build:
	find dist -delete || true
	hatch build

upload:
	hatch publish

bash-py%:
	docker run --rm -it -v $$PWD:/mnt/${PROJECT} -w /mnt/${PROJECT} python:$* bash

lock-py%:
	docker run --rm -it \
		-v $$PWD:/mnt/${PROJECT} \
		-w /mnt/${PROJECT}/ci-requirements \
		python:$* bash -c \
		"rm -f requirements$*.out && pip install -r requirements$*.in && pip freeze > requirements$*.out"

test-py%:
	docker build --build-arg="PY_VERSION=$*" -t ${PROJECT}_$*:latest ci-requirements
	docker run --rm -it -v $$PWD:/mnt/${PROJECT} ${PROJECT}_$*:latest bash -c \
		"source ~/.bashrc && pip install -e . && pytest"

test: test-py3.7 test-py3.8 test-py3.9 test-py3.10 test-py3.11 test-py3.12


lock-int-tst-py%:
	docker run --rm -it \
		-v $$PWD:/mnt/${PROJECT} \
		-w /mnt/${PROJECT}/tests/int_tst \
		python:$* bash -c \
		"rm -f requirements$*.out && pip install -r requirements$*.in && pip freeze > requirements$*.out"

test/int-tst:
	cd tests/int_tst \
		&& docker compose stop \
		&& docker compose build \
		&& docker compose up frontend \
		&& docker compose stop

checks:
	isort src tests
	black src tests
	ruff check
	mypy --check-untyped-defs src
	pylint src


docs:
	mkdocs serve
