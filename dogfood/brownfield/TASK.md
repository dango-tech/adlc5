Add batch stock reservations to the warehouse inventory utility using ADLC5.
Operators need to preview a batch of reservations, commit it, and keep the
nightly report working on current inventory files. Use three independently
verifiable stories for preview, committed updates, and reporting compatibility.

Expose `app.reserve_stock(path, requests, *, preview=False)`. Requests are a
mapping of SKU to positive integer units. Return a mapping of SKU to the
number of units actually reserved or proposed in preview. A malformed quantity
or unknown SKU raises `ValueError` with no file change. For a valid request
that exceeds available stock, operations and customer support have proposed
different policies. Get an explicit decision from the stakeholder before
implementation.

Use repo evidence for existing behavior and inventory/reporting conventions.
Preserve stored data and keep the sample nightly report compatible. A failed
commit must keep the previous inventory readable and unchanged. A preview must
leave the inventory bytes unchanged. Publish committed updates using atomic same-directory
replacement. Let file I/O errors propagate to the caller.

Run the existing regression and the required inventory check in the README.
Preserve the check, its workflow, the existing report reader, and its sample
inventory. Follow the ADLC5 lifecycle and retain evidence for interruption,
resume, verification, and PR readiness.
