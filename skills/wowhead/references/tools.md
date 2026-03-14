# Tool-State Commands

## Best For

- stable inspection of Wowhead calculator and share-link state

## Start With

- talent calculator: `wowhead talent-calc <url-or-ref>`
- profession tree: `wowhead profession-tree <url-or-ref>`
- dressing room: `wowhead dressing-room <url-or-hash>`
- profiler: `wowhead profiler <url-or-list-ref>`

## Effective Use

- `talent-calc` extracts:
  - class slug
  - spec slug
  - build code
  - listed embedded builds when available
- `profession-tree` extracts:
  - profession slug
  - loadout code
- `dressing-room` normalizes the share hash and cited state URL
- `profiler` normalizes the `list=` reference and extracts obvious list/region/realm/name parts

## Boundary

- `dressing-room` and `profiler` are state inspectors, not full decoders
- do not claim they decode the underlying appearance payload or profile contents fully
- deeper reverse-engineering is intentionally out of scope unless a later product decision reopens it
