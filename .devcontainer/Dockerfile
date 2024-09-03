FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

ARG NODE_VERSION=20
RUN curl -fsSL https://deb.nodesource.com/setup_$NODE_VERSION.x | bash - && \
  apt-get install -y nodejs

RUN npm install -g aws-cdk@2.152.0
