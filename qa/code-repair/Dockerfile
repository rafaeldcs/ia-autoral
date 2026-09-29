FROM caddy:2-alpine AS caddy
FROM localauthor-functional-lab:1
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy
USER root
# Strip the upstream bind-service file capability; validation needs no privileges.
RUN cat /usr/local/bin/caddy > /tmp/caddy && chmod 755 /tmp/caddy && mv /tmp/caddy /usr/local/bin/caddy
USER 10001:10001
ENTRYPOINT ["python3"]
