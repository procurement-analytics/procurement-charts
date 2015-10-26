#!/usr/bin/env python
# -*- coding: latin-1 -*-

import argparse
import textwrap
from datetime import datetime
import json
import numpy as np
import os
import pycurl
import pandas as pd
from pandas.io.json import json_normalize
from utils.utils import check_create_folder, exit, timer, list_files

from charts import settings, chartdata

import glob


DESCRIPTION = """A tool that processes OCDS record packages and generates
  JSON files that can be used by the Procurement Dashboards project.

  Commands:
    procurement-charts.py [sourceFolder]

    positional arguments:
      sourceFolder        Folder that contains JSON files with OCDS record 
                          packages

"""


def args_options():
  """ Generates an argument parser.
  :returns:
    Parser object
  """

  parser = argparse.ArgumentParser(prog='python procurement-charts.py ./data/ocds',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   description=textwrap.dedent(DESCRIPTION))

  parser.add_argument('source',
                      help='Provide the path to the folder containing the source data.')

  return parser


def slice_df(df, col, field):
  """
  Slice a dataframe

  :param df:
    Pandas dataframe
  :type df:
    Dataframe
  :param col:
    The column name to slice on
  :type col:
    String
  :param field:
    String to slice on
  :type field:
    String

  :returns:
    A sliced dataframe
  """
  try:
    sliced_df = df.groupby(col).get_group(field)
  except KeyError, e:
    print 'The column "%s" doesn\'t contain any "%s"' % (col, field)
    sliced_df = pd.DataFrame()

  return sliced_df


def flatten_object(o):
  out = {}

  def flatten(x, name=''):
    if type(x) is dict:
      for a in x:
        flatten(x[a], name + a + '_')
    elif type(x) is list:
      i = 0
      for a in x:
        flatten(a, name + str(i) + '_')
        i += 1
    else:
      out[str(name[:-1])] = x

  flatten(o)
  return out


def flatten_contracts(f, df):
  """
  Read an OCDS record package and flatten each contract so it can be added to
  a Pandas dataframe

  :param f:
    Path to a file containing a record package
  :type f:
    String
  :param df:
    The dataframe the flattened contracts will be added to
  :type df:
    Pandas DataFrame

  :returns:
    DataFrame with the data

  """
  with open(f, 'rb') as infile:
    package = json.load(infile)

    contracts = []

    # De-normalize each contract by merging data about the
    # tender, buyer and related award.
    for r in package['records']:
      for c in r['contracts']:
        final = {}
        final.update({'contract': c})
        final.update({'tender': r['tender']})
        final.update({'buyer': r['buyer']})
        # Every contract is related to an award. Merge the related award
        # object in the contract object
        for a in r['awards']:
          if a['id'] == c['awardID']:
            final.update({'award': a})
            break
        
        contracts.append(flatten_object(final))
    # Caveat:
    #   doesn't handle multiple suppliers well
 
    flattened_contracts = json_normalize(contracts)
    df = df.append(flattened_contracts,ignore_index=True)
    return df


def main(args):
  """
  Main function - launches the program.
  """

  if args:
    check_create_folder(settings.folder_charts)

    df = pd.DataFrame()

    # Read in the JSON files, flatten the contracts and add them to a DataFrame
    for f in list_files(args.source + '*'):
      df = flatten_contracts(f, df)

    # Improve
    df['contract_period_startDate'] = df['contract_period_startDate'].convert_objects(convert_dates='coerce')
    df['tender_publicationDate'] = df['tender_publicationDate'].convert_objects(convert_dates='coerce')
    df['tender_tenderPeriod_startDate'] = df['tender_tenderPeriod_startDate'].convert_objects(convert_dates='coerce')
    df['award_date'] = df['award_date'].convert_objects(convert_dates='coerce')


    # Cut every contract that's before a starting date
    start_date = datetime.strptime(settings.start_date_charts,'%Y-%m-%d')
    end_date = datetime.strptime(settings.end_date_charts,'%Y-%m-%d')
    df = df[(df[settings.main_date_contract] >= start_date) & (df[settings.main_date_contract] <= end_date)]

    # Generate the summary statistics, independent of comparison or slice
    overview_data = chartdata.generate_overview(df)

    with open(os.path.join(settings.folder_charts, 'general.json'), 'w') as outfile:
      json.dump(overview_data, outfile)

    for dimension in settings.dimensions:
      for comparison in settings.comparisons:

        # Each unique combination of dimension + comparison is a 'lense'
        lense_id = dimension + '--' + comparison['id']
        lense = { 
          'metadata': { 
            'id': lense_id
          },
          'charts': []
        }

        for chart in settings.charts:
          if chart['dimension'] == dimension:
            if chart['function']:
              chart['meta']['data'] = []
         
              previous_slice = False
              d = { }

              # Generate the chart data
              for sl in comparison['slices']:
                sliced_chart = { 'id': sl['id'], 'label': sl['label'] }
                
                # Prep the dataframe, slice it or serve it full
                if comparison['compare']:
                  sliced_df = slice_df(df, comparison['compare'], sl['field'])
                else:
                  sliced_df = df

                if not sliced_df.empty:
                  current_slice = chart['function'](sliced_df)

                  # Append the slice's data & meta-data 
                  sliced_chart['data'] = current_slice['data']
                  chart['meta']['data'].append(sliced_chart)
                  
                  # Update the domain based on the slice
                  for axis, func in chart['domain'].items():
                    if previous_slice:
                      d[axis] = func(d[axis], current_slice['domain'][axis])
                    else:
                      d[axis] = current_slice['domain'][axis]
                    
                  previous_slice = True


              # Add the domain to the chart
              for axis, func in chart['domain'].items():
                chart['meta'][axis]['domain'] = d[axis]
              
            # Append the chart data
            lense['charts'].append(chart['meta'])

        file_name = os.path.join(settings.folder_charts,lense_id + '.json')
        with open(file_name, 'w') as outfile:
          json.dump(lense, outfile)


def __main__():

    global parser
    parser = args_options()
    args = parser.parse_args()
    with timer():
        exit(*main(args))


if __name__ == "__main__":
  try:
    __main__()
  except (KeyboardInterrupt, pycurl.error):
    exit('Received Ctrl + C... Exiting! Bye.', 1)