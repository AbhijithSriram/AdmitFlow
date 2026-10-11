# MinIO no longer publishes prebuilt community images (docker.io/minio/minio is gone and
# quay.io/minio/minio now answers 401), but it still publishes its source. This builds the
# same release the project was developed and tested against, so `docker compose up` works
# on any machine without needing a cached image. The first build takes a few minutes.
FROM golang:1.24-alpine AS build
RUN apk add --no-cache git
ARG MINIO_VERSION=RELEASE.2025-09-07T16-13-09Z
RUN go install github.com/minio/minio@${MINIO_VERSION}

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /go/bin/minio /usr/local/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
