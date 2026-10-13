# Attribution and provenance

This is an independently maintained companion fork of
[EchoMuse by Wil Bowes](https://github.com/wilbowes/EchoMuse), released under MIT.
The original copyright notice and license are preserved in `LICENSE`, the app
folder, and the derived image. This project is not an official EchoMuse release.

The base is upstream `controller-v2.26.0`, source commit
`e119433c0845dfe80f4b1ec44c9e8e8028adbb07`, using the immutable public amd64 image
listed in `upstream-pin.json`. Four modules add opt-in external audio routing and
its authenticated provisioning/recovery behavior. Their reviewed input hashes
and the exported bytes are recorded separately.

The upstream image also contains third-party dependencies, wake/VAD models and
sound assets under their own licenses. Their existing files and notices remain
in the base image; the MIT notice does not relicense those assets. Device firmware
and wake models are inherited unchanged by this packaging layer.
