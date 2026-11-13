"""Tuple construction with effects and exceptional elements."""


def triple(first, middle, last):
    return first(), middle(), last()


def mixed(value, produce):
    return value, produce(), value
