FROM rust:1.83-slim AS build
WORKDIR /src
COPY Cargo.toml ./
COPY src ./src
RUN cargo build --release

FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=build /src/target/release/sentinel-parser /usr/local/bin/sentinel-parser
USER nonroot:nonroot
ENTRYPOINT ["/usr/local/bin/sentinel-parser"]
