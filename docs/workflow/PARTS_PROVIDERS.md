# Parts, CAD and supplier connections

Use the [parts assistant](PARTS_TO_ORDER.md) for the implemented workflow. It
already resolves the 3D models paired with an assigned KiCad footprint, copies
portable assets with their original transforms, checks pad geometry and prepares
a reviewed BOM. Exact manufacturer-part-number CAD retrieval is not connected yet.
A supplier ordering handoff and a CAD download are separate integrations; neither
requires the other to be available.

The table records provider documentation checked on 2026-09-24. **Available** means
implemented here; **candidate** means an external capability, not a working
repository connection. Provider access and coverage can change.

| Source / endpoint | Useful result | Access and repository status |
| --- | --- | --- |
| [Official KiCad libraries](https://www.kicad.org/libraries/download/) | Footprints with authored 3D references and transforms; standard symbol libraries. | **Available, no account.** Uses installed assets first, then the project's exact release from the official library repositories. Matches an existing footprint ID, not an arbitrary MPN. |
| [DigiKey myLists third-party API](https://github.com/Digi-Key/KiCad-Push-to-DigiKey) | Sends BOM lines and returns a single-use review URL. | **Available, no API key.** After **Prepare order**, click **Send BOM to DigiKey**. Sign in at DigiKey to save the list; CSV remains available. This sends no CAD and places no order. |
| [DigiKey FastAdd](https://forum.digikey.com/t/digikey-fastadd-bulk-add-parts-into-a-digikey-cart-via-third-party-tooling-and-urls/61356/1) | Browser GET/POST to `/classic/ordering/fastadd.aspx` with DigiKey SKUs and quantities. | **Candidate, no developer account.** Adds to a cart, so it is a separate user action. Prefer myLists for reviewing manufacturer/MPN matches; FastAdd expects DigiKey part numbers. |
| [DigiKey Product Information v4](https://developer.digikey.com/products/product-information-v4/productsearch) and [Media](https://developer.digikey.com/products/product-information-v4/productsearch/media) | Part identity, pricing, stock and product-media links; product and `/products/v4/search/{productNumber}/media` lookups. | **Candidate, registered application and OAuth credentials.** Media links do not guarantee a complete KiCad symbol/footprint/3D bundle. This authentication requirement does not apply to the separate myLists handoff. |
| [EasyEDA/LCSC converter](https://github.com/uPesy/easyeda2kicad.py) | `easyeda2kicad --full --lcsc_id=C…` produces a symbol, footprint and available WRL/STEP models; supports KiCad 6+ and project-relative paths. | **Candidate, no credentials in the normal community adapter.** Pin a reviewed converter release. Its public EasyEDA web endpoints are not an established vendor REST contract, and this repository has not verified a live import. Requires an exact LCSC ID and package/pin review. |
| [Ultra Librarian API](https://api.ultralibrarian.com/api-docs/) | Exact manufacturer/MPN lookup through `/api/v1/parts/findpart`; export through `/api/v1/export` or `/api/v1/cip/download`. | **Candidate, provisioned API access and OAuth credentials.** Confirm entitlement, KiCad export format and model coverage during one-time connection setup. A website account alone does not establish API access. |
| [SnapMagic Search API](https://www.snapeda.com/get-api/) | Symbols, footprints and 3D models in supported formats, including KiCad. | **Candidate, developer access by request.** Free/premium API options exist. Its separate desktop/plugin documentation does not establish a working Mac/KiCad 10 integration or automatic 3D alignment. |
| [SamacSys / Component Search Engine](https://componentsearchengine.com/learn-more) and [Mouser ECAD](https://www.mouser.co.uk/en/electronic-cad-symbols-models/) | Exact-part CAD bundles and Library Loader import. | **Candidate, free user registration for downloads.** Useful bundle source; no supported public CAD REST contract or Mac/KiCad 10 loader verification is established here. |
| [Mouser Search API](https://www.mouser.com/en/api-search/) and [Nexar Supply API](https://nexar.com/api) | Manufacturer/MPN, distributor offers, stock and pricing. | **Candidates, API key or OAuth application setup.** Primarily sourcing metadata. Nexar advertises plan-dependent ECAD modules, but neither route establishes guaranteed complete KiCad/3D coverage. |
| [KiCad HTTP libraries](https://dev-docs.kicad.org/en/apis-and-binding/http-libraries/index.html) | A catalog in KiCad's symbol chooser: `categories.json`, `parts/category/{id}.json` and `parts/{id}.json`, including manufacturer/MPN fields and a footprint reference. | **Candidate, our own service and configured token.** A native front end for reviewed parts; it references installed libraries and does not download geometry. |

## Keep the common path short

The intended extension is one part-selection flow: enter an exact manufacturer/MPN
or supplier ID, resolve its identity, obtain a paired CAD bundle, preview pin/package
fit, then apply and prepare the order. Provider routing, asset registration and
portable model paths belong in the tool. Connection setup should happen once and
only for the provider being used.

Prefer official KiCad pairs for known standard footprints. An optional pinned
EasyEDA/LCSC adapter can cover exact LCSC parts without adding a provider login;
Ultra Librarian or SnapMagic can extend exact-MPN coverage after access is set up.
Those external CAD adapters remain proposed. Until one is implemented, bring a
reviewed bundle into the controlled library using the [library policy](LIBRARIES.md).
Do not substitute a same-looking package or declare a model aligned merely because
it downloaded successfully.

The implemented supplier handoff runs only when you click **Send BOM to DigiKey**
after **Prepare order**. It sends part numbers, quantities, manufacturer/MPN,
references and notes, and returns a DigiKey review link. It uses the request
contract in [DigiKey's own plugin](https://github.com/Digi-Key/KiCad-Push-to-DigiKey);
the [FastAdd guide](https://forum.digikey.com/t/digikey-fastadd-bulk-add-parts-into-a-digikey-cart-via-third-party-tooling-and-urls/61356/1)
also describes the separate no-authentication myLists handoff.
Failed or uncertain submissions are not retried automatically. Prepare a fresh
order before an explicit new attempt; a saved single-use URL cannot trigger a new
submission automatically. CSV upload remains the fallback. The handoff does not
confirm stock, price, packaging or a purchase. The existing readiness checks and
[BOM policy](BOM_POLICY.md) still apply.
