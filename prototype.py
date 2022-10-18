"""
Alright. I've tried this once about five years ago and I started from the wrong direction.

A unitful quantity is a scalar multiplied by the product of every unit in existence to the power of some integer, almost
all of them 0; also throw in a numerator or denominator SI coefficient:

    8 km/h = 8 * 10^3 / 10^0 * m^1 * h^-1 *  A^0 * V^0 ...

To be able to move from one equivalent to another, the system needs some equations expressed in a network; so

V = IR            Volts   Amps   Ohms    Furlongs
           before     1      0      0    -1        Volts per furlong
           after      0      1      1    -1        Amp ohms per furlong
           diff      -1      1      1

Going from one equation to the next involves adding to the existing equation's exponents a given vector of deltas.

          before      2      0      -1   -1        Volts squared per ohm furlong
        +            -1      1       1
          after       1      1       0   -1        Volt amps per furlong

       or before     -1                   1        Furlongs per volt
          -          -1      1       1
                      0     -1      -1    1        Furlongs per amp ohm


Unit-meddling is like the above, but with an outer coefficient:

                         metres    seconds   minutes
          before 1.17    1              -1         0    metres/second
                 *60   + 0               1        -1
          after = 70.2   1               0        -1    metres/minute

So the fundamental operations are:

- Reciprocate (or not), only once
- Dimension-meddle: choose any non-zero exponent, and pull it closer to zero with one of the conversions,
  "at least once"

coulombs = amp seconds
-1         1   1

amps = coulombs / sec
1      -1         1

amps   coulombs seconds
1      0        0
- above
=0     1        -1


"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterator, Literal


def lhs(**kwargs: int) -> dict[str, int]:
    return {unit: -exp for unit, exp in kwargs.items()}


def rhs(**kwargs: int) -> dict[str, int]:
    return kwargs


CONVERSIONS = (
    # Coefficient, {unit: exponent, unit: exponent, ...})
    ( 1, {**lhs(volt=1), **rhs(ampère=1, ohm=1)}),
    ( 1, {**lhs(watt=1), **rhs(volt=1, ampère=1)}),
    ( 1, {**lhs(ampère=1), **rhs(coulomb=1, second=-1)}),
    ( 1, {**lhs(hertz=1), **rhs(second=-1)}),
    (60, {**lhs(minute=1), **rhs(second=1)}),
    (60, {**lhs(hour=1), **rhs(minute=1)}),
    (24, {**lhs(day=1), **rhs(hour=1)}),
    ( 7, {**lhs(week=1), **rhs(day=1)}),
    ( 1, {**lhs(siemen=1), **rhs(ohm=-1)}),
)


def format_exp(unit: str, exp: int, natural_sign: Literal[1, -1]) -> str:
    if exp == natural_sign:
        return unit
    return f'{unit}^{exp}'


@dataclass
class Quantity:
    coeff: float
    units: dict[str, int]

    def unit_pairs(self, units: dict[str, int], sign: Literal[1, -1]) -> Iterator[tuple[str, int]]:
        for u in units.keys() | self.units.keys():
            new_exp = units.get(u, 0) + sign * self.units.get(u, 0)
            if new_exp != 0:
                yield u, new_exp

    def convert(self, target_unit: str, coeff: float, units: dict[str, int]) -> 'Quantity':
        sign = 1 if self.units[target_unit] < units[target_unit] else -1
        return Quantity(
            coeff=self.coeff**sign * coeff,
            units=dict(self.unit_pairs(units, sign)),
        )

    def random_convert(self) -> 'Quantity':
        reduce_options = tuple(self.units.keys())
        target_unit = random.choice(reduce_options)
        conv_index = CONV_BY_UNIT[target_unit]
        entry = conv_index.pick_from()
        return entry.convert(target_unit, self.coeff, self.units)

    def __str__(self) -> str:
        num_pairs = [
            (unit, exp)
            for unit, exp in self.units.items()
            if exp > 0
        ]

        if num_pairs:
            *num_others, (num_last_u, num_last_e) = num_pairs
            num = ' '.join(format_exp(*pair, 1) for pair in num_others)
            num_sep = ' ' if num_others else ''
            num_units = format_exp(f'{num}{num_sep}{num_last_u}s', num_last_e, 1)
            division = 'per '
        else:
            num_units = 'inverse'
            division = ''

        den = ' '.join(
            format_exp(unit, exp, -1)
            for unit, exp in self.units.items()
            if exp < 0
        )

        qnum = f'{self.coeff:,} {num_units}'
        if den:
            return f'{qnum} {division}{den}'
        return qnum


class ConvIndex:
    def __init__(self):
        self.conversions: list[Quantity] = []

    def add(self, coeff: float, units: dict[str, int]):
        self.conversions.append(Quantity(coeff, units))

    def pick_from(self) -> Quantity:
        return random.choice(self.conversions)

    @classmethod
    def index_all(cls) -> dict[str, 'ConvIndex']:
        by_unit = defaultdict(cls)

        for conv_pair in CONVERSIONS:
            coefficient, conversion = conv_pair
            for unit, exponent in conversion.items():
                by_unit[unit].add(*conv_pair)

        return by_unit


CONV_BY_UNIT = ConvIndex.index_all()
start = Quantity(2e3, {'volt': 1})
result = start.random_convert()
print(result)
