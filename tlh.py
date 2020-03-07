#!/usr/bin/env python3
# Description: Beancount Tax Loss Harvester

import argparse,argcomplete,argh
from dateutil.parser import parse
import logging, sys

from beancount import loader
from beancount.core.number import ZERO
from beancount.query import query
import sys
import pickle
import decimal
from types import SimpleNamespace
import hashlib

entries = None
options_map = None
argsmap = {}
def init_entries(filename, args):
    global entries
    global options_map
    global argsmap
    entries, _, options_map = loader.load_file(filename)
    argsmap = SimpleNamespace(**args)

def tlh(filename, account_prefix, info=False, debug=False, loss_threshold=50):
    global argsmap
    argsmap = locals()
    init_entries(filename, argsmap)

    sql = """
    SELECT account,
        units(sum(position)) as units,
        cost_number as cost,
        first(getprice(currency, cost_currency)) as price,
        cost(sum(position)) as book_value,
        value(sum(position)) as market_value,
        cost_date as acquisition_date
      WHERE account_sortkey(account) ~ "^[01]" AND
        account ~ "{account_prefix}"
      GROUP BY account, cost_date, currency, cost_currency, cost_number, account_sortkey(account)
      ORDER BY account_sortkey(account), currency, cost_date
    """.format(**locals())
    rtypes, rrows = query.run_query(entries, options_map, sql, numberify=True)

    # Find rows where market value is not none, and is lower than book value by a threshold

    bv_col = 0
    mv_col = 0
    for c, label in enumerate(rtypes):
        if label[0] == 'book_value (USD)':
            bv_col = c
        if label[0] == 'market_value (USD)':
            mv_col = c

    if not bv_col or not mv_col:
        print("Error: bv_col/mv_col not set")
        import pdb; pdb.set_trace()

    row_fmt = '{:<55} {:>15} {} {:>5}'
    losses = 0
    num_transactions = 0
    for row in rrows:
        if row[mv_col] and row[mv_col] - row[bv_col] < -loss_threshold:
            loss = int(row[bv_col] - row[mv_col])
            for uc, ulabels in enumerate(rtypes):
                if 'units' in ulabels[0] and row[uc]:
                    amt = '{} {}'.format(row[uc], ulabels[0].replace('units ', ''))
            print(row_fmt.format(row[0], amt, row[-1], loss))
            losses += loss
            num_transactions += 1
    print(row_fmt.format('', '', 10*' ', 5*'-'))
    print(row_fmt.format(num_transactions, '', 10*' ', losses))

    todo = '''TODO:
    - check if any of these have been bought in the last 30 days
    - print TLH pairs
    - analysis of TLH pairs: can't be present in both sell and buy columns!
    - print #transactions: number of unique (account, ticker) pairs
    - print DO-NOT-BUY-UNTIL-WARNING list

    '''

    print()
    print(todo)


#-----------------------------------------------------------------------------
def main():
    parser = argh.ArghParser(description="Beancount Tax Computer.")
    argh.set_default_command(parser, tlh)
    argh.completion.autocomplete(parser)
    parser.dispatch()

if __name__ == '__main__':
    main()
