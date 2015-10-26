# Procurement Charts - chart data
# -*- coding: latin-1 -*-

# A set of functions to calculate the chart data for procurement
# dashboards

import pandas as pd
import numpy as np

import sys

import settings


def generate_overview(df):
  """
  Generate an overview of the whole dataset.

  :param df:
    Pandas dataframe
  :type df:
    Dataframe

  :returns:
    List labels and values
  :example:
    [
      {
        'label': 'Total procurement procedures',
        'value': 2105446
      },
      {
        'label': 'Total amount spent',
        'value': 210544616548924
      },
      ...
    ]
  """
  total_contracts = df['contract_id'].nunique()
  total_spent = (int(df['contract_value_amount'].sum()) / 1000000)


  overview = [
                {
                  'label': 'Total contracts',
                  'value': '{:,}'.format(total_contracts)
                },
                {
                  'label': 'Total amount contracted',
                  'value':  '$ ' + '{:,}'.format(total_spent) + ' mm (' + settings.desired_currency + ')'
                },
                {
                  'label': 'Contract start dates between',
                  'value': df[settings.main_date_contract].min().strftime("%d-%m-%Y") + ' and ' + df[settings.main_date_contract].max().strftime("%d-%m-%Y")
                },
                {
                  'label': 'Most active supplier',
                  'value': df['award_suppliers_0_name'].value_counts().index[0]
                },
                {
                  'label': 'Most active buyer',
                  'value': df['buyer_name'].value_counts().index[0]
                }
              ]

  return overview


def contracts_time(df):
  """
  Generate chart data for total amount of contracts per month
  Receives sliced data

  :param df:
    Pandas dataframe
  :type df:
    Dataframe

  :returns:
    Object with the domains and data
  :example:
    {
      'xdomain': ['2015-02-01', '2105-03-01', '2015-04-01'],
      'xdomain': [0, 100],
      'data': [ { 'date': '2015-02-01', 'value': 100 }, { 'date': '2015-03-01', 'value': 200 } ]
    }
  """

  chart_data = {
                'domain': {
                  'x': [],
                  'y': []
                },
                'data': []
                }

  # Prep the dataframe
  chart_df = df.loc[:,['contract_period_startDate','contract_id']].set_index('contract_period_startDate')
  chart_df = chart_df.groupby(pd.Grouper(level='contract_period_startDate',freq='1M')).contract_id.nunique()

  # Calculate the data
  # Improve this. Shouldn't have to use iterrows
  for ind, val in chart_df.iteritems():
    formatted_date = ind.strftime('%Y-%m-%d')
    if np.isnan(val):
      val = None
    else:
      val = int(val)

    chart_data['data'].append({'date': formatted_date, 'value': val})

  # Calculate the domains of this slice
  chart_data['domain']['x'] = [dt.strftime("%Y-%m-%d") for dt in chart_df.index.tolist()]
  chart_data['domain']['y'] = [0, int(chart_df.max())]

  return chart_data


def amount_time(df):
  """
  Generate chart data for total amount of money spent per month
  Receives sliced data

  :param df:
    Pandas dataframe
  :type df:
    Dataframe

  :returns:
    Object with the domains and data
  :example:
    {
      'xdomain': ['2015-02-01', '2105-03-01', '2015-04-01'],
      'xdomain': [0, 100],
      'data': [ { 'date': '2015-02-01', 'value': 100 }, { 'date': '2015-03-01', 'value': 200 } ]
    }
  """
  
  chart_data = {
                'domain': {
                  'x': [],
                  'y': []
                },
                'data': []
                }

  # Prep the dataframe
  chart_df = df.loc[:,['contract_period_startDate','contract_value_amount']].set_index('contract_period_startDate')
  xdf = chart_df.groupby(pd.Grouper(level='contract_period_startDate',freq='1M')).sum()

  # Calculate the data
  # Improve this. Shouldn't have to use iterrows
  for ind, row in xdf.iterrows():
    formatted_date = ind.strftime('%Y-%m-%d')
    if np.isnan(row[0]):
      val = None
    else:
      val = int(row[0])

    chart_data['data'].append({'date': formatted_date, 'value': val})

  # Calculate the domains of this slice
  chart_data['domain']['x'] = [dt.strftime("%Y-%m-%d") for dt in xdf.index.tolist()]
  chart_data['domain']['y'] = [0, int(xdf.max())]

  return chart_data


def average_timeline(df):
  """
  Generate chart data for the average timeline
  Receives sliced data

  :param df:
    Pandas dataframe
  :type df:
    Dataframe

  :returns:
    Object with the domains and data
  :example:
    {
      'data': [ 100, 200, 300 ]
    }
  """
  
  chart_data = {
                'data': []
                }

  # Prep the dataframe

  # To calculate a correct mean, we convert the timedelta to hours
  p1 = (df['tender_tenderPeriod_startDate'] - df['tender_publicationDate']).astype('timedelta64[h]')
  p2 = (df['award_date'] - df['tender_tenderPeriod_startDate']).astype('timedelta64[h]')
  p3 = (df['contract_period_startDate'] - df['award_date']).astype('timedelta64[h]')

  # Calculate the data
  chart_data['data'].append(int(p1.mean() / 24))
  chart_data['data'].append(int(p2.mean() / 24))
  chart_data['data'].append(int(p3.mean() / 24))

  return chart_data


def price_variation(df):
  """
  Generate chart data for a box and whisker plot about price variation
  Receives sliced data

  :param df:
    Pandas dataframe
  :type df:
    Dataframe

  :returns:
    (Dict) with the chart data
  :example:
    [ { 'min': '590', 'max': 8090, 'whisker1': 590, 'q1': 1090 } ]
  """
  
  chart_data = {
                'domain': {
                  'x': [],
                  'y': []
                },
                'data': []
                }

  # Prep the dataframe
  s = df.loc[:,['contract_value_amount']]

  # Calculate the data
  qr1 = int(s.quantile(0.25))
  median = int(s.median(numeric_only=True))
  qr3 = int(s.quantile(0.75))
  iqr = qr3 - qr1

  # Outlier = less than Q1 or greater than Q3 by more than 1.5 the IQR
  outlier_min = qr1 - (iqr * 1.5)
  outlier_max = qr3 + (iqr * 1.5)
  ol_series = s[(s > outlier_min) & (s < outlier_max)]

  boxplot = {}
  boxplot['min'] = int(s.min(numeric_only=True))
  boxplot['max'] = int(s.max(numeric_only=True))
  boxplot['whisker1'] = int(ol_series.min())
  boxplot['q1'] = qr1
  boxplot['median'] = median
  boxplot['q3'] = qr3
  boxplot['whisker2'] = int(ol_series.max())

  # Calculate the domains of this slice
  chart_data['data'] = boxplot
  chart_data['domain']['x'] = [int(ol_series.min()), int(ol_series.max())]
  chart_data['domain']['y'] = None

  return chart_data


def price_distribution(df):
  """
  

  :param df:
    Pandas dataframe, the full dataset or a slice of it
  :type df:
    Dataframe

  :returns:
    
  :example:
    
  """
  
  chart_data = {
                'domain': {
                  'x': [],
                  'y': []
                },
                'data': []
                }

  # Prep the dataframe
  # Cut off data above 95 percentile
  df_perc = df[(df['contract_value_amount'] <= df['contract_value_amount'].quantile(.95))]
  maxcontr = df_perc['contract_value_amount'].max()
  
  # Determine bins
  # Equally spaced bins
  bin_limits = np.arange(0, int(maxcontr) +1, int(maxcontr / 10))

  # Generate the chart data
  binned = pd.cut(df_perc['contract_value_amount'], bin_limits, labels=False)
  dist = pd.value_counts(binned).sort_index()
  chart_data['data'] = dist.tolist()

  # Calculate the domains of this slice
  # Generate the x-domain. Result is list with bin [[min, max],[min, max]...]
  bin_max = bin_limits[1:]
  chart_data['domain']['x'] = [list(a) for a in zip(bin_limits[0:-1],bin_max)]
  chart_data['domain']['y'] = [0, dist.max()]

  return chart_data


def top_contracts(df):
  """
  Generate a top five of biggest contracts by price

  :param df:
    Pandas dataframe, the full dataset or a slice of it
  :type df:
    Dataframe

  :returns:
    Object with the chart data
  :example:
    >>> { 'data': [ {'SIGLAS': 'ADECUP', 'DEPENDECIA': 'Administración'}, {'SIGLAS': 'ADECUP', 'DEPENDECIA': 'Administración'} ] }
  """

  chart_data = { 'data': [] }

  top_df = df.sort(columns='contract_value_amount', ascending=False)[:5]
  
  for ind, row in top_df.iterrows():
    top_contract = [
                      {
                        'value': row['buyer_abbreviation'],
                        'tooltip': row['buyer_name']
                      },
                      {
                        'value': row['award_suppliers_0_name']
                      },
                      {
                        'value': int(row['contract_value_amount']),
                        'format': 'amount|million'
                      }
                    ]

    chart_data['data'].append(top_contract)

  return chart_data
  

def relationships(df):
  """
  Generate chart data for a scatter plot that shows relationships between 
  suppliers and purchasing units

  :param df:
    Pandas dataframe, full dataset or a sliced bit
  :type df:
    Dataframe

  :returns:
    (Dict) with the chart data
  :example:
    
  """
  
  chart_data = {
                'domain': {
                  'x': [],
                  'y': [],
                  'r': []
                },
                'data': []
                }

  # Prep the dataframe
  df_buyer = df.groupby('buyer_abbreviation')
  
  # Calculate the data
  for name, group in df_buyer:
    sdata = {}
    #print str(group['buyer_name'].iloc[0])
    sdata['name'] = group['buyer_name'].iloc[0]
    sdata['suppliers'] = group['award_suppliers_0_name'].nunique()
    sdata['contracts'] = group['contract_id'].nunique()
    sdata['amount'] = int(group['contract_value_amount'].sum())
    chart_data['data'].append(sdata)
  

  # Calculate the domains
  minx = int(df_buyer['contract_value_amount'].sum().min())
  maxx = int(df_buyer['contract_value_amount'].sum().max())
  miny = df_buyer['award_suppliers_0_name'].nunique().min()
  maxy = df_buyer['award_suppliers_0_name'].nunique().max()
  minr = df_buyer['contract_id'].nunique().min()
  maxr = df_buyer['contract_id'].nunique().max()
  
  chart_data['domain']['x'] = [minx, maxx]
  chart_data['domain']['y'] = [miny, maxy]
  chart_data['domain']['r'] = [minr, maxr]

  return chart_data


def concentration_winning(df):
  """
  Generate chart data for a scatter plot that shows concentration of 
  winning by suppliers

  :param df:
    Pandas dataframe, full dataset or a sliced bit
  :type df:
    Dataframe

  :returns:
    (Dict) with the chart data
  :example:
    
  """
  
  chart_data = {
                'domain': {
                  'x': [],
                  'y': []
                },
                'data': []
                }

  # Prep the dataframe
  df_supplier = df.groupby('award_suppliers_0_name')
  
  # Calculate the data
  for name, group in df_supplier:
    sdata = {}
    sdata['name'] = str(group['award_suppliers_0_name'].iloc[0])
    sdata['contracts'] = group['contract_id'].nunique()
    sdata['amount'] = int(group['contract_value_amount'].sum())
    chart_data['data'].append(sdata)
  
  # Calculate the domains
  minx = int(df_supplier['contract_value_amount'].sum().min())
  maxx = int(df_supplier['contract_value_amount'].sum().max())
  miny = df_supplier['contract_id'].nunique().min()
  maxy = df_supplier['contract_id'].nunique().max()
  
  chart_data['domain']['x'] = [minx, maxx]
  chart_data['domain']['y'] = [miny, maxy]

  return chart_data