# Optional collection backend

The recommended path is local CSV download: each rater completes the private study app, downloads a
CSV, and transfers it to the study lead through an approved channel. Concatenate the files and run
`score_multi_annotator.py`.

`google_sheets_collector.gs` is included only as a minimal implementation example. A deployment set
to “Anyone” accepts unauthenticated POST requests and therefore must not be treated as a secure or
integrity-protected study database. Before real use, add authentication or signed requests, validate
the expected study and item IDs, reject duplicate/unexpected raters, close writes at the end of
collection, and follow institutional retention policy.

If the demonstration backend is still appropriate for a non-sensitive exercise:

1. Create a new Google Sheet and open **Extensions → Apps Script**.
2. Paste `google_sheets_collector.gs` and deploy it as a Web App.
3. Paste its `/exec` URL into `CONFIG.SHEETS_WEBAPP_URL` in a private copy of
   `annotation_app.html`.
4. Test with synthetic rows before distributing the app.
5. Export the sheet as CSV and close the deployment after collection.

The exported long-format columns are `rater_id,item_id,benchmark,annotator_label` plus optional
collection metadata. Remove names, notes and timestamps before public release.
