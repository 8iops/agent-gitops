# Cross-organization context

GitHub context is a graph across repositories and organizations. References use
`owner/repository#number` or a full GitHub URL. A bare `#number` is reserved for
the current repository.

The reviewed context map is `governance/cross-org-context.json`. It names the
Projects and adjacent GitOps authorities that may appear in parent Issues,
sub-issues, pull requests and evidence links. GitHub resolves the reference;
repository visibility and the reader's permissions determine what can be read.

Static sanitized context is published through GitHub Pages. Public Issues,
Discussions and Wiki pages follow the shared evidence privacy contract. Raw
runtime observations, Kubernetes output and investigations remain in the
private observation Project or an approved evidence system.
