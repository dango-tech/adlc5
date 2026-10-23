# Consumer conventions

Display names preserve caller capitalization, strip only surrounding whitespace,
and preserve internal spaces. Existing item records must not be mutated.
`created` is an integer timestamp; larger values are newer. The project uses
Python's standard library. Independent checks live outside this writable repo.

Migration input is a JSON list of item records. Version two is
`{"schema_version": 2, "items": [...]}`. Preserve item data. Re-running a version
two migration is a no-op. Use atomic same-directory replacement and clean up on
failure; no promise of power-loss durability is required.

Delivery calls `send(payload, key)` at most three times on TimeoutError, propagates
other exceptions immediately, and remembers a key only after success. A successful
key is never sent again within the supplied delivered set. Duplicate delivery
returns None. This local contract is not a distributed exactly-once guarantee.
