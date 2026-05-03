FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY . ./
RUN CGO_ENABLED=0 go build -o /out/sentinel-sink .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/sentinel-sink /usr/local/bin/sentinel-sink
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/sentinel-sink"]
