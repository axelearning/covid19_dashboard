import pandas as pd


def filter_df(df, countries, time_range):
    df = filter_by_country(df, countries)
    return filter_by_dates(df, time_range)


def filter_by_country(df, countries):
    if countries:
        return df[df['State'].isin(countries)]
    else:
        return df


def filter_by_dates(df, time_range):
    if time_range != 0:
        last_day = df['Date'].max()
        time_range = last_day - pd.Timedelta(days=time_range)
        return df[df['Date'] > time_range]
    else:
        return df


def sumurize_by_country(df):
    usefull_columns = ['Death', 'Confirmed']
    df = df.groupby(['Lat', 'Long', 'State']).apply(
        lambda x: x.max() - x.min())
    return df.loc[:, usefull_columns].reset_index()


def get_daily_case(df):
    daily_cases = df.set_index(['Date', 'State'])
    daily_cases = daily_cases['Confirmed'].groupby('State').diff().fillna(0)
    daily_cases[daily_cases < 0] = 0
    return daily_cases
