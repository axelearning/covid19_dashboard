from dateutil.parser import parse


def prettify_number(number):
    if number:
        if number > 1e6-1:
            return f'{round(number/1e6,2)}M'
        elif number > 1e3-1:
            return f'{round(number/1e3,2)}k'
        else:
            return number
    else:
        return None


def format_date(str_date, date_format):
    date = parse(str_date)
    return date.strftime(date_format)
