# Terminology-content boundary

This public analysis-data release is identifier-free. It does not redistribute terminology
identifiers, identifier-linked description records, terminology label tables, transitive-ancestor
maps, node-depth maps, caches or the original identifier-linked annotation items.

Figure 1 contains one worked example already disclosed in the manuscript, without terminology
identifiers or release-local row keys. It does not distribute the linked answer-key collection or a
terminology description table.

The per-item CSVs contain only release-local item IDs, human granularity strata and already-derived
numeric or categorical scoring fields. `data/ontology/FROZEN_MAP_HASHES.sha256` records verification
digests of the private frozen scoring objects without distributing those objects. A digest cannot be
used to reconstruct a map.

## Licensed-user utilities

The utilities under `code/` can query EBI OLS4 or score locally supplied identifier pairs. Anyone
using those utilities must obtain and comply with the applicable SNOMED CT Affiliate Licence and
national release centre requirements. Generated identifiers, labels, maps and caches must remain in
that user's authorized environment unless the user independently holds redistribution rights.

The private frozen maps were retrieved from the EBI OLS4 `snomed` endpoint in July 2026. This release
does not interpret an OLS metadata identifier as an official RF2 edition date and makes no claim that
a later live rebuild will be bit-identical. For the reported paper-level statistics, use the deposited
identifier-free per-item metrics and aggregate tables.

SNOMED CT licensing information: https://www.snomed.org/get-snomed
