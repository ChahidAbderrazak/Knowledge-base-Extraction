#!/bin/bash
. .env  2>/dev/null

# #### -----------------------   GET THE IP ADDRESSES OF THE RUNNING DOCKER  -------------------------------
###! for docker-compose
docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -aq) > .env-ip
# cat .env-ip


# remove the ' - ' / from the raw output: NB!: 2>/dev/null || true //: is added to ignore the Operation not permitted
sed -i 's/ - /=/g' .env-ip 2>/dev/null || true
sed -i 's|/||g' .env-ip 2>/dev/null || true
sed -i '/=$/d' .env-ip 2>/dev/null || true

# # display the container's IP addresses
# cat .env-ip

# Load the .env-ip variables
. .env-ip  2>/dev/null

#### -----------------------   RUNNING APP SERVERS  -------------------------------
echo && echo "[${PROJECT_NAME}][Servers] the running servers IPs and URLs :"

#### -----------------------   APP  -------------------------------
eval "APP_CNTNR_IP=\$${PROJECT_NAME}_app"
if [ "$APP_CNTNR_IP" != "" ] ; then
	echo "APP_CNTNR_IP=${APP_CNTNR_IP}" >>.env-ip
	echo -e "-- APP server IP = ${APP_CNTNR_IP} "
	echo "APP_SERVER_IP=${APP_CNTNR_IP}" >>.env-ip
fi


#### -----------------------   WEBAPP  -------------------------------
eval "WEBAPP_CNTNR_IP=\$${PROJECT_NAME}_webapp"
if [ "$WEBAPP_CNTNR_IP" != "" && "$APP_CNTNR_IP" != "$" ] ; then
	WEBAPP_SERVER_URL="http://$WEBAPP_CNTNR_IP:${APP_HOST_PORT}"
	echo "WEBAPP_CNTNR_IP=${WEBAPP_CNTNR_IP}" >>.env-ip
	echo -e "-- WEBAPP server URL = ${WEBAPP_SERVER_URL} \t OR \t http://localhost:${APP_HOST_PORT}"
	sed -i '/WEBAPP_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "WEBAPP_SERVER_URL=${WEBAPP_SERVER_URL}" >>.env-ip
	# xdg-open "${WEBAPP_SERVER_URL}"
fi

#### -----------------------  MLOPs RUNNING SERVERS  -------------------------------
. .env-mlops  2>/dev/null
echo  && echo "------------------------------------------------------"
echo "[${PROJECT_NAME}][Servers] the MLOPs servers URLs :"

#### -----------------------   ZENML  -------------------------------
eval "ZENML_CNTNR_IP=\$$ZENML_CNTNR_NAME"
if [[ "$ZENML_CNTNR_IP" != "" && "$ZENML_CNTNR_IP" != "$" ]] ; then
	ZENML_SERVER_URL="http://$ZENML_CNTNR_IP:${ZENML_HOST_PORT}"
	echo "ZENML_CNTNR_IP=${ZENML_CNTNR_IP}" >>.env-ip
	echo -e "-- ZENML server URL = ${ZENML_SERVER_URL} \t OR \t http://localhost:${ZENML_HOST_PORT}"
	sed -i '/ZENML_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "ZENML_SERVER_URL=${ZENML_SERVER_URL}" >>.env-ip
	# xdg-open "${ZENML_SERVER_URL}"
fi

#### -----------------------   Apache Superset  -------------------------------
eval "SUPERSET_CNTNR_IP=\$$SUPERSET_CNTNR_NAME"
if [[ "$SUPERSET_CNTNR_IP" != "" && "$SUPERSET_CNTNR_IP" != "$" ]]; then
	SUPERSET_SERVER_URL="http://$SUPERSET_CNTNR_IP:${SUPERSET_HOST_PORT}"
	echo "SUPERSET_CNTNR_IP=${SUPERSET_CNTNR_IP}" >>.env-ip
	echo -e "-- SUPERSET server URL = ${SUPERSET_SERVER_URL} \t OR \t http://localhost:${SUPERSET_HOST_PORT}"
	sed -i '/SUPERSET_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "SUPERSET_SERVER_URL=${SUPERSET_SERVER_URL}" >>.env-ip
	# xdg-open "${SUPERSET_SERVER_URL}"
fi

#### -----------------------   MINIO  -------------------------------
eval "MINIO_CNTNR_IP=\$$MINIO_CNTNR_NAME"
if [[ "$MINIO_CNTNR_IP" != "" && "$MINIO_CNTNR_IP" != "$" ]]; then
	MINIO_SERVER_URL="http://$MINIO_CNTNR_IP:${MINIO_HOST_PORT}"
	echo "MINIO_CNTNR_IP=${MINIO_CNTNR_IP}" >>.env-ip
	echo -e "-- MINIO server URL = ${MINIO_SERVER_URL} \t OR \t http://localhost:${MINIO_HOST_PORT}"
	sed -i '/MINIO_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "MINIO_SERVER_URL=${MINIO_SERVER_URL}" >>.env-ip
	# xdg-open "${MINIO_SERVER_URL}"
fi


#### -----------------------   REDIS -------------------------------
eval "REDIS_CNTNR_IP=\$$REDIS_CNTNR_NAME"
if [[ "$REDIS_CNTNR_IP" != "" && "$REDIS_CNTNR_IP" != "$" ]] ; then
	REDIS_SERVER_URL="http://$REDIS_CNTNR_IP:${REDIS_HOST_PORT}"
	echo -e "-- REDIS server URL = ${REDIS_SERVER_URL} \t OR \t http://localhost:${REDIS_HOST_PORT}"
	sed -i '/REDIS_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "REDIS_SERVER_URL=${REDIS_SERVER_URL}" >>.env-ip
	# xdg-open "${REDIS_SERVER_URL}"
fi

#### -----------------------   REDIS GUI -------------------------------
eval "REDIS_GUI_CNTNR_IP=\$$REDIS_GUI_CNTNR_NAME"
if [[ "$REDIS_GUI_CNTNR_IP" != "" && "$REDIS_GUI_CNTNR_IP" != "$" ]] ; then
	REDIS_GUI_SERVER_URL="http://$REDIS_GUI_CNTNR_IP:${REDIS_GUI_HOST_PORT}"
	echo -e "-- REDIS GUI URL = ${REDIS_GUI_SERVER_URL} \t OR \t http://localhost:${REDIS_GUI_HOST_PORT}"
	sed -i '/REDIS_GUI_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "REDIS_SERVER_URL=${REDIS_GUI_SERVER_URL}" >>.env-ip
	# xdg-open "${REDIS_GUI_SERVER_URL}"
fi


#### -----------------------   POSTGRES  -------------------------------
eval "POSTGRES_CNTNR_IP=\$$POSTGRES_CNTNR_NAME"
if [[ "$POSTGRES_CNTNR_IP" != "" && "$POSTGRES_CNTNR_IP" != "$" ]] ; then
	POSTGRES_SERVER_URL="http://$POSTGRES_CNTNR_IP:${POSTGRES_HOST_PORT}"
	echo -e "-- POSTGRES server URL = ${POSTGRES_SERVER_URL} \t OR \t http://localhost:${POSTGRES_HOST_PORT}"
	sed -i '/POSTGRES_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "POSTGRES_SERVER_URL=${POSTGRES_SERVER_URL}" >>.env-ip

	# # data base credentials
	# "postgres://YourUserName:YourPassword@YourHostname:5432/YourDatabaseName"
	POSTGRES_DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_CNTNR_IP}:${POSTGRES_HOST_PORT}/${POSTGRES_DATABASE}"
	echo "POSTGRES_CNTNR_IP=${POSTGRES_CNTNR_IP}" >>.env-ip
	echo "POSTGRES_DATABASE_URL=${POSTGRES_DATABASE_URL}" >>.env-ip
	# echo && echo "POSTGRES_CNTNR_IP=${POSTGRES_CNTNR_IP}"
	echo -e "-- POSTGRES_DATABASE_URL=${POSTGRES_DATABASE_URL} \t OR \t http://localhost:${POSTGRES_HOST_PORT}"

	# xdg-open "${POSTGRES_SERVER_URL}"
fi


#### -----------------------   MySQL  -------------------------------
eval "MySQL_CNTNR_IP=\$$MySQL_CNTNR_NAME"
if [[ "$MySQL_CNTNR_IP" != "" && "$MySQL_CNTNR_IP" != "$" ]] ; then
	MySQL_SERVER_URL="http://$MySQL_CNTNR_IP:${MySQL_HOST_PORT}"
	echo -e "-- MySQL server URL = ${MySQL_SERVER_URL} \t OR \t http://localhost:${MySQL_HOST_PORT}"
	sed -i '/MySQL_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "MySQL_SERVER_URL=${MySQL_SERVER_URL}" >>.env-ip

	# # data base credentials
	MySQL_HOST_IP="${MySQL_CNTNR_IP}"
	echo "MySQL_HOST_IP=${MySQL_HOST_IP}" >>.env-ip
	echo "MySQL_HOST_PORT=${MySQL_HOST_PORT}" >>.env-ip
	# xdg-open "${MySQL_SERVER_URL}"
fi


#### -----------------------   MLFLOW  -------------------------------
eval "MLFLOW_CNTNR_IP=\$$MLFLOW_CNTNR_NAME"
if [[ "$MLFLOW_CNTNR_IP" != "" && "$MLFLOW_CNTNR_IP" != "$" ]] ; then
	MLFLOW_SERVER_URL="http://$MLFLOW_CNTNR_IP:${MLFLOW_HOST_PORT}"
	echo -e "-- MLFLOW server URL = ${MLFLOW_SERVER_URL} \t OR \t http://localhost:${MLFLOW_HOST_PORT}"
	sed -i '/MLFLOW_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "MLFLOW_SERVER_URL=${MLFLOW_SERVER_URL}" >>.env-ip
	echo "S3_LOCAL_DIR=${S3_LOCAL_DIR}">>.env-ip
	echo "-- MLflow artifact -->  S3_LOCAL_DIR=${S3_LOCAL_DIR}"

	#### -----------------------   UPDATE THE MLFLOW_URI  -------------------------------
	sed -i "s|mlflow_uri:.*|mlflow_uri: $MLFLOW_SERVER_URL|g" config/config.yaml 2>/dev/null || true
	# xdg-open "${MLFLOW_SERVER_URL}"
fi


#### -----------------------   JENKINS  -------------------------------
eval "JENKINS_CNTNR_IP=\$$JENKINS_CNTNR_NAME"
if [[ "$JENKINS_CNTNR_IP" != "" && "$JENKINS_CNTNR_IP" != "$" ]] ; then
	JENKINS_SERVER_URL="http://$JENKINS_CNTNR_IP:${JENKINS_HOST_PORT}"
	echo -e "-- JENKINS server URL = ${JENKINS_SERVER_URL} \t OR \t http://localhost:${JENKINS_HOST_PORT}"
	sed -i '/JENKINS_SERVER_URL/d' .env-ip 2>/dev/null || true
	echo "JENKINS_SERVER_URL=${JENKINS_SERVER_URL}" >>.env-ip

	# xdg-open "${JENKINS_SERVER_URL}"
fi

echo "------------------------------------------------------"
# cp .env-ip ../.env-ip
