ARG VARIANT=debian:bookworm
FROM ${VARIANT}
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update --fix-missing && \
    apt-get upgrade --assume-yes --no-install-recommends && \
    apt-get install --assume-yes --no-install-recommends \
    build-essential debmake debhelper-compat dh-python \
    python3 python3-all python3-setuptools \
    protobuf-compiler python3-protobuf && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the detd to the container.
ADD tmp_detd /usr/local/src/detd/

WORKDIR /usr/local/src/detd/tools

# Work around bug in debmake and run the packaging script.
RUN ln -s /usr/lib/debmake/python3.short /usr/lib/debmakepython3.short && \
    ln -s /usr/lib/debmake/python3.long /usr/lib/debmakepython3.long && \
    ./package_debian.sh
