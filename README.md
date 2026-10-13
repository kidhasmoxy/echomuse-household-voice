# EchoMuse Household Voice

An independent EchoMuse companion add-on for authenticated Household Voice audio
routing. It retains EchoMuse's controller and wake-word implementation and adds
four reviewed Python modules. External routing starts disabled. This repository
contains no household configuration or private registry dependency.

## Install and update

The maintainer must first publish the matching versioned GHCR image and make it
public. Then add `https://github.com/kidhasmoxy/echomuse-household-voice` to Home Assistant's app store repositories and select
**EchoMuse Household Voice**. The app's slug is `echomuse_household_voice`, with a separate data
volume from the official controller. Only amd64 is declared; arm64 is not built
or claimed supported by this release.

**Do not start it beside the official controller.** Both need the same host
network ports: dashboard 8768, device WebSocket 8767, TLS 8770, discovery, and the
configured per-device native API range (normally 16001 onward). Changing only the
per-device range does not eliminate the other conflicts. The new app starts
manually; a deliberate migration and one-controller cutover are required.

Use Supervisor to update this fork from this repository's versioned image.
Upstream dashboard release notices/device-firmware controls are not a substitute
for this fork's release process. Prefer an upstream release with equivalent
functionality when one is available. See [migration and rollback](./echomuse_household_voice/DOCS.md)
before copying data, starting the controller, or enabling a device.

## Reproducible public build

`upstream-pin.json` records the public source commit and amd64 base digest.
The Dockerfile copies only four controller modules and the license. It runs no
dependency installer, downloads no assets, and requires no private build secrets.
GitHub Actions verifies the release manifest, builds linux/amd64, then runs the
full derived image against synthetic loopback fixtures with networking disabled.
Those checks prove software behavior; they do not prove microphone, speaker,
native-device, Home Assistant household, or backup-restore acceptance.

```sh
python3 scripts/verify_release.py
python3 -m unittest discover -s tests -v
docker build --platform linux/amd64 -t echomuse-household-test ./echomuse_household_voice
docker run --rm --network none --user 65532:65532 --cap-drop ALL \
  --security-opt no-new-privileges --read-only --tmpfs /tmp:rw,mode=1777,size=256m \
  --memory 1g --cpus 2 -e PYTHONPATH=/app -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD/tests/image_smoke.py:/smoke/image_smoke.py:ro" \
  --entrypoint python echomuse-household-test /smoke/image_smoke.py
```

## Maintainer releases

1. Review upstream changes and the four-module diff. Advance public pins only
   together with verified source/image evidence; keep upstream license notices.
2. Edit the add-on's `config.json` version and Dockerfile default build version.
   Run `python3 scripts/verify_release.py --refresh` after reviewing every changed
   allowlisted file, then run verification and image tests. New files require a
   deliberate manifest allowlist addition; refresh never discovers runtime files.
3. Commit the reviewed source, then push a matching `v<version>` tag. The release
   workflow rejects version mismatches, builds and tests before pushing the exact
   Supervisor image tag, verifies an anonymous pull, and creates a GitHub release
   carrying the immutable digest and provenance manifest. Tags must never be reused.
4. Configure the GitHub `release` environment with required maintainer reviewers.
   Package visibility must be public before the anonymous-pull gate can pass.
   No registry token is stored in this repository: Actions uses its scoped token.
5. Verify Supervisor's pulled digest against the release evidence before a pilot.
   Keep the existing controller and private backup until physical acceptance.

Protected credentials, diagnostics, build logs, recordings, databases, cluster
manifests and Git history are excluded by the preparation allowlist. Text scanning
is an additional check, not a guarantee that arbitrary secrets cannot exist.

[MIT attribution](NOTICE.md) · [Security](SECURITY.md) ·
[HA app configuration](https://developers.home-assistant.io/docs/apps/configuration/)
