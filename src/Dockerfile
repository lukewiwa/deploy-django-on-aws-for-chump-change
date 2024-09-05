FROM python:3.12

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

COPY --from=ghcr.io/astral-sh/uv:0.4.5 /uv /usr/local/bin/uv
ENV UV_CACHE_DIR=/tmp/uv UV_LINK_MODE=copy

COPY . .

ENTRYPOINT [ "entrypoint.sh" ]
CMD [ "uv", "run", "gunicorn", "config.wsgi.application" ]