# Reference data

`src/stratagent/data/license_texts.json` contains five license texts from
[SPDX license-list-data](https://github.com/spdx/license-list-data), used solely
as static comparison reference data. These texts retain their original license
notices and are not re-licensed as Stratagent source code. Immutable upstream
URLs and SHA-256 values are recorded in `license_sources.json` beside the data.

Discovered third-party skill/sub-agent content is never bundled into this source
distribution. Installed content retains its own license and notices, recorded
in each workspace's lockfile and generated notice files.
