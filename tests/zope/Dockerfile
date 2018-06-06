FROM python:2.7-alpine3.7
RUN apk add --update build-base su-exec bash
RUN adduser -D -u 1000 zope
RUN mkdir -p /var/zope
WORKDIR /var/zope
COPY add_file.py buildout.cfg bootstrap.py /var/zope/
RUN chown -R zope:zope /var/zope
USER zope
RUN python2 /var/zope/bootstrap.py -c /var/zope/buildout.cfg
RUN python2 /var/zope/bin/buildout -Nv -c /var/zope/buildout.cfg
RUN python2 /var/zope/bin/instance run /var/zope/add_file.py
COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["start"]
