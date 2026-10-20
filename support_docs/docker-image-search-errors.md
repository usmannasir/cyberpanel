# Docker image-search error display

Image search now displays the backend's `error_message`, accepts a legacy string
`error`, and otherwise shows a useful fallback. Both HTTP success responses
containing an application error and rejected HTTP requests use the same handling.
Errors render as text, not HTML. Successful image results and spinner completion
are preserved. The Manage Images template uses a new asset version so browsers
fetch the corrected script after upgrade/static collection.

Validation:

- `node dockerManager/test_image_search_errors.js`: ten callback cases, including
  Docker unavailable, registry errors, malformed/empty responses, transport
  failure, escaped text, and successful search results. The old source fails with
  `undefined` instead of `Docker not installed`.
- `node dockerManager/test_tag_pagination.js`: existing pagination regression.
- Actual isolated CyberPanel 3.0.8 QA: authenticated browser, native Manage Images
  template rendered as a temporary same-origin fixture, real served Docker JS,
  and real `/docker/searchImage` endpoint. With Docker absent, the original UI
  displayed `undefined`; the candidate displayed `Docker not installed`.
- Candidate served/source asset hashes matched and the native template compiled.

The fixture exposes the native template because the ordinary Manage Images GET
correctly routes to Docker installation when Docker is absent. It does not bypass
authentication on the search endpoint. No Docker installation, image pull,
container creation, registry-success integration, or customer-server repair is
claimed. Successful-result handling is covered by the callback regression test.
