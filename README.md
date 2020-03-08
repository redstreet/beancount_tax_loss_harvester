# beancount_tax_loss_harvester
Tax loss harvester for Beancount personal finance software

Reports the set of lots that can be tax loss harvested from your beancount input file.
Example:

```
$ ./tlh.py ~/accounts/accounts.beancount -a "Assets:MyInvestments"

Account              Qty  Ticker       Market  Purchased    W      Loss
---------------  -------  --------  ---------  -----------  ---  ------
HTrade-Main        32.22   YYY        1982.123  2019-11-22           41
HTrade-Main         1.313  YYY         893.23   2019-11-23         1142
HTrade-Main        40.4    APPLE       704.344  2019-11-20           83
HTrade-Main       159.504  BETAX      7615.4    2019-07-10   *      384
HTrade-Second      68.695  APPLE       526.55   2019-05-10           19
HTrade-Second      77.786  BETAX      4437.66   2019-08-15   *       28
6 (5 sets)         0                20596.97                       1697

Wash sales: recent purchase (within 30 days):
----------  ------------ ------- -------  -----
2020-01-25  HTrade-Third   75.39  100.00  BETAX
----------  -----------  ------- -------  -----
```

The example above shows that 1697 USD of losses can be harvested by selling the rows
listed. However, 100 USD of that would be considered a wash sale and will not be
allowable. It also shows the account and quantities of each commodity to sell total sale
proceeds (20596.97 USD) if all the recommended lots were sold.

### Features
- reports on possible wash sales (US) in the second table above
- optionally set a loss threshold. Useful to filter out minor TLH opportunities
- reports the total number of sale transactions needed
- optionally takes:
  - account patterns to search for wash-sale creating purchases
  - account patterns to exclude for wash-sale creating purchases (eg: tax deferred
    accounts)

TODO:
- show if a loss generated would be long term or short term
