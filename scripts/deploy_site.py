"""Assemble the deployable site: build/deploy, the contents of the repository's `deploy` branch.

usage: python scripts/deploy_site.py

Builds the showcase with absolute link-preview addresses, then adds what the public
address promises: the ready-made stylesheet at /css/four-irish-typefaces.css with the
web fonts it points to (other sites link them), an nginx configuration and a Dockerfile.
Coolify builds the Dockerfile on every push to `deploy`, so the published site is only
ever these files, never the repository. CI runs this after the tests pass on main.
"""
import paths
import json, os, shutil
import showcase
from build2 import VERSION

SLUG = 'irish-typefaces'
URL = f'https://{SLUG}.apps.drayne.xyz'
DEST = os.path.join(paths.BUILD, 'deploy')

DOCKERFILE = '''FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/
EXPOSE 80
'''

DOCKERIGNORE = '''*
!site/
!site/**
!nginx.conf
'''

# Every response carries the security headers; nginx drops inherited add_header lines in a
# location that adds its own, so each location repeats them through the include.
HEADERS = r'''add_header X-Content-Type-Options nosniff always;
add_header Referrer-Policy strict-origin-when-cross-origin always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'" always;
'''

NGINX = r'''server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    server_tokens off;
    charset utf-8;
    client_max_body_size 1m;
    client_body_timeout 15s;
    send_timeout 30s;
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml font/ttf font/otf text/plain;

    # The page and its modules are imported without version stamps, so they revalidate
    # (cheap 304s); fonts and images change only with a release.
    location / {
        limit_except GET { deny all; }
        include /etc/nginx/conf.d/headers.inc;
        add_header Cache-Control "no-cache" always;
        try_files $uri $uri/ =404;
    }
    location ~ ^/(js|data)/ {
        limit_except GET { deny all; }
        include /etc/nginx/conf.d/headers.inc;
        add_header Cache-Control "no-cache" always;
    }
    # The ready-made stylesheet and fonts are for other sites too, so they allow any origin.
    location /css/ {
        limit_except GET { deny all; }
        include /etc/nginx/conf.d/headers.inc;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Cache-Control "no-cache" always;
    }
    location /fonts/ {
        limit_except GET { deny all; }
        include /etc/nginx/conf.d/headers.inc;
        add_header Access-Control-Allow-Origin "*" always;
        add_header Cache-Control "public, max-age=86400" always;
        location ~* \.ttf$ {
            default_type font/ttf;
            include /etc/nginx/conf.d/headers.inc;
            add_header Access-Control-Allow-Origin "*" always;
            add_header Cache-Control "public, max-age=86400" always;
        }
        location ~* \.otf$ {
            default_type font/otf;
            include /etc/nginx/conf.d/headers.inc;
            add_header Access-Control-Allow-Origin "*" always;
            add_header Cache-Control "public, max-age=86400" always;
        }
    }
    location ~ ^/(img|vendor|downloads)/ {
        limit_except GET { deny all; }
        include /etc/nginx/conf.d/headers.inc;
        add_header Cache-Control "public, max-age=86400" always;
    }
    location ~ /\. { deny all; }
}
'''

README = f'''# Deployed site (generated)

This branch is written by CI (`scripts/deploy_site.py`) from `main` after the tests pass.
Do not edit it: change the showcase on `main` instead. Coolify builds the Dockerfile here
on every push and serves it at {URL}/.

- `site/`: the showcase site, version {VERSION}, plus `/css/four-irish-typefaces.css` and the
  web fonts it links, for other sites to use
- `nginx.conf`, `headers.inc`: caching, cross-origin access for the fonts and stylesheet, and
  the security headers
- `publish.json`: the app's settings for the Drayne publishing helper
'''


def build():
    os.environ.setdefault('SITE_URL', URL)
    showcase.build()
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    site = os.path.join(DEST, 'site')
    shutil.copytree(showcase.DEST, site)
    # the public stylesheet, at the address the page gives, with the fonts it references
    shutil.copy(os.path.join(paths.ROOT, 'css', 'four-irish-typefaces.css'), os.path.join(site, 'css', 'four-irish-typefaces.css'))
    for fmt in ('woff2', 'woff'):
        shutil.copytree(os.path.join(paths.ROOT, 'fonts', fmt), os.path.join(site, 'fonts', fmt))
    w = lambda name, text: open(os.path.join(DEST, name), 'w', encoding='utf-8').write(text)
    w('Dockerfile', DOCKERFILE.replace('COPY nginx.conf /etc/nginx/conf.d/default.conf',
                                       'COPY nginx.conf /etc/nginx/conf.d/default.conf\nCOPY headers.inc /etc/nginx/conf.d/headers.inc'))
    w('.dockerignore', DOCKERIGNORE + '!headers.inc\n')
    w('nginx.conf', NGINX)
    w('headers.inc', HEADERS)
    w('README.md', README)
    w('publish.json', json.dumps(dict(
        slug=SLUG, title='Four Irish Typefaces',
        description='Céilí, Carrick, Kilfane and Tuam Uncial, the winners of the 1978 Design an Irish Typeface competition, rebuilt as free fonts to try, play with and download.',
        access='public', port=80, repository='ddrayne/four-irish-typefaces', branch='deploy',
        buildPack='dockerfile', memoryMiB=256, cpus=0.5, domain=URL), indent=2, ensure_ascii=False) + '\n')
    for dirpath, dirs, files in os.walk(DEST):
        for n in dirs: os.chmod(os.path.join(dirpath, n), 0o755)
        for n in files: os.chmod(os.path.join(dirpath, n), 0o644)
    print('assembled', DEST)


if __name__ == '__main__':
    build()
