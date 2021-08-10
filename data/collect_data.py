import pandas as pd

# Load the data
URL_CONFIRMED = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
URL_DEATH = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'


def reshape_df(df, state='Confirmed'):
    df.set_index(['Province/State', 'Country/Region',
                 'Lat', 'Long'], inplace=True)
    df = df.stack().reset_index(drop=False)
    df.rename(columns={'level_4': 'Date', 0: state}, inplace=True)
    return df


def collect_data():
    df_confirmed = pd.read_csv(URL_CONFIRMED)
    df_death = pd.read_csv(URL_DEATH)

    # Fill the NaN
    df_confirmed['Province/State'].fillna(
        df_confirmed['Country/Region'], inplace=True)
    df_death['Province/State'].fillna(df_death['Country/Region'], inplace=True)

    df_confirmed = df_confirmed.pipe(reshape_df, 'Confirmed')
    df_death = df_death.pipe(reshape_df, 'Death')

    df_covid19 = pd.merge(df_confirmed, df_death)
    df_covid19['Date'] = pd.to_datetime(df_covid19['Date'])
    df_covid19.drop(columns='Country/Region', inplace=True)
    df_covid19.rename(columns={'Province/State': 'State'}, inplace=True)

    df_covid19.to_csv("spreading_covid19.csv", index=False)


if __name__ == '__main__':
    collect_data()
