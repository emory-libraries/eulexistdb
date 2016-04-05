#!/usr/bin/env bash

set -e

if [[ "${EXIST_DB_VERSION}" == eXist* ]]; then
  echo "reset data and logfiles for ${EXIST_DB_VERSION}"
  cd ${EXIST_DB_FOLDER}
  ./build.sh clean-default-data-dir
  rm webapp/WEB-INF/logs/*.log
  exit 0
fi

echo "exclude ${EXIST_DB_VERSION} from cache"
rm -rf ${EXIST_DB_FOLDER}