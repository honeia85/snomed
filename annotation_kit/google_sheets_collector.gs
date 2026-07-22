/**
 * Granularity Annotation — Google Sheets collector (Apps Script Web App)
 * Receives POSTs from annotation_app.html and appends one row per label.
 * DEMONSTRATION ONLY: this endpoint has no authentication or input signature. Use the
 * download-only path or add institutional authentication before collecting real labels.
 *
 * SETUP (5 min, no coding):
 *  1. Create a new Google Sheet. Note its tab name (default "Sheet1").
 *  2. Extensions → Apps Script. Delete the stub, paste THIS file, Save.
 *  3. Deploy → New deployment → type "Web app".
 *       Execute as: Me   ·   Who has access: Anyone
 *     Click Deploy, authorize, and COPY the /exec Web app URL.
 *  4. Paste that URL into annotation_app.html → CONFIG.SHEETS_WEBAPP_URL, re-share the file.
 *  5. Every submission now appends rows here. Download as CSV when done.
 *
 * One row per (rater, item). Columns:
 *   received_at | study | rater_id | item_id | benchmark | annotator_label | annotator_notes | client_ts
 */
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    if (sh.getLastRow() === 0) {
      sh.appendRow(["received_at","study","rater_id","item_id","benchmark",
                    "annotator_label","annotator_notes","client_ts"]);
    }
    var body = JSON.parse(e.postData.contents);
    var now = new Date().toISOString();
    (body.rows || []).forEach(function(r){
      sh.appendRow([now, body.study||"", body.rater_id||"", r.item_id||"", r.benchmark||"",
                    r.label||"", r.note||"", r.ts||""]);
    });
    return ContentService.createTextOutput(JSON.stringify({ok:true, n:(body.rows||[]).length}))
                         .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error:String(err)}))
                         .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}
function doGet() {  // health check in a browser
  return ContentService.createTextOutput("Granularity collector is live. POST JSON to submit.");
}
