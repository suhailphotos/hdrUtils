# syntax=docker/dockerfile:1.7

# --- builder ---------------------------------------------------------------
FROM ubuntu:24.04 AS build
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential git cmake ninja-build meson pkg-config \
    libglib2.0-dev libexpat1-dev liborc-0.4-dev \
    libjpeg-turbo8-dev libpng-dev libtiff-dev libwebp-dev libexif-dev liblcms2-dev \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ARG PREFIX=/opt/vips
ENV PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig
ENV LD_LIBRARY_PATH=$PREFIX/lib

# ---- libultrahdr ----------------------------------------------------------
ARG LIBUHDR_REF=main
WORKDIR /tmp/build
RUN git clone --depth 1 --branch ${LIBUHDR_REF} https://github.com/google/libultrahdr.git
RUN cmake -S libultrahdr -B build-uhdr -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=${PREFIX} \
      -DUHDR_MAX_DIMENSION=65500 \
 && cmake --build build-uhdr \
 && cmake --install build-uhdr

# ---- libvips + UltraHDR ---------------------------------------------------
ARG LIBVIPS_REF=master
RUN git clone --depth 1 https://github.com/libvips/libvips.git \
 && cd libvips && git checkout ${LIBVIPS_REF} \
 && meson setup build \
      --prefix=${PREFIX} -Dlibdir=lib \
      -Duhdr=enabled \
      -Dintrospection=disabled -Ddeprecated=false -Dexamples=false \
 && meson compile -C build \
 && meson install -C build

# --- runtime ---------------------------------------------------------------
FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      libglib2.0-0 libexpat1 liborc-0.4-0 \
      libjpeg-turbo8 libpng16-16 libtiff6 \
      libwebp7 libwebpmux3 libwebpdemux2 \
      libexif12 liblcms2-2 \
      python3 python3-pip python3-venv \
 && rm -rf /var/lib/apt/lists/*

ENV VIPS_PREFIX=/opt/vips
COPY --from=build ${VIPS_PREFIX} ${VIPS_PREFIX}
ENV LD_LIBRARY_PATH=${VIPS_PREFIX}/lib
ENV PKG_CONFIG_PATH=${VIPS_PREFIX}/lib/pkgconfig

# Create a dedicated venv for Python deps
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir pyvips

# Make venv & vips tools come first
ENV PATH="/opt/venv/bin:${VIPS_PREFIX}/bin:${PATH}"

WORKDIR /work
# no default entrypoint; compose will supply ["python3"]
