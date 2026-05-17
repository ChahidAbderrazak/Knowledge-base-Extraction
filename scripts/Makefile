# load .env variables from list of ENVFILES separated by space
ENVFILES := $(foreach f,.env .env-ip-mlops .env-mlops,$(firstword $(wildcard $(f) ../$(f))))

# Load all env files
define LOAD_ENV
include $(1)
export $(shell sed '/^\#/d; s/=.*//' $(1))
endef
$(foreach envfile,$(ENVFILES),$(eval $(call LOAD_ENV,$(envfile))))

# default project variables
PROJECT_NAME ?= ml-project
export PROJECT_NAME

VERSION ?= dev
export VERSION

HARD_DRIVE2_PATH ?= .
export HARD_DRIVE2_PATH

PROJECT_LOCAL_DIR = ${HARD_DRIVE2_PATH}/${PROJECT_NAME}
export PROJECT_LOCAL_DIR

ZENML_CNTNR_NAME ?= zenml
export ZENML_CNTNR_NAME

# mlops artifacts variables
ZENML_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/zenml
export ZENML_LOCAL_DIR

POSTGRES_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/postgres
export POSTGRES_LOCAL_DIR

MySQL_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/mysql
export MySQL_LOCAL_DIR

S3_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/S3_database
export S3_LOCAL_DIR

Jenkins_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/jenkins
export Jenkins_LOCAL_DIR

REDIS_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/redis
export REDIS_LOCAL_DIR

SQLITE_LOCAL_DIR ?= ${HARD_DRIVE2_PATH}/sqlite
export SQLITE_LOCAL_DIR

# default target
default: dev

# help
help: #----------------------- Showing the help -----------------------
	@NO_AT_BRIDGE=1 clear
	@echo "\033[0;31mDev Makefile:\033[0m for ${PROJECT_NAME} project"
	@echo ""
	@echo "Usage:"
	@echo "  make dev              Run the app container for development mode"
	@echo "  make container        Access the running dev container"
	@echo ""
	@echo "development mode:"
	@echo "\033[0;31mNote:\033[0m The folowing commands are used only for development container mode"
	@echo "  make setup            setting up the virtual env using poetry"
	@echo "  make jupyter          Run jupyter lab for development mode"
	@echo "  make install          Install/initialize the needed dev packages"
	@echo "  make test             Run unit test and code test coverage"
	@echo "  make clean            Clean the project build files"
	@echo "  make zenml-dev        Show how to run the ZenML development framework inside the app container"
	@echo ""
	@echo "  make help             Display this help message"
	@echo ""

variables:
	@echo "\nBuilding the Python project using the following environment variables: "
	@echo "PROJECT_NAME=${PROJECT_NAME}"
	@echo "VERSION=${VERSION}"
	@echo "HARD_DRIVE2_PATH=${HARD_DRIVE2_PATH}"
	@echo "ZENML_IMG_NAME=${ZENML_IMG_NAME}"
	@echo "ZENML_LOCAL_DIR=${ZENML_LOCAL_DIR}"
	@echo "POSTGRES_LOCAL_DIR=${POSTGRES_LOCAL_DIR}"
	@echo "MySQL_LOCAL_DIR=${MySQL_LOCAL_DIR}"
	@echo "S3_LOCAL_DIR=${S3_LOCAL_DIR}"
	@echo "Jenkins_LOCAL_DIR=${Jenkins_LOCAL_DIR}"
	@echo "REDIS_LOCAL_DIR=${REDIS_LOCAL_DIR}"


setup:
	@echo ">>> Full project using poetry (.venv) ...."
	@poetry config virtualenvs.in-project true --local

	@echo "- Convert ../requirements.txt to pyproject.toml (if file exists)"
	@if [ -f ./requirements.txt ]; then \
	    echo "- Converting requirements.txt → pyproject.toml dependencies..."; \
	    poetry config virtualenvs.create false; \
	    grep -vE '^\s*#|^\s*$$' ./requirements.txt | xargs poetry add --lock; \
	    poetry config virtualenvs.create true; \
	else \
	    echo "No ./requirements.txt found (skipping conversion)."; \
	fi

	@echo "Installing project dependencies with Poetry"
	@poetry install

	@echo ">>> Setup complete!"
	@echo ">>> Activate the environment with: poetry shell"



install: pre-commit convert-packages

pre-commit:
	# install pre-commit
	pip install pre-commit
	pre-commit install

convert-packages:
	# Convert your requirements.txt to pyproject.toml dependencies once locally:
	@NO_AT_BRIDGE=1 poetry config virtualenvs.create false
	grep -vE '^\s*#|^\s*$$' requirements.txt | xargs poetry add --lock

lint:  #----------------------- Lint and format the code -----------------------
	clear
	@echo  " #################################################"
	@echo " ##     [${PROJECT_NAME}]  Linting and formatting           "
	@echo " #################################################"

	# flake8 linting
	@NO_AT_BRIDGE=1 python -m flake8 . --count --select=E9,F63,F7,F82 --ignore=F541,W503 --show-source --statistics
	@NO_AT_BRIDGE=1 python -m flake8 .  --count --ignore=F541,W503 --max-complexity=10 --max-line-length=127 --statistics

	# format the code using Black
	@NO_AT_BRIDGE=1 python -m black .  #--check --diff

test:  #----------------------- Test the code -----------------------
	# @NO_AT_BRIDGE=1 $(MAKE) --no-print-directory lint

	@NO_AT_BRIDGE=1 clear
	@echo && echo " measure  tests coverage report"
	@NO_AT_BRIDGE=1 pytest --cov=src/ tests/ --verbose --durations=5 -vv --cov-report term-missing --cov-fail-under 60 || true

	# # run code coverage
	# @NO_AT_BRIDGE=1 $(MAKE) --no-print-directory coverage

coverage:#----------------------- Run code coverage tests -----------------------
	@echo  " #################################################"
	@echo " ##         [${PROJECT_NAME}]            "
	@echo " ## Evaluate the code testing coverage "
	@echo " #################################################"

	@NO_AT_BRIDGE=1 # save the report table as html
	@NO_AT_BRIDGE=1 mkdir -p artifacts
	@NO_AT_BRIDGE=1 rm -rf artifacts/htmlcov | python -m coverage html &&  mv  htmlcov artifacts/

	@echo  "\n\n-> The coverage report table : "
	@NO_AT_BRIDGE=1 python -m coverage report
	@NO_AT_BRIDGE=1 xdg-open ./artifacts/htmlcov/index.html 2>/dev/null
	@echo "\n\n ==> The report (saved in : ./artifacts/htmlcov/index.html) has been opened in your browser!\n"

dev:   #----------------------- Run the development container -----------------------
	@NO_AT_BRIDGE=1 docker system prune -f || docker volume prune -f

	# shw the env variables
	printenv

	# run the development container
	docker run -it -u root --rm \
				--network host \
				--env-file ../.env \
				--env-file ../.env-llm \
				--env-file ../.env-mlops \
				-p "${APP_HOST_PORT}:${APP_SERVER_PORT}" \
				-v $(realpath ../):/app/ \
				-v $(realpath ../)/data:/app/data \
				--name  "${PROJECT_NAME}-dev" \
				-w /app/ \
				"${PROJECT_NAME}:${VERSION}" \
				bash -c "echo \"alias makee='make -f scripts/Makefile'\" >> ~/.bashrc && exec bash"|| true


	@NO_AT_BRIDGE=1 docker system prune -f || docker volume prune -f

container:
	docker exec -it "${PROJECT_NAME}-dev" bash

jupyter: #----------------------- Open the Jupyter-lab  server -----------------------
	# run the jupyter notebooks to test queries
	# jupyter lab --allow-root
	jupyter lab --allow-root --ip=0.0.0.0 --port=8888 --no-browser --NotebookApp.token='' --NotebookApp.password=''

	# # execute a specific notebook
	# jupyter nbconvert --execute <notebook>



zenml-dev:  #----------------------- Run the Zenml based development -----------------------
	# @NO_AT_BRIDGE=1 clear
	# @echo && echo " -> Get the IP addresses of the running MLOPS containers"
	# @NO_AT_BRIDGE=1 $(MAKE) --no-print-directory ip

	@NO_AT_BRIDGE=1 clear
	# Explore the Zenml development framework
	@echo && echo "-> You can run the project inside the zenml folder."
	cd zenml && $(MAKE) help
	@NO_AT_BRIDGE=1 clear
	@echo && echo " #################################################"
	@echo " ##         ${PROJECT_NAME} PROJECT           "
	@echo " ##    Clean the build python files "
	@echo " #################################################" && echo

	@NO_AT_BRIDGE=1 #--------------------------------------------------------
	@echo && echo " -> Clean the __pycache__ folders "
	@NO_AT_BRIDGE=1 rm -rfv `find -type d -name *__pycache__*`

	@echo && echo " -> Clean the .pyc files "
	@NO_AT_BRIDGE=1 rm -fv `find -type f -name *.pyc`

	@echo && echo " -> Clean the checkpoint folders "
	@NO_AT_BRIDGE=1 rm -rfv `find -type d -name *checkpoint*`

	@echo && echo " -> Clean the pytest_cache folders "
	@NO_AT_BRIDGE=1 rm -rfv `find -type d -name *.pytest_cache*`


version:
	@echo "🔧 Generating version tag..."
	@RELEASE_VERSION=$$(( $$(git tag --list 'v*' | wc -l) + 1 )); \
	MAIN_COUNT=$$(git log origin/master --grep='Merge pull request' --oneline | wc -l); \
	DEV_COUNT=$$(git log origin/dev --grep='Merge pull request' --oneline | wc -l); \
	REPOSITORY_NAME=$${GITHUB_REPOSITORY#*/}; \
	VERSION_TAG="$$RELEASE_VERSION.$$MAIN_COUNT.$$DEV_COUNT"; \
	echo "REPOSITORY_NAME=$$REPOSITORY_NAME"; \
	echo "VERSION_TAG=v$$VERSION_TAG" ; \
	echo && echo && echo "-> To push the tag to github run"; \
	echo "git push origin v$$VERSION_TAG"; \
	echo && echo ""
