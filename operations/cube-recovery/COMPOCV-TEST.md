# CompoCV persistent Cube test site

The existing Stalwart OIDC boundary at `cube.re8ch.com` protects
`/compocv-test/` and `/test-rpc/`. The internal router restores `/` to the recovered
Cube UI. The retired Cube DNS declaration is reactivated through the existing external-dns
controller at the inventory-approved public edge `223.159.210.222`. No new listener,
public IP or OAuth client is created.
OAuth identity tokens and cookies are not forwarded into the test guest;
only the product's own test JWT reaches the test RPC. The router mounts only the
private Cube traffic header from `compocv-cube-test-access`, never SDK credentials.

The sandbox is `31b7f25e4ef04efe874818f7a3d02dd3`, owned operationally by the
`re8ch` application tenant, with private traffic, a masked `cube.re8ch.com` host,
two CPUs, 4 GiB RAM, an 8 GiB writable layer, and timeout `-1` (no expiration).
Template `tpl-20c7da2257b1416eb1a0127d` reuses the accepted root filesystem
`rfs-f4b45fbf282e9617e4d02e33`, SHA256
`968dd364c1b9d3042fdc445076fa2b04a87582b60ae6b7124fe816ddda7f1709`.
Only guest DNS changes to `223.5.5.5` and `1.1.1.1`; cluster Service DNS is not
reachable from this guest. No host route or cluster DNS configuration changes.

The baseline is reviewed CompoCV commit
`e9e29625041e4ce0dae547c538c3707941d527a9` (PR #6). PostgreSQL and PostgREST
listen only on guest loopback, use independent test credentials and synthetic
users, and never receive a production database URL. Vite serves test mode with
hot reload and noindex. Database files persist in `/var/lib/compocv-test` across
application restarts and Cube pause/resume; deleting the sandbox deletes its
writable layer. This test instance is not a database backup or an HA service.

## Credentials

- `cube-trial/compocv-cube-test-access`: SDK state and private traffic header;
  replace only when recreating the sandbox, then reconcile the exact router target.
- `cube-trial/compocv-cube-test-data`: four independently generated test-only
  credentials, injected through the Cube SDK into a mode-0600 guest file.
  Rotate with the test database and synthetic accounts, never independently.
- Existing Stalwart OAuth credentials remain in `oauth2-proxy-cube`.

## Delivery and acceptance

Pass repository validation and a signed PR, bootstrap only the new router objects
through Cloud Platform, apply the exact cube-trial release Role, then publish the
existing static-release contract. Reuse its digest on retry. Check unauthenticated
requests still require OIDC, authenticated HTML and HMR work, test RPC authentication
and cross-user isolation hold, raw tables are denied, and database data survive a
runtime restart. Compare the production deployment generations/images and public
endpoint before and after. Merging this platform PR does not deploy CompoCV production.

The first synthetic feedback entered the private CompoCV Issue #7 and Projects #1
through the existing Stalwart JMAP intake; repeated intake preserved triage without
duplication. Improvement PR #8 adds a bilingual test-only banner and verifies its
absence from both production bundles. The initial synthetic message required a
single-message release from Junk; no global spam policy was weakened. Automated
mail replies and thread synchronization are outside this first intake experiment.
