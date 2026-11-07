#!/bin/sh
# Recompute the primary Mantel-Haenszel 95% interval (B=10000, seed=12345)
# from the fixed panel, the document mapping and the per-item scores.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
WORK=$(mktemp -d)
mkdir -p "$WORK/OUT" "$WORK/RAW/A_fixed_sample"
cp "$HERE/OUT/protocol.json" "$HERE/OUT/mapping_validation.json" "$WORK/OUT/"
cp "$HERE/inputs/panel_documents.csv" "$WORK/RAW/A_fixed_sample/item_documents.csv"
cp "$HERE/inputs/pooled_risk_ratio_record.json" "$WORK/RAW/A_fixed_sample/fixed_sample_pooled_risk_ratio_record.json"
cp "$HERE/inputs/scores.csv" "$WORK/RAW/A_fixed_sample/scores.csv"
node "$HERE/cluster_bootstrap.mjs" "$WORK/OUT" "$WORK/RAW"
node -e '
const fs=require("fs");
const got=JSON.parse(fs.readFileSync(process.argv[1]+"/bootstrap_result.json","utf8"));
const exp=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const ga=got.primary, ea=exp.primary;
const okPoint=ga.point===ea.point;
const okCI=JSON.stringify(ga.newCI)===JSON.stringify(ea.newCI);
const keys=Object.keys(exp.intervals);
const okAll=keys.every(k=>JSON.stringify(got.intervals[k])===JSON.stringify(exp.intervals[k]));
console.log("point estimate identical:", okPoint);
console.log("primary 95% CI identical:", okCI, JSON.stringify(ga.newCI));
console.log("all "+keys.length+" intervals identical:", okAll);
if(!(okPoint&&okCI&&okAll)) process.exit(1);
' "$WORK/OUT" "$HERE/expected/bootstrap_result.json"
echo "note: the protocol file was path-sanitised, so its file hash differs from the archived hash; the reported numbers do not."
echo "workdir: $WORK"
