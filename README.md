# Deployed site (generated)

This branch is written by CI (`scripts/deploy_site.py`) from `main` after the tests pass.
Do not edit it: change the showcase on `main` instead. Coolify builds the Dockerfile here
on every push and serves it at https://irish-typefaces.apps.drayne.xyz/.

- `site/`: the showcase site, version 2.010, plus `/css/four-irish-typefaces.css` and the
  web fonts it links, for other sites to use
- `nginx.conf`, `headers.inc`: caching, cross-origin access for the fonts and stylesheet, and
  the security headers
- `publish.json`: the app's settings for the Drayne publishing helper
