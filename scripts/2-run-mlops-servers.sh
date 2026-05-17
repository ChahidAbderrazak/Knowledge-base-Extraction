#!/bin/bash

# open MLOps frameworks
#### -------------------------   RUN MLOPS SERVERS  ----------------------------
dir=$(pwd)
project_name="${PWD##*/}"

# run the mlops servers
mlops_dir=../MLOPs-servers/

if [ -d $mlops_dir ]; then
    cd $mlops_dir
    bash scripts/open-servers-browser.sh

    #### ---------------   LOAD / SHOW THE SERVERS IPS SERVERS  --------------------
    cp .env-ip $dir/.env-ip-mlops
    cd $dir
    . .env-ip-mlops
    . .env

    #### -----------------------   UPDATE MLFLOW  URI -------------------------------
    echo && echo "[${PROJECT_NAME}][Docker-Compose] Updating the configuration file..."

    if [ "$MLFLOW_SERVER_URL" != "" ] ; then
        #### --------------------   UPDATE THE MLFLOW_URI  -------------------------
        echo "   -> updating the mlflow_uri in <config/config.yaml> file "
        sed -i "s|mlflow_uri:.*|mlflow_uri: $MLFLOW_SERVER_URL|g" config/config.yaml
        echo "   -> S3_LOCAL_DIR=${S3_LOCAL_DIR}"
        # xdg-open "${MLFLOW_SERVER_URL}"
    fi


else
    echo && echo "MLOPs-servers directory does not exist"
    exit 0
fi
