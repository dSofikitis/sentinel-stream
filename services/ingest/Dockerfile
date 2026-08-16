FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY . ./
RUN CGO_ENABLED=0 go build -o /out/sentinel-ingest .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/sentinel-ingest /usr/local/bin/sentinel-ingest
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/sentinel-ingest"]
