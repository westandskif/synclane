PROJECT := synclane

build:
	find dist -delete || true
	hatch build

bash-py%:
	docker run --rm -it -v $$PWD:/mnt/$PROJECT -w /mnt/$PROJECT python:$* bash

lock-py%:
	docker run --rm -it \
		-v $$PWD:/mnt/$PROJECT \
		-w /mnt/$PROJECT/ci-requirements \
		python:$* bash -c \
		"rm -f requirements$*.out && pip install -r requirements$*.in && pip freeze > requirements$*.out"

test-py%:
	docker build --build-arg="PY_VERSION=$*" -t $PROJECT_$*:latest ci-requirements
	docker run --rm -it -v $$PWD:/mnt/$PROJECT $PROJECT_$*:latest bash -c \
		"pip install -e . && pytest"

test: test-py3.6 test-py3.7 test-py3.8 test-py3.9 test-py3.10 test-py3.11 test-py3.12
