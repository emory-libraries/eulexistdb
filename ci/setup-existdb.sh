# shell script to download and install a version of exist for testing
export TARBALL=https://github.com/eXist-db/exist/archive/${EXISTDBVERSION}.tar.gz
mkdir -p ${EXISTDBFOLDER}
curl -L ${TARBALL} | tar xz -C ${EXISTDBFOLDER} --strip-components=1
cd ${EXISTDBFOLDER}
./build.sh