from dateutil.parser import parse


def filter_by_dates(df, start_date, end_date):
    return df[(df['Date'] > start_date) & (df['Date'] < end_date)]


def filter_by_country(df, country_dropdown):
    if country_dropdown:
        return df[df['State'].isin(country_dropdown)]


def filter_df(df, start_date, end_date, country_dropdown):
    if country_dropdown:
        df = filter_by_country(df, country_dropdown)
    return filter_by_dates(df, start_date, end_date)


def sumurize_by_country(df):
    usefull_columns = ['Death', 'Confirmed']
    df = df.groupby(['Lat', 'Long', 'State']).apply(
        lambda x: x.max() - x.min())
    return df.loc[:, usefull_columns].reset_index()


def get_daily_case(df, tabs_type):
    daily_cases = df.set_index('Date')
    daily_cases = daily_cases[tabs_type].diff()
    return daily_cases.fillna(0)


def format_date(str_date, date_format):
    date = parse(str_date)
    return date.strftime(date_format)
