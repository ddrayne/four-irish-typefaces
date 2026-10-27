# Deployed site (generated)

This branch is written by CI (`scripts/deploy_site.py`) from `main` after the tests pass.
Do not edit it: change the showcase on `main` instead. Coolify builds the Dockerfile here
on every push and serves it at https://irish-typefaces.apps.drayne.xyz/.

- `site/`: the showcase site, version 3.100; the fonts are downloaded from the GitHub releases
- `nginx.conf`, `headers.inc`: caching and the security headers (no cross-origin access)
- `publish.json`: the app's settings for the Drayne publishing helper
