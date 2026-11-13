def invert(value):
    if value:
        return 'yes'
    return 'no'


def dispatch(which, first, second, value):
    if which == 1:
        result = first(value)
    elif which == 2:
        result = second(value)
    else:
        return None
    if result is None:
        return -1
    return result


def pair(left, right):
    return left(), right()


def identity_false(which, first, second, value):
    if which == 1:
        result = first(value)
    elif which == 2:
        result = second(value)
    else:
        return 'other'
    if result is not False:
        return result
    return 'was-false'
