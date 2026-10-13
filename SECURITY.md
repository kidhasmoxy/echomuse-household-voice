# Reporting security issues

Use this repository's private vulnerability reporting if enabled. Do not post
credentials, recordings, database files, diagnostics archives, device identifiers,
private hostnames, or household inventory in an issue. Share a sanitized reproduction.

The controller runs on the host network for discovery and native device ports.
Keep it on the trusted LAN and keep the admin dashboard behind authenticated HA
ingress. No new Docker API, Supervisor API, privileged capabilities, or unrestricted
host-directory mounts are requested. Source provisioning secrets belong only in
protected runtime configuration. Backups contain credentials and need equivalent
protection. Unknown playback outcomes must not be treated as confirmed silence.

The base image is pinned for reproducibility, not permanently exempt from updates.
Review upstream security releases, deliberately advance the source/base pins,
reapply the small patch, and rerun the complete image and HA compatibility checks.
