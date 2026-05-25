# Changelog

## [1.7.0](https://github.com/bcit-tlu/qcon-api/compare/v1.6.1...v1.7.0) (2026-05-25)


### Features

* **ci:** add Python lint job with ruff ([0a86497](https://github.com/bcit-tlu/qcon-api/commit/0a864976c44143ba6087324dd5f9d1349e52a5b2))

## [1.6.1](https://github.com/bcit-tlu/qcon-api/compare/v1.6.0...v1.6.1) (2026-05-25)


### Bug Fixes

* remove stale release-as and fix CLASSPATH undefined var warning ([dec0ea3](https://github.com/bcit-tlu/qcon-api/commit/dec0ea3c8a57a32b259ef7cce76ea60d4bd63548))

## [1.6.0](https://github.com/bcit-tlu/qcon-api/compare/v0.3.0...v1.6.0) (2026-05-25)


### Bug Fixes

* exclude charts/templates/secrets.yaml from secrets gitignore ([55e77d6](https://github.com/bcit-tlu/qcon-api/commit/55e77d679a94601007e8069ced8c58124154bf56))

## [0.3.0](https://github.com/bcit-tlu/qcon-api/compare/v0.2.0...v0.3.0) (2026-05-25)


### Features

* **charts:** add generic secret management and volume mounts ([b6213e7](https://github.com/bcit-tlu/qcon-api/commit/b6213e734a42a7d86334c230fe271c1f51c95faf))
* **charts:** conditional secret mounts and clean YAML separators ([bee52b9](https://github.com/bcit-tlu/qcon-api/commit/bee52b9d3f61d9ddbca56c3957d7a7cb2db17162))
* read POSTGRES_PORT from mounted secret instead of hardcoding ([0499080](https://github.com/bcit-tlu/qcon-api/commit/04990800de02606ebcfa7b22b4289ca1ad64d8ca))


### Bug Fixes

* **charts:** combine with + toJson guard for nil-safe affinity conditional ([f83c1a7](https://github.com/bcit-tlu/qcon-api/commit/f83c1a74cc5f3ca03dc79e1e0c9ccee752093cae))

## [0.2.0](https://github.com/bcit-tlu/qcon-api/compare/v0.1.0...v0.2.0) (2026-05-24)


### Features

* add application version to WebSocket server identification ([f93a709](https://github.com/bcit-tlu/qcon-api/commit/f93a709de35f0bc9077426706bc1e3e7f18f29b1))
* add custom PostgreSQL database backend with dynamic credential loading ([ee493c4](https://github.com/bcit-tlu/qcon-api/commit/ee493c47e673be17c1508be4fb5305b85ca6d52a))
* add secrets loader to support both file and environment variable sources ([214a2a2](https://github.com/bcit-tlu/qcon-api/commit/214a2a225ef6a2cd05af9e147a0f51f78342cddc))
* add server identification to WebSocket connections ([ba03c84](https://github.com/bcit-tlu/qcon-api/commit/ba03c8495f59da0fc780dcc8eac18d6b2e46b221))
* add subdirectory support to secret loading for better credentia… ([ab1eacb](https://github.com/bcit-tlu/qcon-api/commit/ab1eacb84be2241b00fabff99b78a0f829100780))
* add subdirectory support to secret loading for better credential organization ([7ec7ea0](https://github.com/bcit-tlu/qcon-api/commit/7ec7ea0a02020799d81e10ff82b48726ed76eedb))
* Merge pull request [#8](https://github.com/bcit-tlu/qcon-api/issues/8) from bcit-ltc/7-modify-secrets-directory ([ab1eacb](https://github.com/bcit-tlu/qcon-api/commit/ab1eacb84be2241b00fabff99b78a0f829100780))


### Bug Fixes

* add debug logging for secrets directory in docker entrypoint ([06e1cb6](https://github.com/bcit-tlu/qcon-api/commit/06e1cb6192a5e80b464cdf7d329cb6c423f01a74))
* add development fallback for dynamic database credentials and improve startup diagnostics ([29071cc](https://github.com/bcit-tlu/qcon-api/commit/29071ccd7e2cf0802f3c920f399e0db2db5382c4))
* add digest-empty guard to release-retag sign step ([5e30328](https://github.com/bcit-tlu/qcon-api/commit/5e303284b247ff41b205defa9ae484db7fe64867))
* add temporary pause in docker entrypoint for manual migration troubleshooting ([af724b1](https://github.com/bcit-tlu/qcon-api/commit/af724b152e18e8ad3873b2f431e3fca35baa7340))
* add x-release-please-version annotation to Chart.yaml version field ([8be32b0](https://github.com/bcit-tlu/qcon-api/commit/8be32b06757293a9357a58cef972363dc127d09d))
* address review feedback on probes and chart name ([ce4cdf3](https://github.com/bcit-tlu/qcon-api/commit/ce4cdf3401168c976e933a0d34ffb80b3051b576))
* adds permissions to workflow file ([30f4a15](https://github.com/bcit-tlu/qcon-api/commit/30f4a156e234f55c23b194717447265b74270848))
* adds secret generation to skaffold ([2d739c2](https://github.com/bcit-tlu/qcon-api/commit/2d739c2ddf201e805a1e6013469324bc917594d2))
* correct PostgreSQL host configuration in Docker environment ([edf019f](https://github.com/bcit-tlu/qcon-api/commit/edf019f1551eca21dd10c89b4cf33ce55116964a))
* corrects codeowners ([90841d5](https://github.com/bcit-tlu/qcon-api/commit/90841d52d2f2ebff32aad6edc04aa604f114afaf))
* disable text conversion and numbering fix steps in document processing ([955a163](https://github.com/bcit-tlu/qcon-api/commit/955a1635fa7344259466efbb28a28356667f639d))
* disable text conversion and numbering fix steps in document processing ([66d2124](https://github.com/bcit-tlu/qcon-api/commit/66d2124a0a8fab69f928e3d8a814b2daad4f6ea2))
* Merge pull request [#10](https://github.com/bcit-tlu/qcon-api/issues/10) from bcit-ltc/9-subprocesses-fails ([955a163](https://github.com/bcit-tlu/qcon-api/commit/955a1635fa7344259466efbb28a28356667f639d))
* Merge pull request [#13](https://github.com/bcit-tlu/qcon-api/issues/13) from bcit-ltc/12-update-to-django-62-lts ([f2867af](https://github.com/bcit-tlu/qcon-api/commit/f2867afa0135a0f3acc08806178ae299664d6a25))
* Merge pull request [#15](https://github.com/bcit-tlu/qcon-api/issues/15) from bcit-ltc/11-refactor-db-engine-to-support-dynamic-credential-rotation ([10adf32](https://github.com/bcit-tlu/qcon-api/commit/10adf32eeb940b1e61d095010552279726dbc3fa))
* Merge pull request [#6](https://github.com/bcit-tlu/qcon-api/issues/6) from bcit-ltc/5-refactor-to-match-names-with-helm-configs-vars ([7e8e8b6](https://github.com/bcit-tlu/qcon-api/commit/7e8e8b67f415357463832e20c9ff709e389519ef))
* move database migrations before debug sleep in docker entrypoint ([89f92df](https://github.com/bcit-tlu/qcon-api/commit/89f92df49e5f16fb562d379ce579398a56128361))
* Optimize image processing to handle large images ([1734bb2](https://github.com/bcit-tlu/qcon-api/commit/1734bb234fc04b57b5aecaac21d68c8fc5666116))
* Optimize image processing to handle large images ([c2248e6](https://github.com/bcit-tlu/qcon-api/commit/c2248e64eb050593e77b90b8a1cee8171b0a16e7))
* point release-please to VERSION file ([b40dea3](https://github.com/bcit-tlu/qcon-api/commit/b40dea3d3a78b10fdba8852e2a85a769ab3a083c))
* preserve helm push error output on failure ([2d5c0a6](https://github.com/bcit-tlu/qcon-api/commit/2d5c0a6c2ebc1cc20653cd698397ac23a106143f))
* push to verify deployment ([6b9df29](https://github.com/bcit-tlu/qcon-api/commit/6b9df291ac2743d2830d1c9f55401489c1e6ee60))
* re-pushes updated chart ([a6b3443](https://github.com/bcit-tlu/qcon-api/commit/a6b34439a7e545c11c0cec61b206e3492a91bd5f))
* remove custom network configuration and upgrade Django to 5.2 ([f2867af](https://github.com/bcit-tlu/qcon-api/commit/f2867afa0135a0f3acc08806178ae299664d6a25))
* remove custom network configuration and upgrade Django to 5.2 ([54271be](https://github.com/bcit-tlu/qcon-api/commit/54271beb4fd2d09cf841f25f1d7627075bd94e39))
* remove elastic env vars ([a8434a9](https://github.com/bcit-tlu/qcon-api/commit/a8434a98a18593848e5d46ed50cee0f33d121443))
* remove temporary debug pause from docker entrypoint ([fc789e1](https://github.com/bcit-tlu/qcon-api/commit/fc789e1834d099d6e4c71162ab86badf6879e0cf))
* remove VERSION file, align with org release-please pattern ([811c8b0](https://github.com/bcit-tlu/qcon-api/commit/811c8b0f063af3afdb20dcc782f03a4f8364abe9))
* removes deployment config files ([898e5ee](https://github.com/bcit-tlu/qcon-api/commit/898e5eef7d7710ceab992234eae2fffb20dae38f))
* skip empty affinity block in rendered manifest ([2c6c2de](https://github.com/bcit-tlu/qcon-api/commit/2c6c2de024fd8093ccee3054240f0a2d704b4dff))
* test deployment ([064accd](https://github.com/bcit-tlu/qcon-api/commit/064accd27ad060af1cd5e81ba44043a6866c1c20))
* Update README.md ([43f8684](https://github.com/bcit-tlu/qcon-api/commit/43f8684f8d461b232277dc4c6d995b91ee46509e))
* Update README.md ([4f81512](https://github.com/bcit-tlu/qcon-api/commit/4f815127cf764336e9b70f77eabd8bb54800bd4e))
* updates app chart ([641c233](https://github.com/bcit-tlu/qcon-api/commit/641c2331b126c7965d35494fa942c8b9fe3ee595))
* updates README ([11529ca](https://github.com/bcit-tlu/qcon-api/commit/11529caccfa48a0e6445eb86a8a957e416f1f94f))
