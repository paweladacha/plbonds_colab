# from _pytest._code import source
"""
This module contains tests for the exact examples in the documentation.

Data is compared to tables published at:
- [matured bonds](https://www.obligacjeskarbowe.pl/archiwum-produktow/)
- [not matured bonds](https://www.obligacjeskarbowe.pl/tabela-odsetkowa/)
"""

import pytest
import pandas as pd
from plbonds import Maturity, RelativeDate, Date, Bond, Rates, Period, RateNames
import functools
import numpy as np

# fmt: off
@pytest.fixture
def fix_Rates():
    # https://stat.gov.pl/obszary-tematyczne/ceny-handel/wskazniki-cen/wskazniki-cen-towarow-i-uslug-konsumpcyjnych-pot-inflacja-/miesieczne-wskazniki-cen-towarow-i-uslug-konsumpcyjnych-od-1982-roku/
    GUSCPI = [
        0.5,0.7,0.7,0.3,0.2,0.3,-0.2,-0.3,-0.3,-0.6,
        -0.6,-1.0,-1.4,-1.6,-1.5,-1.1,-0.9,-0.8,-0.7,-0.6,-0.8,-0.7,
        -0.6,-0.5,-0.9,-0.8,-0.9,-1.1,-0.9,-0.8,-0.9,-0.8,-0.5,-0.2,
        0,0.8,1.7,2.2,2.0,2.0,1.9,1.5,1.7,1.8,2.2,2.1,
        2.5,2.1,1.9,1.4,1.3,1.6,1.7,2.0,2.0,2.0,1.9,1.8,
        1.3,1.1,0.7,1.2,1.7,2.2,2.4,2.6,2.9,2.9,2.6,2.5,
        2.6,3.4,4.3,4.7,4.6,3.4,2.9,3.3,3.0,2.9,3.2,3.1,
        3.0,2.4,2.6,2.4,3.2,4.3,4.7,4.4,5.0,5.5,5.9,6.8,
        7.8,8.6,9.4,8.5,11.0,12.4,13.9,15.5,15.6,16.1,17.2,17.9,
        17.5,16.6,16.6,18.4,16.1,14.7,13.0,11.5,10.8,10.1,8.2,6.6,
        6.6,6.2,3.7,2.8,2.0,2.4,2.5,2.6,4.2,4.3,4.9,5.0,
        4.7,
        4.7,
    ]
    r = Rates()
    r.set_rates_periodicaly(
        RateNames.GUSCPI,
        values=GUSCPI,
        period=Period.monthly,
        start=Date(2014, 1),
        end=Date(2024, 12),
    )

    # CPI predicted NBP https://nbp.pl/projekcja-inflacji-i-pkb-listopad-2024/
    r.set_rates_continuously(
        name=RateNames.GUSCPI,
        values=[6.0, 5.5, 4.5, 3.5, 2.5],
        dates=[Date(2025, 1, 1), Date(2025, 4, 1), Date(2025, 7, 1), Date(2025, 10, 1), Date(2026, 1, 1)],
        extended_range=(None, Date(2026, 1, 31)),
    )

    r.set_rates_continuously(
        name=RateNames.NBPREF,
        values=[
            1.5,1.0,0.5,0.1,0.5,1.25,1.75,
            2.25,2.75,3.5,4.5,5.25,6.0,6.50,
            6.75,6.0,5.75,
        ],
        dates=[
            Date(2015, 3, 5),
            Date(2020, 3, 18),
            Date(2020, 4, 9),
            Date(2020, 5, 29),
            Date(2021, 10, 7),
            Date(2021, 11, 4),
            Date(2021, 12, 9),
            Date(2022, 1, 5),
            Date(2022, 2, 9),
            Date(2022, 3, 9),
            Date(2022, 4, 7),
            Date(2022, 5, 6),
            Date(2022, 6, 9),
            Date(2022, 7, 8),
            Date(2022, 9, 8),
            Date(2023, 9, 7),
            Date(2023, 10, 5),
        ],
        extended_range=(None, Date(2026, 1, 31)),
    )

    # NBP:REF predicted
    r.set_rates_continuously(
        name=RateNames.NBPREF,
        values=[5.25, 4.75, 4.25, 3.75, 3.25, 2.75],
        dates=[
            Date(2025, 7, 1),
            Date(2025, 10, 1),
            Date(2026, 1, 1),
            Date(2026, 4, 1),
            Date(2026, 7, 1),
            Date(2026, 10, 1),
        ],
        extended_range=(None, Date(2027, 1, 31)),
    )
    return r
# fmt: on

def test_fix_Rates(fix_Rates):
    assert fix_Rates.data.loc[pd.to_datetime(Date(2024, 1, 1))][RateNames.GUSCPI] == 3.7
    assert fix_Rates.data.loc[pd.to_datetime(Date(2024, 1, 1))][RateNames.NBPREF] == 5.75


@pytest.fixture
def fix_Bond_factory(fix_Rates):
    return functools.partial(
        Bond,
        maturity=Maturity(years=1),
        initial_rate=5.0,
        source_rate_name=RateNames.GUSCPI,
        premium=1.0,
        period=Period.yearly,
        buy_date=Date(2025, 1, 1),
        rates=fix_Rates,
        continuation_premium=0.1,
    )


def test_OTS0525(fix_Bond_factory):
    # this is excepiton - period should be yearly
    b = fix_Bond_factory(
        maturity=Maturity(months=3),
        period=Period.yearly,
        buy_date=Date(2025, 2, 1),
        initial_rate=3.00,
        premium=0.0,
        capitalization=False,
        constant_rate=True,
    )
    b.get_interest_table(till_date=Date(2025, 5, 1))
    df = b.interest_table
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2025, 5, 1))), "sum_interest"], 2) == 0.73

def test_OTS0525_multiinstance(fix_Bond_factory):
    # this is excepiton - period should be yearly
    b = fix_Bond_factory(
        maturity=Maturity(months=3),
        period=Period.yearly,
        buy_date=Date(2025, 2, 1),
        initial_rate=3.00,
        premium=0.0,
        capitalization=False,
        constant_rate=True,
    )
    b.get_interest_table(till_date=Date(2025, 12, 31))
    df = b.interest_table
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2025, 5, 1))), "sum_interest"], 2) == 0.73
    assert (31+28+31) <= len(df.loc[(1,1),:]) <= (30+31+31) + 1 # +1 for overlap
    assert (31+28+31) <= len(df.loc[(2,1),:]) <= (30+31+31) + 1 # +1 for overlap
    assert (31+28+31) <= len(df.loc[(3,1),:]) <= (30+31+31) + 1 # +1 for overlap
    assert (31+28+31) <= len(df.loc[(4,1),:]) <= (30+31+31) + 1 # +1 for overlap


def test_ROR0125(fix_Bond_factory):
    b = fix_Bond_factory(
        maturity=Maturity(years=1),
        period=Period.monthly,
        buy_date=Date(2024, 1, 1),
        initial_rate=6.15,
        capitalization=False,
        early_buyout_cost=0.5,
        constant_rate=False,
        premium=0.0,
        source_rate_name=RateNames.NBPREF,
    )
    b.get_interest_table(till_date=Date(2025, 1, 1))
    df = b.interest_table

    assert df.loc[(1, 1, pd.to_datetime(Date(2024, 1, 1))), "interest"] == 0.0
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2024, 1, 2))), "sum_interest"], 2) == 0.02
    assert df.loc[(1, 1, pd.to_datetime(Date(2024, 1, 31))), "rate"] == 6.15
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2024, 2, 1))), "sum_interest"], 2) == 0.51
    assert all(df.loc[(1, 12), "rate"] == 5.75)
    assert round(df.loc[(1, 12), "interest"].sum(), 2) == 0.48
    assert round(df.loc[(1, 2), "interest"].sum(), 2) == 0.48
    assert round(df.loc[(1, 2, pd.to_datetime(Date(2024, 3, 1))), "interest"], 8) == round(5.75 / 12 / 29, 8)


def test_ROR0125_extended_to_2nd_instance(fix_Bond_factory):
    b = fix_Bond_factory(
        maturity=Maturity(years=1),
        period=Period.monthly,
        buy_date=Date(2024, 1, 1),
        initial_rate=6.15,
        capitalization=False,
        early_buyout_cost=0.5,
        constant_rate=False,
        premium=0.0,
        source_rate_name=RateNames.NBPREF,
        mark_early_buyout_not_applicable=False,
    )
    b.get_interest_table(till_date=Date(2026, 1, 1))
    df = b.interest_table
    assert df.loc[(2, 1, pd.to_datetime(Date(2025, 1, 1))), "rate"] == 5.75
    assert df.loc[(2, 1, pd.to_datetime(Date(2025, 1, 1))), "continuation_premium"] == 0.1
    assert df.loc[:, "continuation_premium"].sum() == 0.1
    assert df.loc[(2, 1, pd.to_datetime(Date(2025, 1, 1))), "early_buyout_cost"] == 0.0
    assert round(df.loc[(2, slice(None), slice(None)), "interest"].sum(), 2) == 5.46  # uses predicted rates prev: 5.75


def test_DOR0125(fix_Bond_factory):
    b = fix_Bond_factory(
        maturity=Maturity(years=2),
        period=Period.monthly,
        buy_date=Date(2023, 1, 1),
        initial_rate=6.85,
        premium=0.1,
        capitalization=False,
        source_rate_name=RateNames.NBPREF,
        early_buyout_cost=0.7,
    )
    b.get_interest_table(till_date=Date(2025, 1, 1))
    df = b.interest_table
    assert df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 1))), "interest"] == 0.0
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 2))), "interest"], 8) == round(6.85 / 12 / 31, 8)
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2023, 2, 1))), "sum_interest"], 2) == 0.57

    assert round(df.loc[(1, 2, slice(None)), "interest"].sum(), 2) == 0.57
    assert round(df.loc[(1, 3, slice(None)), "interest"].sum(), 2) == 0.57
    assert round(df.loc[(1, 10, slice(None)), "interest"].sum(), 2) == 0.51
    assert round(df.loc[(1, 13, slice(None)), "interest"].sum(), 2) == 0.49
    assert round(df.loc[(1, 18, slice(None)), "interest"].sum(), 2) == 0.49
    assert round(df.loc[(1, 24, slice(None)), "interest"].sum(), 2) == 0.49

    assert df.loc[(1, 24, pd.to_datetime(Date(2024, 12, 1))), "early_buyout_cost"] == b.early_buyout_cost


def test_TOS0825(fix_Bond_factory):
    b = fix_Bond_factory(
        maturity=Maturity(years=3),
        buy_date=Date(2022, 8, 1),
        initial_rate=6.5,
        constant_rate=True,
        capitalization=True,
        period = Period.yearly,
    )

    b.get_interest_table(till_date=Date(2025, 1, 31))
    df = b.interest_table
    # period 1
    assert df.loc[(1, 1, pd.to_datetime(Date(2022, 8, 1))), "interest"] == 0.0
    assert len(df.loc[(1, 1), :]) == 366 # +1 for overlap
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2022, 8, 2))), "sum_interest"], 2) == 0.02
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2023, 7, 31))), "sum_interest"], 2) == 6.48
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2023, 8, 1))), "sum_interest"], 2) == 6.5
    assert round(df.loc[(1, 1, pd.to_datetime(Date(2023, 2, 28))), "sum_interest"], 2) == 3.76

    # period 2
    assert df.loc[(1, 2, pd.to_datetime(Date(2023, 8, 1))), "interest"] == 0.0
    assert df.loc[(1, 2, pd.to_datetime(Date(2023, 8, 2))), "capital"] == 106.5
    assert len(df.loc[(1, 2), :]) == 367 # +1 for overlap
    assert round(df.loc[(1, 2, pd.to_datetime(Date(2023, 8, 2))), "sum_interest"], 2) == 6.52
    sample = df.loc[(1, 2, pd.to_datetime(Date(2023, 8, 2))),:]
    print("check-period2",sample)
    assert round(df.loc[(1, 2, pd.to_datetime(Date(2024, 7, 31))), "sum_interest"], 2) == 13.40
    assert round(df.loc[(1, 2, pd.to_datetime(Date(2024, 8, 1))), "sum_interest"], 2) == 13.42
    assert round(df.loc[(1, 2, pd.to_datetime(Date(2024, 2, 29))), "sum_interest"], 2) == 10.51

    # period 3
    assert df.loc[(1, 3, pd.to_datetime(Date(2024, 8, 1))), "interest"] == 0.0
    assert round(df.loc[(1, 3, pd.to_datetime(Date(2024, 8, 2))), "sum_interest"], 2) == 13.44
    assert round(df.loc[(1, 3, pd.to_datetime(Date(2025, 7, 31))), "sum_interest"], 2) == 20.77
    assert round(df.loc[(1, 3, pd.to_datetime(Date(2025, 8, 1))), "sum_interest"], 2) == 20.79
    assert round(df.loc[(1, 3, pd.to_datetime(Date(2025, 2, 28))), "sum_interest"], 2) == 17.68


def test_COI1224(fix_Bond_factory):
    b = fix_Bond_factory(
        maturity=Maturity(years=4),
        period=Period.yearly,
        buy_date=Date(2020, 12, 1),
        initial_rate=1.3,
        premium=0.75,
        capitalization=False,
        source_rate_name=RateNames.GUSCPI,
    )
    b.get_interest_table(till_date=Date(2024, 12, 1))
    df = b.interest_table
    assert round(df.loc[(1, 1), "interest"].sum(), 2) == 1.3
    assert round(df.loc[(1, 2), "interest"].sum(), 2) == 7.55
    assert round(df.loc[(1, 3), "interest"].sum(), 2) == 18.65
    assert round(df.loc[(1, 4), "interest"].sum(), 2) == 7.35


def test_EDO0125(fix_Bond_factory):
    b = fix_Bond_factory(
        maturity=Maturity(years=10),
        period=Period.yearly,
        buy_date=Date(2015, 1, 1),
        initial_rate=3.0,
        premium=1.5,
        capitalization=True,
        source_rate_name=RateNames.GUSCPI,
    )
    b.get_interest_table(till_date=Date(2025, 1, 1))
    df = b.interest_table
    assert round(df.loc[(1, 1), "interest"].sum(), 2) == 3.0

    # below should be equal to 4.55 but because python and numpy uses 'half to even' rounding - we get 4.54
    assert round(df.loc[(1, 2), "interest"].sum() + 3.0, 2) == 4.54
    assert round(df.loc[(1, 2, pd.to_datetime(Date(2017, 1, 1))), "sum_interest"], 2) == 4.55

    assert round(df.loc[(1, 3), "interest"].sum() + 4.54, 2) == 6.11
    assert round(df.loc[(1, 3, pd.to_datetime(Date(2018, 1, 1))), "sum_interest"], 2) == 6.11

    assert round(df.loc[(1, 4), "interest"].sum() + 6.12, 2) == 10.36
    assert round(df.loc[(1, 4, pd.to_datetime(Date(2019, 1, 1))), "sum_interest"], 2) == 10.36

    assert round(df.loc[(1, 5), "interest"].sum() + 10.36, 2) == 13.45
    assert round(df.loc[(1, 5, pd.to_datetime(Date(2020, 1, 1))), "sum_interest"], 2) == 13.45

    assert round(df.loc[(1, 6), "interest"].sum() + 13.45, 2) == 18.1
    assert round(df.loc[(1, 6, pd.to_datetime(Date(2021, 1, 1))), "sum_interest"], 2) == 18.1

    assert round(df.loc[(1, 7), "interest"].sum() + 18.10, 2) == 23.41
    assert round(df.loc[(1, 7, pd.to_datetime(Date(2022, 1, 1))), "sum_interest"], 2) == 23.41

    assert round(df.loc[(1, 8), "interest"].sum() + 23.41, 2) == 34.89
    assert round(df.loc[(1, 8, pd.to_datetime(Date(2023, 1, 1))), "sum_interest"], 2) == 34.89

    assert round(df.loc[(1, 9), "interest"].sum() + 34.89, 2) == 60.52
    assert round(df.loc[(1, 9, pd.to_datetime(Date(2024, 1, 1))), "sum_interest"], 2) == 60.52

    assert round(df.loc[(1, 10), "interest"].sum() + 60.52, 2) == 73.52
    assert round(df.loc[(1, 10, pd.to_datetime(Date(2025, 1, 1))), "sum_interest"], 2) == 73.52
