
 # load .env variables from list of ENVFILES separated by space
ENVFILES = .env  .env-llm .env-mlops

# Load all env files
define LOAD_ENV
include $(1)
export $(shell sed '/^\#/d; s/=.*//' $(1))
endef
$(foreach envfile,$(ENVFILES),$(eval $(call LOAD_ENV,$(envfile))))

# default project variables
PROJECT_NAME ?= ml-project
export PROJECT_NAME

VERSION ?= ml-cv
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
default: help

# run the demo
docker-demo: docker-build docker-run

# help
help: #-------------------- Showing the help message ---------------------
	@echo "Makefile for ${PROJECT_NAME} project"
	@echo ""
	@echo "Usage:"
	@echo "  make docker-demo      Build & Run a quick demo using Docker containers"
	@echo "  make dev              Run/Access the running the app container"
	@echo ""
	@echo "  make convert-packages Convert requirements.txt to pyproject.toml dependencies"
	@echo "  make docker-build     Build the Docker image and containers  "
	@echo "  make docker-run       Run the Docker containers of the project: $(PROJECT_NAME)"
	@echo "  make docker-app       Run the app container"
	@echo "  make docker-webapp    Run the webapp container endpoint"
	@echo ""
	@echo "  make docker-ip               Get the IP addresses of the running containers"
	@echo "  make docker-stop             Stop the running containers"
	@echo "  make clean            Clean the project build files"
	@echo "  make help             Display this help message"

variables:
	@echo "Building the Python project using: "
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


convert-packages:
	# convert requirements.txt to pyproject.toml dependencies
	# Convert your requirements.txt to pyproject.toml dependencies once locally:
	@NO_AT_BRIDGE=1 poetry config virtualenvs.create false
	grep -vE '^\s*#|^\s*$$' requirements.txt | xargs poetry add --lock

	# save the packages to requirements_version.txt
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory generate-requirement

generate-requirement:
	@echo "Generating requirements.txt from pyproject.toml..."
	@awk '/\[tool.poetry.dependencies\]/ {flag=1; next} /^\[/ {flag=0} flag && /^[a-zA-Z0-9_-]+ *=/ {print $$0}' pyproject.toml \
	| grep -v '^python' \
	| sed -E 's/ *= *"*\^?~?([^"]+)"*/==\1/' \
	> requirements_version.txt


docker-build:#----------------------- BUILDING THE MLOPS containers -----------------------
	@NO_AT_BRIDGE=1 docker system prune -f || docker volume prune -f
	@NO_AT_BRIDGE=1 clear
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory variables

	# get the poetry packages
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory convert-packages

	# build  the project containers
	@echo && echo "[${PROJECT_NAME}][Docker-Compose] Building the app container"
	docker compose -p "${PROJECT_NAME}" -f docker-compose.yml up --build

	#### ----------------   NOTIFICATION MESSAGE -------------------------
	docker system prune -f || docker volume prune -f
	notify-send "[${PROJECT_NAME}][Docker-Compose] is built is finished!!"

	# get the IP addresses
	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory docker-ip

docker-run:  #----------------------- Run all project containers -----------------------
	@echo && echo "[${PROJECT_NAME}][Docker-Compose] Running all project containers..."
	docker compose  -p "${PROJECT_NAME}" -f docker-compose.yml up

	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory docker-ip


docker-app:  #----------------------- Run the app container -----------------------
	@NO_AT_BRIDGE=1 docker system prune -f || docker volume prune -f
	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory docker-ip

	@NO_AT_BRIDGE=1 # run the MINIO containers
	@echo && echo "[${PROJECT_NAME}][Docker-Compose] Running the app container..."
	docker compose  -p "${PROJECT_NAME}" -f docker-compose.yml up -d app


docker-webapp:#----------------------- Run the webapp container -----------------------
	@NO_AT_BRIDGE=1 docker system prune -f || docker volume prune -f
	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory docker-ip

	@NO_AT_BRIDGE=1 # run the MINIO containers
	@echo && echo "[${PROJECT_NAME}][Docker-Compose] Running the webapp container..."
	docker compose  -p "${PROJECT_NAME}" -f docker-compose.yml up -d webapp

	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory docker-ip



wait_for_containers:
	@echo "\n\n ==>Waiting for all containers to start..."
	@START_TIME=$$(date +%s); \
	while :; do \
		STARTING=$$(docker ps --filter "health=starting" --format "{{.Names}}" | wc -l); \
		UNHEALTHY=$$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | wc -l); \
		CRASHED=$$(docker ps --filter "status=exited" --format "{{.Names}}" | grep -v '^waitfordb' | wc -l); \
		\
		if [ "$$CRASHED" -gt 0 ]; then \
			echo -e "\r❌ Crashed: $$CRASHED | ⚠️ Unhealthy: $$UNHEALTHY | ⏳ Starting: $$STARTING"; \
			exit 1; \
		fi; \
		\
		ELAPSED_TIME=$$((`date +%s` - $$START_TIME)); \
		printf "\r[$$ELAPSED_TIME s] ⏳ Monitoring... ❌ Crashed: $$CRASHED | ⚠️ Unhealthy: $$UNHEALTHY | ⏳ Starting: $$STARTING"; \
		\
		if [ "$$STARTING" -eq 0 ] && [ "$$UNHEALTHY" -eq 0 ]; then \
			break; \
		fi; \
		sleep 5; \
	done

	@NO_AT_BRIDGE=1 printf "\n -->✅ All containers are healthy!\n"


docker-ip:#----------------------- Get the IP addresses of the running containers -----------------------
	@NO_AT_BRIDGE=1 # wait for all containers to start
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory wait_for_containers

	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 bash ./scripts/2-run-mlops-servers.sh

docker-stop: #----------------------- STOP all running containers -----------------------
	#### -----------------------   STOP THE PROJECT SERVERS   -------------------------------
	@echo && echo "[${PROJECT_NAME}][Docker-Compose] Stopping all containers..."
	docker compose -p "${PROJECT_NAME}" -f docker-compose.yml stop
	@NO_AT_BRIDGE=1 docker system prune -f || docker volume prune -f


clean:#----------------------- Clean the python/files/build -----------------------
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

dev:   #----------------------- Run the development container -----------------------
	@NO_AT_BRIDGE=1 # get the servers IP addresses
	@NO_AT_BRIDGE=1 $(MAKE) --no-print-directory docker-ip


	@echo "🔍 Checking .env-ip-mlops..."
	@if [ ! -s .env-ip-mlops ]; then \
		echo "⚠️  Warning: .env-ip-mlops is missing or empty!! ";  \
		echo "please make sure to MLOPs servers are running correctly"; \
		echo " "; \
		printf "Do you want to continue anyways [y]: "; \
		read answer; \
		if [ "$$answer" = "y" ]; then \
			echo "Continuing..."; \
			echo "MLOPS_HOST='Not defined'" >> .env-ip-mlops ; \
			cd scripts && make $(MAKECMDGOALS);\
		else \
			echo "Aborted."; \
		fi; \
	else \
		echo "✅ .env-ip-mlops is found. and MLOPs servers are running"; \
		cd scripts && make $(MAKECMDGOALS);\
	fi
