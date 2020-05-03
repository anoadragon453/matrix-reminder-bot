# To build the image, run `docker build` command from the root of the
# synapse repository:
#
#    docker build -f docker/Dockerfile .
#
# There is an optional PYTHON_VERSION build argument which sets the
# version of python to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg PYTHON_VERSION=3.6 .
#
#
# And an optional LIBOLM_VERSION build argument which sets the
# version of libolm to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg LIBOLM_VERSION=3.1.4 .
#
ARG PYTHON_VERSION=3.8

FROM docker.io/python:${PYTHON_VERSION}-alpine3.11

##
## Build libolm for matrix-nio e2e support
##

COPY docker/build_and_install_libolm.sh /scripts/

# Install libolm build dependencies
#
# We do all of this in one command in order to add and remove all
# build dependencies in the same docker layer, significantly saving
# space
ARG LIBOLM_VERSION=3.1.4
RUN apk add --no-cache --virtual .build-deps \
	make \
    cmake \
	gcc \
	g++ \
	git \
	libffi-dev \
	python3-dev && \
        # These are our runtime dependencies. We want to keep them
        # around
	    apk add --no-cache --virtual .runtime-deps libstdc++ && \
            # Build libolm at the specified version
            /scripts/build_and_install_libolm.sh ${LIBOLM_VERSION} /olm && \
            # Install matrix-nio with e2e dependencies
            pip install matrix-nio[e2e] && \
            # Delete build dependencies
            apk del .build-deps

# Remove libolm build script
RUN rm -rf scripts