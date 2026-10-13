FROM ghcr.io/wilbowes/echomuse-controller@sha256:4f21aec35044644d9cec0ed15f941904f6232478d69665b8871031a9b97a6056
ARG BUILD_VERSION=2.26.0-hv.1
ARG BUILD_ARCH=amd64
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}" \
      org.opencontainers.image.source="https://github.com/kidhasmoxy/echomuse-household-voice" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.description="EchoMuse companion with authenticated Household Voice audio routing"
ENV EM_CONTROLLER_VERSION=${BUILD_VERSION}
COPY src/em_controller.py /app/em_controller.py
COPY src/em_api.py /app/em_api.py
COPY src/em_esphome.py /app/em_esphome.py
COPY src/em_household_audio.py /app/em_household_audio.py
COPY LICENSE /app/LICENSE.household-voice
# Keep the pinned upstream em_start.py, dependencies, assets and launch command.
# No installation command, network fetch, credentials, or enabled routing here.
