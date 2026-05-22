# rocket-distro

Self-contained distribution package for running [Rocket](https://github.com/paranoid-software/rocket) from published images.

Pulls `rocket-api`, `rocket-bridge`, `rocket-indexer` from `ghcr.io/paranoid-software/*`. Bundles the local Logy and Zookeeper emulators (small Python images, built on first `up`). No Rocket source code required.

See [docker/README.md](docker/README.md) for setup.
