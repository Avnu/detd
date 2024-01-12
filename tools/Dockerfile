FROM debian:bookworm
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update --fix-missing && \
    apt-get upgrade --assume-yes --no-install-recommends && \
    apt-get install --assume-yes --no-install-recommends \
    debmake debhelper-compat dh-python \
    python3 python3-all python3-setuptools \
    protobuf-compiler python3-protobuf && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ADD . /usr/local/src/detd/

WORKDIR /usr/local/src/detd/tools

# Work around bug in debmake
RUN ln -s /usr/lib/debmake/python3.short /usr/lib/debmakepython3.short
RUN ln -s /usr/lib/debmake/python3.long /usr/lib/debmakepython3.long

CMD ./package_debian.sh

