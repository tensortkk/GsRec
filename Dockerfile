FROM python:3.6.15

WORKDIR /app
COPY . /app

RUN echo "Asia/Shanghai" > /etc/timezone && rm /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

RUN mkdir -p /root/.pip/ && \
    mv /app/bin/pip.conf /root/.pip/
ENV PIP_CONFIG_FILE=/root/.pip/pip.conf

ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"
RUN pip install --upgrade pip && \
    pip3 install -r ./bin/requirements.txt && \
    rm /app/bin/requirements.txt
RUN chmod -R 755 /app/bin/
RUN chmod -R 755 /var/log/server

EXPOSE 5001

ENTRYPOINT ["/app/bin/docker-entrypoint"]
CMD ["server"]
