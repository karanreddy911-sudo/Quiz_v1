# Jenkins server with the Docker CLI installed, so pipelines can run "docker build/run".
# It talks to the host's Docker engine through the mounted /var/run/docker.sock.
FROM jenkins/jenkins:lts-jdk17

USER root
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker/buildx-bin /buildx /usr/libexec/docker/cli-plugins/docker-buildx
