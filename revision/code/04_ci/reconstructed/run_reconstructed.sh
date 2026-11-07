#!/bin/sh
# Recompute the reconstructed-panel 95% intervals (B=2000, seed=42).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
cp "$HERE/protocol.json" "$HERE/matrix.json" "$HERE/preflight.json" "$HERE/rng.mjs" "$HERE/reconstructed_bootstrap.mjs" "$WORK/"
(cd "$WORK" && node reconstructed_bootstrap.mjs "$WORK")
node -e '
const fs=require("fs");
const got=JSON.parse(fs.readFileSync(process.argv[1]+"/CI_results.json","utf8"));
const exp=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const byB=Object.fromEntries(exp.results.map(r=>[r.benchmark,r]));
let ok=true;
for(const r of got.results){
  const e=byB[r.benchmark];
  const same = e && Math.abs(r.point_computed-e.point)<1e-12 && Math.abs(r.lo-e.lo)<1e-12 && Math.abs(r.hi-e.hi)<1e-12;
  ok = ok && !!same;
  console.log("  "+r.benchmark+": point "+r.point_computed+" ["+r.lo+", "+r.hi+"] "+(same?"identical":"DIFFERS"));
}
console.log("reconstructed point estimates and intervals identical:", ok);
if(!ok) process.exit(1);
' "$WORK" "$HERE/expected/CI_results.json"
echo "note: the protocol file was path-sanitised, so its file hash differs from the archived hash; the reported numbers do not."
echo "workdir: $WORK"
