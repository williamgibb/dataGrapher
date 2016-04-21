import re


_float_regex = r'-?[\d]*[\.]?[\d]+'
FLOAT_REGEX = re.compile(_float_regex)

# This regex is designed to capture (possibly negative) integer/float
# values followed by a string value which represents a unit type.
_emission_regex = r'(?P<value>-?[\d]*[\.]?[\d]+)\s?(?P<unit>[a-z]{1,4}$)'
EMISSION_REGEX = re.compile(_emission_regex, re.IGNORECASE)

UNKNOWN_UNIT = 'unknownUnit'
