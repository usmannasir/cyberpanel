Chart.js 4.5.1, official UMD browser distribution, vendored without modification.

Upstream: https://github.com/chartjs/Chart.js/releases/tag/v4.5.1
Package: https://github.com/chartjs/Chart.js/releases/download/v4.5.1/chart.js-4.5.1.tgz
Package SHA256: d74ffdc9e4760d8960de3fd92bfa03397f01f85497c887d580bcf72641766aad
Member: package/dist/chart.umd.min.js
Asset SHA256: 48444a82d4edcb5bec0f1965faacdde18d9c17db3063d042abada2f705c9f54a
License: MIT, exact upstream LICENSE.md alongside the asset. The optional source map is not included.

The pinned local script removes the dashboard's dependency on an external CDN at page load. Keep the versioned path, original bundle header and license when updating. Validate the dashboard's actual line-chart configuration and refresh behavior before changing the version.
