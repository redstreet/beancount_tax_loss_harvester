#!/usr/bin/env python3
# Description: Beancount Tax Loss Harvester

from beancount import loader
from beancount.query import query

import argparse,argcomplete,argh
import pickle
from types import SimpleNamespace
import tabulate

# TODO:
# - print TLH pairs
# - analysis of TLH pairs: can't be present in both sell and buy columns!
# - print DO-NOT-BUY-UNTIL-WARNING list

entries = None
options_map = None
argsmap = {}
def init_entries(beancount_file, args):
    global entries
    global options_map
    global argsmap
    entries, _, options_map = loader.load_file(beancount_file)
    argsmap = SimpleNamespace(**args)

def query_recently_bought(ticker, wash_pattern, wash_pattern_exclude):

    wash_pattern_sql = ''
    wash_pattern_exclude_sql = ''
    if wash_pattern:
        wash_pattern_sql = 'AND account ~ "{}"'.format(wash_pattern)
    if wash_pattern_exclude:
        wash_pattern_exclude_sql = 'AND NOT STR(account) ~ "{}"'.format(wash_pattern_exclude)

    sql = '''
    SELECT date,LEAF(account),sum(number),cost(sum(position)),currency
      WHERE
        date >= DATE_ADD(TODAY(), -31)
        {wash_pattern_sql}
        {wash_pattern_exclude_sql}
        AND currency = "{ticker}"
      GROUP BY date,payee,description,LEAF(account),currency
      ORDER BY date DESC
      '''.format(**locals())
    rtypes, rrows = query.run_query(entries, options_map, sql, numberify=True)
    return rtypes, rrows

def tlh(beancount_file,
        accounts_pattern='',
        loss_threshold=10,
        wash_pattern = '',
        wash_pattern_exclude = '',
        ):
    '''Finds opportunities for tax loss harvesting in a beancount file'''
    global argsmap
    argsmap = locals()
    init_entries(beancount_file, argsmap)

    sql = """
    SELECT LEAF(account),
        units(sum(position)) as units,
        cost_number as cost,
        first(getprice(currency, cost_currency)) as price,
        cost(sum(position)) as book_value,
        value(sum(position)) as market_value,
        cost_date as acquisition_date
      WHERE account_sortkey(account) ~ "^[01]" AND
        account ~ "{accounts_pattern}"
      GROUP BY LEAF(account), cost_date, currency, cost_currency, cost_number, account_sortkey(account)
      ORDER BY account_sortkey(account), currency, cost_date
    """.format(**locals())
    rtypes, rrows = query.run_query(entries, options_map, sql, numberify=True)

    # Figure out the columns of interest
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

    # Find rows where market value is not none, and is lower than book value by a threshold
    # try:
    #     with open('.tlh.pickle', 'rb') as fh:
    #         to_sell, recently_bought = pickle.load(fh)
    # except:
    if True:
        # print("Couldn't load from pickle cache")
        to_sell = []
        recently_bought = {}
        for row in rrows:
            if row[mv_col] and row[mv_col] - row[bv_col] < -loss_threshold:
                loss = int(row[bv_col] - row[mv_col])
                for uc, ulabels in enumerate(rtypes):
                    if 'units' in ulabels[0] and row[uc]:
                        ticker = ulabels[0].replace('units ', '')[1:-1]
                        qty = row[uc]
                recent = recently_bought.get(ticker, None)
                if not recent:
                    recent = query_recently_bought(ticker, wash_pattern, wash_pattern_exclude)
                    recently_bought[ticker] = recent
                wash = '*' if len(recent[1]) else ''
                to_sell.append((row[0], qty, ticker, row[mv_col], row[-1], wash, loss))

        # with open('.tlh.pickle', 'wb') as fh:
        #     pickle.dump((to_sell, recently_bought), fh, protocol=pickle.HIGHEST_PROTOCOL)


    # Pretty print TLH recommendation table
    unique_txns = set(r[0] + r[2] for r in to_sell)
    total_txns = '{} ({} sets)'.format(len(to_sell), len(unique_txns))
    headers = ['Account', 'Qty', 'Ticker', 'Market', 'Purchased', 'W', 'Loss']
    total_loss = sum(i[-1] for i in to_sell)
    total_mv = sum(i[3] for i in to_sell)
    footer = [(total_txns, '0.0', '', total_mv, '', '', total_loss)]
    print(tabulate.tabulate(to_sell + footer, headers=headers))


    # Pretty print Wash sale table
    print()
    print('Wash sales: recent purchase (within 30 days):')
    washes = False
    for t in recently_bought:
        if len(recently_bought[t][1]):
            washes = True
            print(tabulate.tabulate(recently_bought[t][1]))
    if not washes:
        print("None found.")

    warning = '''Note:
    1) Do NOT repurchase tickers within 30 days to avoid a wash sale.
    2) Turn OFF dividend reinvestment for all these tickers across ALL accounts
    '''
    print()
    print(warning)



#-----------------------------------------------------------------------------
def main():
    parser = argh.ArghParser(description="Beancount Tax Loss Harvester")
    argh.set_default_command(parser, tlh)
    argh.completion.autocomplete(parser)
    parser.dispatch()

if __name__ == '__main__':
    main()
