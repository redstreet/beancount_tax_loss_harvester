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

def query_recently_bought(ticker, wash_pattern):
    wash_pattern_sql = ''
    if wash_pattern:
        wash_pattern_sql = 'AND account ~ "{}"'.format(wash_pattern)

    sql = '''
    SELECT date,LEAF(account),sum(number),cost(sum(position)),currency
      WHERE
        date >= DATE_ADD(TODAY(), -30)
        {wash_pattern_sql}
        AND currency = "{ticker}"
      GROUP BY date,payee,description,LEAF(account),currency
      ORDER BY date DESC
      '''.format(**locals())
    rtypes, rrows = query.run_query(entries, options_map, sql)
    return rtypes, rrows

def tlh(beancount_file,
        accounts_pattern='',
        loss_threshold=10,
        wash_pattern = '',
        ):
    '''Finds opportunities for tax loss harvesting in a beancount file'''
    global argsmap
    argsmap = locals()
    init_entries(beancount_file, argsmap)

    sql = """
    SELECT LEAF(account),
        units(sum(position)) as units,
        value(sum(position)) as market_value,
        cost(sum(position)) as book_value,
        cost_date as acquisition_date
      WHERE account_sortkey(account) ~ "^[01]" AND
        account ~ "{accounts_pattern}" AND
        date <= DATE_ADD(TODAY(), -30)
      GROUP BY LEAF(account), cost_date, currency, cost_currency, cost_number, account_sortkey(account)
      ORDER BY account_sortkey(account), currency, cost_date
    """.format(**locals())
    rtypes, rrows = query.run_query(entries, options_map, sql)

    def val(inv):
        return inv.get_only_position().units.number

    # Find rows where market value is not none, and is lower than book value by a threshold
    # try:
    #     with open('.tlh.pickle', 'rb') as fh:
    #         to_sell, recently_bought = pickle.load(fh)
    # except:
    if True:
        # print("Couldn't load from pickle cache")
        to_sell = []
        recently_bought = {}
        unique_txns = set()
        for row in rrows:
            if row.market_value.get_only_position() and \
             (val(row.market_value) - val(row.book_value) < -loss_threshold):
                loss = int(val(row.book_value) - val(row.market_value))
                ticker = row.units.get_only_position().units.currency

                recent = recently_bought.get(ticker, None)
                if not recent:
                    recent = query_recently_bought(ticker, wash_pattern)
                    recently_bought[ticker] = recent
                wash = '*' if len(recent[1]) else ''

                to_sell.append((row.leaf_account, row.units, row.market_value, row.acquisition_date, wash, loss))
                unique_txns.add(row.leaf_account + '*' + ticker)

        # with open('.tlh.pickle', 'wb') as fh:
        #     pickle.dump((to_sell, recently_bought), fh, protocol=pickle.HIGHEST_PROTOCOL)


    # Pretty print TLH recommendation table
    total_txns = '{} ({} sets)'.format(len(to_sell), len(unique_txns))
    headers = ['Account', 'Units', 'Market', 'Purchased', 'W', 'Loss']
    total_loss = sum(i[-1] for i in to_sell)
    total_mv = sum(i[2].get_only_position().units.number for i in to_sell)
    footer = [(total_txns, '0.0', total_mv, '', '', total_loss)]
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
