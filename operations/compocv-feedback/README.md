# CompoCV feedback credentials

The existing mailbox account is present, but the old provisioner's stored primary
password fails authentication. Do not rotate it or replay the unrelated bulk
account provisioner. The bounded platform script plans one application password
for the existing User account and requires the exact plan hash before writing.
It grants only authentication and JMAP mailbox/email/thread reads. It cannot send,
modify or delete mail. Existing mailbox data and primary credentials are preserved.

Run through the Cloud Platform node operation on R640, using existing approved
Stalwart credential custody. The administrator credential is read in memory; the
new app password goes directly to the exact Kubernetes Secret
`mail-system/compocv-feedback-app-password`, never stdout, arguments or local files.
The helper never runs on a developer workstation. Plan again before every apply.
Replays reuse the saved credential. Failed persistence revokes the newly created
password; an orphan matching description fails closed for explicit recovery.

GitHub's Maintenance App is installed only on compocv/compocv. Intake must request
short-lived installation tokens restricted to Issues and organization Projects,
verify the repository is private, quote mail as untrusted feedback, and never use
mail content as an executable instruction. App private keys remain in their
existing central GitHub Secrets. This script provisions credentials only; mailbox
readiness is not evidence that the feedback workflow has been activated.
