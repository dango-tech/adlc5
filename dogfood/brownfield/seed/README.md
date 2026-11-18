# Warehouse inventory

This Python standard-library inventory utility is used by the warehouse's nightly
reporting job. The job reads a UTF-8 JSON array using
`reporting.read_stock(path)`. The sample in `fixtures/legacy-stock.json` is a
copy of the existing file format. Every row has a unique, case-sensitive
`sku`, a display `name`, a nonnegative integer `quantity`, and may carry
extra reporting fields. The report depends on the root array and original row
order. `app.save_items(path, items)` is the existing writer.

Run the existing regression and the required pull request check locally:

```sh
python3 -m unittest regression
python3 -m unittest regression reservation_check
```
