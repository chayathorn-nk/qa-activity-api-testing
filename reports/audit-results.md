# Bruno audit results

45 requests; 149 checks; 128 passed; 21 failed.

Failures are preserved against the correct contract. Each scenario used a fresh API.

| Scenario | Request | HTTP | Failing check |
| --- | --- | --- | --- |
| 01-contract-and-auth | Missing order | 200 | HTTP status is 404 |
| 02-valid-order-and-price | Create valid order | 200 | BUG-01 Total equals menu price times quantity |
| 02-valid-order-and-price | Retrieve created order | 200 | BUG-01 Total equals menu price times quantity |
| 04-overstock | Reject excess quantity | 200 | HTTP status is 400 |
| 04-overstock | Reject excess quantity | 200 | Error body describes rejection |
| 04-overstock | Inventory after rejection | 200 | Rejected request does not change inventory |
| 04-overstock | Inventory after rejection | 200 | Inventory never becomes negative |
| 05-zero-quantity | Reject zero quantity | 200 | Invalid quantity is rejected with 400 or 422 |
| 05-zero-quantity | Reject zero quantity | 200 | Error body describes rejection |
| 06-negative-quantity | Reject negative quantity | 200 | Invalid quantity is rejected with 400 or 422 |
| 06-negative-quantity | Reject negative quantity | 200 | Error body describes rejection |
| 06-negative-quantity | Inventory after rejection | 200 | Rejected request does not change inventory |
| 07-missing-quantity | Reject missing quantity | 500 | Response is JSON |
| 07-missing-quantity | Reject missing quantity | 500 | Invalid quantity is rejected with 400 or 422 |
| 07-missing-quantity | Reject missing quantity | 500 | Error body describes rejection |
| 08-fractional-quantity | Reject fractional quantity | 200 | Invalid quantity is rejected with 400 or 422 |
| 08-fractional-quantity | Reject fractional quantity | 200 | Error body describes rejection |
| 08-fractional-quantity | Inventory after rejection | 200 | Rejected request does not change inventory |
| 09-string-quantity | Reject string quantity | 500 | Response is JSON |
| 09-string-quantity | Reject string quantity | 500 | Invalid quantity is rejected with 400 or 422 |
| 09-string-quantity | Reject string quantity | 500 | Error body describes rejection |
