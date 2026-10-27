# Agent GitOps repository

- Use signed commits and pull requests for every desired-state change.
- Never commit credentials or decrypted SOPS material.
- Pin images and OCI/Helm artifacts by digest.
- The production root is `clusters/re8ch`.
- Keep product runtime Deployments excluded when their authority is `product-publisher` or `control-plane-direct`.
