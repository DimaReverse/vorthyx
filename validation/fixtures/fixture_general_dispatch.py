"""Independent branch, calls and tuple fixture for native recovery."""


def build(factory, left, right):
    obj = factory(left)
    return obj.first(), obj.second(right)


def choose(which, first, second, value):
    if which == 'first':
        source, result = first(value)
    elif which == 'second':
        source, result = second(value)
    else:
        return 'unknown'
    if result is None:
        return 'failed'
    return result


if __name__ == '__main__':
    print(choose('first', lambda value: ('x', value), None, 3))
