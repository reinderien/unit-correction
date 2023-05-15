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
import math
import random
import re
from bisect import bisect_left
from collections import defaultdict, OrderedDict
from typing import Iterator, Literal, NamedTuple


def lhs(**kwargs: int) -> dict[str, int]:
    return {unit: -exp for unit, exp in kwargs.items()}


def rhs(**kwargs: int) -> dict[str, int]:
    return kwargs


CONVERSIONS = (
    # Coefficient, {unit: exponent, unit: exponent, ...})
    ( 1, {**lhs(volt=1), **rhs(ampère=1, ohm=1)}),
    ( 1, {**lhs(watt=1), **rhs(volt=1, ampère=1)}),
    ( 1, {**lhs(ampère=1), **rhs(coulomb=1, second=-1)}),
    ( 1, {**lhs(siemen=1), **rhs(ohm=-1)}),

    ( 1, {**lhs(hertz=1), **rhs(second=-1)}),
    (33.3564e-12, {**lhs(jiffy=1), **rhs(second=1)}),
    (60, {**lhs(minute=1), **rhs(second=1)}),
    (60, {**lhs(hour=1), **rhs(minute=1)}),
    (24, {**lhs(day=1), **rhs(hour=1)}),
    ( 7, {**lhs(week=1), **rhs(day=1)}),
)

SI_PREFIXES = OrderedDict({
    -30: 'quecto',
    -27: 'ronto',
    -24: 'yocto',
    -21: 'zepto',
    -18: 'atto',
    -15: 'femto',
    -12: 'pico',
     -9: 'nano',
     -6: 'micro',
     -3: 'milli',
     -2: 'centi',
     -1: 'deci',
      0: '',
      1: 'deca',
      2: 'hecto',
      3: 'kilo',
      6: 'mega',
      9: 'giga',
     12: 'tera',
     15: 'peta',
     18: 'exa',
     21: 'zetta',
     24: 'yotta',
     27: 'ronna',
     30: 'quetta',
})


def format_exp(unit: str, exp: int, natural_sign: Literal[1, -1]) -> str:
    if exp == natural_sign:
        return unit
    return f'{unit}^{exp * natural_sign}'


def get_plural(unit: str) -> str:
    if re.search(r'[sz]$', unit):
        return ''
    return 's'


def get_si(x: float, num_powers: list[int], den_powers: list[int]) -> tuple[
    int, str, str,
]:
    keys = tuple(SI_PREFIXES.keys())

    use_num = len(num_powers) == 1 and random.random() < 0.50
    use_den = len(den_powers) == 1 and random.random() < 0.50
    '''
    outer exponents always apply after the SI prefix
    i.e. it's (km)^2.
    adding 'k' (10**3) is as if you added 10**6, so divide this exponent by 2
    '''
    exp = math.floor(math.log10(abs(x)))
    exp_new = 0

    if use_num:
        num_min = max(min(keys), (exp - 6)/num_powers[0])
        num_max = min(max(keys), (exp + 6)/num_powers[0])
        num_choices = keys[
            bisect_left(keys, num_min):
            bisect_left(keys, num_max)
        ]
        num = random.choice(num_choices)
        num_pre = SI_PREFIXES[num]
        exp_new = exp - num*num_powers[0]
    else:
        num_pre, num, exp_new = '', 0, exp

    if use_den:
        den_min = max(min(keys), exp_new - 6)
        den_max = min(max(keys), exp_new + 6)
        den_choices = keys[
            bisect_left(keys, den_min):
            bisect_left(keys, den_max) + 1
        ]
        den = random.choice(den_choices)
        den_pre = SI_PREFIXES[den]
    else:
        den_pre, den = '', 0

    return den - num, num_pre, den_pre


class Quantity(NamedTuple):
    coeff: float
    units: dict[str, int]

    def unit_pairs(self, units: dict[str, int], sign: Literal[1, -1]) -> Iterator[tuple[str, int]]:
        for unit in units.keys() | self.units.keys():
            new_exp = units.get(unit, 0) + sign * self.units.get(unit, 0)
            if new_exp != 0:
                yield unit, new_exp

    def multiply(self, other: 'Quantity', target_unit: str) -> 'Quantity':
        sign = 1 if self.units[target_unit] < other.units[target_unit] else -1
        return Quantity(
            coeff=self.coeff**sign * other.coeff,
            units=dict(self.unit_pairs(other.units, sign)),
        )

    @property
    def reciprocal(self) -> 'Quantity':
        return Quantity(
            coeff=1/self.coeff,
            units={unit: -exp for unit, exp in self.units.items()},
        )

    def random_convert(self, max_rounds: int = 2) -> 'Quantity':
        output = self
        if random.random() < 0.20:
            output = output.reciprocal

        n_rounds = random.randint(1, max_rounds)
        for _ in range(n_rounds):
            reduce_options = tuple(output.units.keys())
            target_unit = random.choice(reduce_options)
            conv_index = CONV_BY_UNIT[target_unit]
            entry = conv_index.pick_random()
            output = entry.multiply(output, target_unit)
        return output

    def format_numerator(self) -> tuple[str, str, list[int]]:
        pairs = [
            (unit, exp)
            for unit, exp in self.units.items()
            if exp > 0
        ]

        if not pairs:
            return 'inverse', '', []

        *num_others, (num_last_unit, num_last_exp) = pairs
        num = ' '.join(format_exp(*pair, 1) for pair in num_others)
        num_sep = ' ' if num_others else ''

        plural = get_plural(num_last_unit)

        return (
            format_exp(f'{num}{num_sep}{num_last_unit}{plural}', num_last_exp, 1),
            'per ',
            [p[1] for p in pairs],
        )

    def format_denominator(self) -> tuple[str, list[int]]:
        pairs = [
            (unit, exp)
            for unit, exp in self.units.items()
            if exp < 0
        ]
        div_str = ' '.join(
            format_exp(unit, exp, -1) for unit, exp in pairs
        )
        return div_str, [p[1] for p in pairs]

    def to_string(self, maybe_si: bool = False) -> str:
        num_units, division, num_powers = self.format_numerator()
        den, den_powers = self.format_denominator()
        if den and division != 'per ':
            den += get_plural(den)

        if maybe_si:
            exp_adj, prefix_num, prefix_den = get_si(self.coeff, num_powers, den_powers)
        else:
            si_num_exp, si_den_exp, prefix_num, prefix_den = 0, 0, '', ''

        coeff = self.coeff * 10**exp_adj
        coeff_num = f'{coeff:,} {prefix_num}{num_units}'

        if den:
            return f'{coeff_num} {division}{prefix_den}{den}'
        return coeff_num

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return self.to_string()


class ConvIndex:
    def __init__(self):
        self.conversions: list[Quantity] = []

    def add(self, coeff: float, units: dict[str, int]):
        self.conversions.append(Quantity(coeff, units))

    def pick_random(self) -> Quantity:
        return random.choice(self.conversions)

    @classmethod
    def index_all(cls) -> dict[str, 'ConvIndex']:
        by_unit = defaultdict(cls)

        for conv_pair in CONVERSIONS:
            coefficient, conversion = conv_pair
            for unit, exponent in conversion.items():
                by_unit[unit].add(*conv_pair)

        return by_unit

    def __str__(self) -> str:
        return ', '.join(str(c) for c in self.conversions)

    def __repr__(self) -> str:
        return str(self)


CONV_BY_UNIT = ConvIndex.index_all()


def demo() -> None:
    start = Quantity(2e3, {'volt': 1})
    # start = Quantity(1, {'jiffy': 1})
    results = {
        start.random_convert().to_string(maybe_si=True)
        for _ in range(100)
    }
    print('\n'.join(results))


if __name__ == '__main__':
    demo()
