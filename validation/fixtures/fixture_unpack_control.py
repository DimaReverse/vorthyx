def unpacker(fetch, value):
    source, balance = fetch(value)
    if balance is None:
        return -1
    return balance


def unpack_direct(items):
    left, right = items
    return right


def unpack_guard(items):
    left, right = items
    if right is None:
        return -1
    return right


def manual_next(items):
    iterator = iter(items)
    first = next(iterator)
    second = next(iterator)
    next(iterator)
    return second


def manual_two_iterators(items):
    unused = iter(items)
    iterator = iter(items)
    first = next(iterator)
    second = next(iterator)
    next(iterator)
    return second
