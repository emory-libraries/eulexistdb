#!/usr/bin/env bash

# shell script to download and install a version of exist for testing

set -e
# Is this version of existDB already cached? Meaning, the folder exists
if [ -d "$EXIST_DB_FOLDER" ]; then
  echo "Using cached eXist DB instance: ${EXIST_DB_VERSION}."
  exit 0
fi

# join some more
TARBALL_URL=https://github.com/eXist-db/exist/archive/${EXIST_DB_VERSION}.tar.gz

mkdir -p ${EXIST_DB_FOLDER}
curl -L ${TARBALL_URL} | tar xz -C ${EXIST_DB_FOLDER} --strip-components=1
cd ${EXIST_DB_FOLDER}
./build.sh

