FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY headers.inc /etc/nginx/conf.d/headers.inc
COPY site/ /usr/share/nginx/html/
EXPOSE 80
