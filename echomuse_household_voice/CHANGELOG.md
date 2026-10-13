# 2.26.0-hv.1

- Initial independent companion app based on EchoMuse controller 2.26.0.
- Adds opt-in authenticated Household Voice routing; unconfigured devices retain
  upstream behavior. Unknown playback keeps an explicit recovery hold.
- Public pinned base image and four reviewed module replacements; amd64 only.
- Separate app slug and private data volume. Installation is not an in-place
  conversion of the official EchoMuse app.
