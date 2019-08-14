# Use Alpine-based Python 3.7 image as base
FROM python:3.7-alpine

MAINTAINER "Vwout <vwout@users.noreply.github.com>"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Build arguments to set metadata labels
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_VERSION="0.0.1"

WORKDIR /usr/src/

COPY proxy proxy/

EXPOSE 8082

# Set entrypoint to proxy, with pre-configured proxy host and port to match the image configuration
ENTRYPOINT ["python", "-m", "proxy", "--proxy-host", "0.0.0.0", "--proxy-port", "8082"]

# Metadata
LABEL maintainer="vwout <vwout@users.noreply.github.com>" \
      org.label-schema.name="os-websocket-proxy" \
      org.label-schema.description="OpenSong Websocket Proxy" \
      org.label-schema.vcs-url="https://github.com/vwout/os-websocket-proxy.git" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.schema-version="$IMAGE_VERSION"
