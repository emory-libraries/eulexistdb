#!/usr/bin/env bash

set -e
# Is this version of existDB already cached? Meaning, the folder exists
if [ -d "$EXIST_DB_FOLDER" ]; then
  echo "Using cached eXist DB instance: ${EXIST_DB_VERSION}."
  exit 0
fi

# shell script to download and install a version of exist for testing
export TARBALL=https://github.com/eXist-db/exist/archive/${EXISTDBVERSION}.tar.gz
mkdir -p ${EXISTDBFOLDER}
curl -L ${TARBALL} | tar xz -C ${EXISTDBFOLDER} --strip-components=1
cd ${EXISTDBFOLDER}
./build.sh