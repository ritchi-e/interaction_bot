# Bookworm dropped Asterisk. Sid is the suite that still publishes it for arm64.
# Debian names the open-source Opus module codec_opus_open_source.so.
FROM debian:sid-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends asterisk \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr -name 'codec_opus*.so' | grep -q .

COPY conf/ /etc/asterisk/
EXPOSE 5061/tcp 8088/tcp 5038/tcp
CMD ["asterisk", "-f", "-vvv"]
