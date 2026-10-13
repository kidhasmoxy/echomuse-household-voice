# Migration and operation

This companion has a different repository, slug and private `/data` volume.
Installing it does not migrate the official controller. Do not uninstall the
official app or overwrite its private data. App protection stays enabled.

## Before cutover

1. Record the installed official app version and actual image identity through
   an authorized inspection path. A public tag digest is not evidence of what
   the existing host has pulled.
2. Create a fresh, scoped Supervisor backup including the official EchoMuse app
   and all its private data. Keep recovery material privately; inspect archive
   contents and rehearse restoration in an isolated, no-network environment.
   A successful backup listing or zero reported size is not restore proof.
3. Stage the new companion without starting it. Preserve the original backup,
   database, device-link certificates/keys, recordings, account/configuration data
   and device identities. Stop the official controller at the approved cutover,
   then use the reviewed platform-supported migration path to copy the complete
   quiescent private data into the new app's volume. Do not copy a running SQLite
   file alone, bypass Supervisor protection, or assume another slug's backup can
   be restored automatically. Verify file ownership, integrity and permissions.
4. Re-enter only the reviewed app options. Retain the stock controller's settings
   and device identity; leave external audio disabled until the HA receiver and
   exact per-device credentials are provisioned. No credential belongs in Git.
5. Verify only one controller can listen on the host ports, start this companion,
   and check health, existing device identities and microphone controls. Pilot
   one explicitly selected device; other devices must stay on the stock path.

## External audio configuration

Provision the device in the canonical Household Voice integration's administrator
interface first. Use its exact controller device ID, HTTPS endpoint, scoped key ID
and credential. The add-on options are `external_audio_enabled` (default false)
and `external_audio_devices`, a list of `controller_device_id`, `endpoint`,
`key_id` and `key_hex`. The controller validates HTTPS and the exact key formats.
Save those values only through the companion's protected options
or the documented private `/data` provisioning path. TLS verification remains
enabled; a private CA may use upstream's read-only `/ssl` certificate option.
No alternate endpoint is guessed and no local audio fallback is assumed.

Both the HA receiver and media provider must reach the intended private services.
The paired Music Assistant speaker must be able to fetch HA-generated audio.
Provider completion is not acoustic delivery proof. Before wider rollout verify
wake ducking, correct room output, question/answer recording, announcements,
audiobook progress after resume, manual interruption, restarts, and hold recovery.

An unknown external playback outcome keeps a durable microphone hold. Do not
delete its journal or toggle routing off to clear it. Use explicit administrative
recovery only after checking the remote output stopped; recovery cannot establish
physical silence on its own.

## Backups and rollback

This app requests cold backups to obtain quiescent private state. The temporary
stop interrupts voice service. Backups include credentials, device state, audio
and durable holds; protect them and their recovery keys. There is no broad backup
exclusion and no automatic removal of recordings or migration snapshots.

For rollback, revoke/disable the new HA receiver's admission, stop the companion,
and confirm no remote output remains. Preserve its private data for diagnosis and
any uncertain holds. Restart the preserved official app with its original data
and verified image. Never run both controllers at once or feed a newer database
to an older image without a verified compatible restore plan. No rollback script
deletes user state or quietly clears holds.
