import datetime


def absolute_time(include_date=True, timestamp=datetime.datetime.now()):
    dt = timestamp
    if include_date == True:
        return datetime.datetime.strftime(dt, "%m/%d/%Y, %I:%M %p")
    if datetime.date(dt.year, dt.month, dt.day) == datetime.date(
        datetime.datetime.now().year,
        datetime.datetime.now().month,
        datetime.datetime.now().day,
    ):
        return datetime.datetime.strftime(dt, "%I:%M %p")
    else:
        return datetime.datetime.strftime(dt, "%m/%d/%Y, %I:%M %p")


def relative_time(date, short=False, seconds=True):
    if seconds == True:
        date = date * 1000
    now = datetime.datetime.now().timestamp() * 1000
    diff = now - date
    diff = int(diff)
    if diff < 1000:
        return "now"
    diff //= 1000
    if diff > 1 and diff < 60:
        return f"{diff} S" if short == True else f"{diff} seconds ago"
    elif diff == 1:
        return f"{diff} S" if short == True else f"{diff} second ago"
    diff //= 60
    if diff > 1 and diff < 60:
        return f"{diff} M" if short == True else f"{diff} minutes ago"
    elif diff == 1:
        return f"{diff} M" if short == True else f"{diff} minute ago"
    diff //= 60
    if diff > 1 and diff < 24:
        return f"{diff} H" if short == True else f"{diff} hours ago"
    elif diff == 1:
        return f"{diff} H" if short == True else f"{diff} hour ago"
    diff //= 24
    if diff > 1 and diff < 7:
        return f"{diff} D" if short == True else f"{diff} days ago"
    elif diff == 1:
        return f"{diff} D" if short == True else f"{diff} day ago"
    diff //= 7
    if diff > 1 and diff < 52:
        return f"{diff} W" if short == True else f"{diff} weeks ago"
    elif diff == 1:
        return f"{diff} W" if short == True else f"{diff} week ago"
    diff //= 52
    return f"{diff} Y" if short == True else f"{diff} years"
