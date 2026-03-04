FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config and static files
COPY nginx.conf /etc/nginx/conf.d/coreskill.conf
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80
