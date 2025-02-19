import pytest
import pandas as pd
from plbonds import (
    Maturity, RelativeDate, Date, Bond, 
    Rates, Period, RateNames, Profit
)
import functools


class TestMaturity:

    def test_raises_error_if_no_params(self):
        with pytest.raises(TypeError, match="One of parameters"):
            Maturity()

    def test_Maturity_has_parameters(self):
        # passed years only
        m = Maturity(years=1)
        assert hasattr(m, "years")
        assert m.years == 1

        # passed months only
        m = Maturity(months=3)
        assert hasattr(m, "months")
        assert m.months == 3

        # passed years and months
        m = Maturity(years=1, months=3)
        assert hasattr(m, "years")
        assert m.years == 1
        assert hasattr(m, "months")
        assert m.months == 3


class TestRelativeDate:

    def test_raises_error_if_no_params(self):
        with pytest.raises(TypeError, match="One of parameters"):
            RelativeDate()

    def test_subtracted_from_Date(self):
        assert Date(2025, 1) - RelativeDate(days=1) == Date(2024, 12, 31)
        assert Date(2025, 1) - RelativeDate(months=1) == Date(2024, 12, 1)

    def test_added_to_Date(self):
        assert Date(2024, 12, 31) + RelativeDate(days=1) == Date(2025, 1, 1)
        assert Date(2025, 1, 31) + RelativeDate(months=1) == Date(2025, 2, 28)
        assert Date(2025, 1, 31) + RelativeDate(months=1, days=2) == Date(2025, 3, 2)


class TestDate:

    def test_needs_only_year(self):
        assert Date(2025) == Date(2025, 1, 1)
        assert Date(2025, 1) == Date(2025, 1, 1)

    def test_end_of_month(self):
        assert Date(2025, 2, 3).end_of_month() == Date(2025, 2, 28)
        assert Date(2025, 12, 3).end_of_month() == Date(2025, 12, 31)

    def test_start_of_month(self):
        assert Date(2025, 2, 3).start_of_month() == Date(2025, 2, 1)

    def test_end_of_year(self):
        assert Date(2025, 2, 3).end_of_year() == Date(2025, 12, 31)

    def test_start_of_year(self):
        assert Date(2025, 2, 3).start_of_year() == Date(2025, 1, 1)

    def test__from_pd_timestamp(self):
        input_date = Date(2025, 1, 1)
        pd_date = pd.to_datetime(input_date)
        assert Date.from_pd_timestamp(pd_date) == input_date

    def test_number_of_days_in_year(self):
        assert Date(2025,1,1).number_of_days_in_year() == 365
        assert Date(2024,1,1).number_of_days_in_year() == 366

    @pytest.mark.skip(reason="not implemented")
    def test_division_by_maturity(self):
        out = (Date(2025, 1, 1) - Date(2023, 2, 28)) / Maturity(years=1)
        print(out)
        assert False


class TestRates:

    def test_init(self):  # do we need anything else here?
        r = Rates()
        assert hasattr(r, "data")

    def test__solve_date_args(self):
        r = Rates()
        start, end = r._solve_date_args(Date(2025, 1, 1), Date(2025, 12, 31))
        assert isinstance(start, Date)
        assert isinstance(end, Date)

    def test__solve_date_args_fails_when_missing_args_on_first_set(self):
        r = Rates()
        with pytest.raises(AssertionError, match="`start` should be passed when it is the first"):
            r._solve_date_args(
                start=None,
                end=Date(2025, 12, 31),
            )
        with pytest.raises(AssertionError, match="`end` should be passed when it is the first"):
            r._solve_date_args(start=Date(2025, 1, 1), end=None)

    def test__solve_date_args_missing_args_on_following_set(self):
        r = Rates()
        r._prep_dataframe(start=Date(2025, 1, 1), end=Date(2025, 12, 31))

    def test__get_monthly_periods(self):
        r = Rates()
        starts, ends = r._get_monthly_periods(Date(2025, 1), Date(2025, 12))
        assert len(starts) == 12 and len(ends) == 12
        assert pd.to_datetime(Date(2025, 12, 1)) in starts
        assert pd.to_datetime(Date(2025, 2, 1)) in starts
        assert pd.to_datetime(Date(2025, 12, 31)) in ends
        assert pd.to_datetime(Date(2025, 2, 28)) in ends
        starts, ends = r._get_monthly_periods(Date(2024, 10), Date(2025, 3))
        assert len(starts) == 6 and len(ends) == 6

    def test__get_yearly_periods(self):
        r = Rates()
        starts, ends = r._get_yearly_periods(Date(2025, 1), Date(2025, 12))
        assert pd.to_datetime(Date(2025, 1, 1)) in starts
        assert pd.to_datetime(Date(2025, 12, 31)) in ends
        assert len(starts) == 1 and len(ends) == 1
        starts, ends = r._get_yearly_periods(Date(2023, 1), Date(2025, 2))
        assert len(starts) == 3 and len(ends) == 3
        assert pd.to_datetime(Date(2023, 1, 1)) in starts
        assert pd.to_datetime(Date(2024, 1, 1)) in starts
        assert pd.to_datetime(Date(2025, 1, 1)) in starts
        assert pd.to_datetime(Date(2023, 12, 31)) in ends
        assert pd.to_datetime(Date(2024, 12, 31)) in ends
        assert pd.to_datetime(Date(2025, 12, 31)) in ends

    def test_set_rates_periodicaly_monthly(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=[5.0] * 12,
            period=Period.monthly,
            start=Date(2025, 1),
            end=Date(2025, 12),
        )
        print(f"min index: {r.data.index[0]}, max index: {r.data.index[-1]}")
        assert r.data.loc[pd.to_datetime(Date(2025, 6, 18)), "NBP:REF"] == 5.0
        assert pd.to_datetime(Date(2025, 12, 31)) in r.data.index
        assert r.data.loc[pd.to_datetime(Date(2025, 12, 31)), "NBP:REF"] == 5.0
        assert r.data.loc[pd.to_datetime(Date(2025, 1, 1)), "NBP:REF"] == 5.0

    def test_set_rates_periodicaly_monthly_various(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=[1.0, *[5.0] * 10, 2.0],
            period=Period.monthly,
            start=Date(2025, 1),
            end=Date(2025, 12),
        )
        print(f"min index: {r.data.index[0]}, max index: {r.data.index[-1]}")
        assert r.data.loc[pd.to_datetime(Date(2025, 6, 18)), "NBP:REF"] == 5.0
        assert r.data.loc[pd.to_datetime(Date(2025, 12, 31)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2025, 1, 1)), "NBP:REF"] == 1.0

    def test_set_rates_periodicaly_yearly(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=[1.0, 2.0],
            period=Period.yearly,
            start=Date(2024, 1),
            end=Date(2025, 12),
        )
        assert r.data.loc[pd.to_datetime(Date(2025, 6, 18)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2025, 12, 31)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2025, 1, 1)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2024, 12, 31)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 1, 1)), "NBP:REF"] == 1.0

    def test_set_rates_periodicaly_daily(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=1.5,
            period=Period.daily,
            start=Date(2024, 1, 1),
            end=Date(2025, 12, 31),
        )
        assert r.data.loc[pd.to_datetime(Date(2025, 6, 18)), "NBP:REF"] == 1.5
        assert r.data.loc[pd.to_datetime(Date(2025, 12, 31)), "NBP:REF"] == 1.5
        assert r.data.loc[pd.to_datetime(Date(2025, 1, 1)), "NBP:REF"] == 1.5
        assert r.data.loc[pd.to_datetime(Date(2024, 12, 31)), "NBP:REF"] == 1.5
        assert r.data.loc[pd.to_datetime(Date(2024, 1, 1)), "NBP:REF"] == 1.5

    def test_set_rates_periodicaly_daily_fails_when_values_not_single(self):
        r = Rates()
        with pytest.raises(AssertionError, match="it is assumed that value will be single number"):
            r.set_rates_periodicaly(
                name="NBP:REF",
                values=[1.5, 2.0],
                period=Period.daily,
                start=Date(2024, 1, 1),
                end=Date(2025, 12, 31),
            )

    def test_set_rates_continuously(self):
        r = Rates()
        r.set_rates_continuously(
            name="NBP:REF",
            values=[1.0, 2.0],
            dates=[Date(2024, 1, 1), Date(2024, 7, 1)],
        )
        assert r.data.loc[pd.to_datetime(Date(2024, 1, 1)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 6, 30)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 7, 1)), "NBP:REF"] == 2.0

    def test_set_rates_continuously_with_extending_to_past(self):
        r = Rates()
        r.set_rates_continuously(
            name="NBP:REF",
            values=[1.0, 2.0],
            dates=[Date(2024, 1, 1), Date(2024, 7, 1)],
            extended_range=(Date(2023, 12, 5),),
        )
        assert r.data.loc[pd.to_datetime(Date(2024, 1, 1)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 6, 30)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 7, 1)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2023, 12, 5)), "NBP:REF"] == 1.0

    def test_set_rates_continuously_with_extending_to_future(self):
        r = Rates()
        r.set_rates_continuously(
            name="NBP:REF",
            values=[1.0, 2.0],
            dates=[Date(2024, 1, 1), Date(2024, 7, 1)],
            extended_range=(None, Date(2024, 12, 31)),
        )
        assert r.data.loc[pd.to_datetime(Date(2024, 1, 1)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 6, 30)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 7, 1)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2024, 12, 31)), "NBP:REF"] == 2.0

    def test_set_rates_continuously_with_extending_both(self):
        r = Rates()
        r.set_rates_continuously(
            name="NBP:REF",
            values=[1.0, 2.0],
            dates=[Date(2024, 1, 1), Date(2024, 7, 1)],
            extended_range=(Date(2023, 12, 5), Date(2024, 12, 31)),
        )
        assert r.data.loc[pd.to_datetime(Date(2024, 1, 1)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 6, 30)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 7, 1)), "NBP:REF"] == 2.0
        assert r.data.loc[pd.to_datetime(Date(2023, 12, 5)), "NBP:REF"] == 1.0
        assert r.data.loc[pd.to_datetime(Date(2024, 12, 31)), "NBP:REF"] == 2.0

    def test_set_multiple_rates(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="GUS:CPI",
            values=[5.0] * 12,
            period=Period.monthly,
            start=Date(2025, 1),
            end=Date(2025, 12),
        )
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=4.5,
            period=Period.daily,
            start=Date(2024, 3),
            end=Date(2025, 6),
        )
        assert r.data.loc[pd.to_datetime(Date(2025, 12, 31)), "GUS:CPI"] == 5.0
        assert r.data.loc[pd.to_datetime(Date(2024, 5, 31)), "NBP:REF"] == 4.5

        with pytest.raises(AssertionError):
            assert r.data.loc[pd.to_datetime(Date(2025, 12, 31)), "NBP:REF"] == 4.5

    def test_extend_to_past(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=1.0,
            period=Period.daily,
            start=Date(2024, 1, 1),
            end=Date(2025, 12, 31),
        )

        assert pd.to_datetime(Date(2023, 5, 13)) not in r.data.index
        r.extend_rate_to_past(Date(2023, 5, 13), name="NBP:REF")
        assert r.data.loc[pd.to_datetime(Date(2023, 5, 13)), "NBP:REF"] == 1.0

    def test_extend_to_future(self):
        r = Rates()
        r.set_rates_periodicaly(
            name="NBP:REF",
            values=1.0,
            period=Period.daily,
            start=Date(2024, 1, 1),
            end=Date(2025, 12, 31),
        )

        assert pd.to_datetime(Date(2023, 5, 13)) not in r.data.index
        r.extend_rate_to_future(Date(2026, 5, 13), name="NBP:REF")
        assert r.data.loc[pd.to_datetime(Date(2026, 2, 28)), "NBP:REF"] == 1.0

    def test_get_rate_by_date_uses_default_method_on_invalid_rate_name(self):
        r = Rates()
        invalid_rate_name = "CUSTOM_NAME"
        r.set_rates_continuously(
            name=invalid_rate_name,
            values=[5.75],
            dates=[Date(2023, 10, 5)],
            extended_range=(None, Date(2024, 12, 31)),
        )
        assert r.get_rate_by_date(invalid_rate_name, Date(2024, 1, 1)) == 5.75

    def test_get_rate_by_date_raises_on_date_out_of_range(self):
        r = Rates()
        r.set_rates_continuously(
            name=RateNames.NBPREF,
            values=[5.75],
            dates=[Date(2023, 10, 5)],
            extended_range=(None, Date(2024, 12, 31)),
        )

        with pytest.raises(KeyError, match="Rate .* not available for date"):
            r.get_rate_by_date(RateNames.NBPREF, Date(2025, 2, 1))

    def test_get_rate_by_date_GUSCPI(self):
        r = Rates()
        r.set_rates_periodicaly(
            name=RateNames.GUSCPI,
            values=[3.7, 2.8, 2.0],
            period=Period.monthly,
            start=Date(2024, 1, 1),
            end=Date(2024, 3, 31),
        )
        assert r.get_rate_by_date(RateNames.GUSCPI, Date(2024, 3, 1)) == 3.7
        assert r.get_rate_by_date(RateNames.GUSCPI, Date(2024, 4, 1)) == 2.8
        assert r.get_rate_by_date(RateNames.GUSCPI, Date(2024, 5, 1)) == 2.0

    def test_get_rate_by_date_NBPREF(self):
        r = Rates()
        r.set_rates_continuously(
            name=RateNames.NBPREF,
            values=[6.75, 6.0, 5.75],
            dates=[Date(2022, 9, 8), Date(2023, 9, 7), Date(2023, 10, 5)],
            extended_range=(None, Date(2024, 12, 31)),
        )

        assert r.get_rate_by_date(RateNames.NBPREF, Date(2022, 12, 31)) == 6.75
        assert r.get_rate_by_date(RateNames.NBPREF, Date(2023, 9, 7)) == 6.75
        assert r.get_rate_by_date(RateNames.NBPREF, Date(2023, 9, 8)) == 6.0
        assert r.get_rate_by_date(RateNames.NBPREF, Date(2023, 10, 5)) == 6.0
        assert r.get_rate_by_date(RateNames.NBPREF, Date(2023, 10, 6)) == 5.75
        assert r.get_rate_by_date(RateNames.NBPREF, Date(2024, 2, 29)) == 5.75

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


class TestBond:

    @pytest.fixture
    def fix_Bond_factory(self, fix_Rates):
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

    class TestInit:

        def test_raises_error_if_missing_parameters(
            self,
        ):  # this is obsolete, there are more necessary arguments right now
            with pytest.raises(TypeError, match="missing"):
                Bond()

        def test__solve_till_date_raises_when_given_Date_is_less_than_buy_date(
            self,
            fix_Bond_factory,
        ):
            b = fix_Bond_factory(maturity=Maturity(years=1), buy_date=Date(2025, 1, 1))
            with pytest.raises(AssertionError, match="When using Date"):
                b._solve_till_date(Date(2024, 5, 24))

        def test_has_source_rate_property(self, fix_Bond_factory):
            b = fix_Bond_factory(source_rate_name=RateNames.GUSCPI)
            assert hasattr(b, "source_rate")
            assert b.source_rate == RateNames.GUSCPI

        def test_has_rates_property(self, fix_Bond_factory, fix_Rates):
            b = fix_Bond_factory(rates=fix_Rates)
            assert hasattr(b, "rates")
            assert b.rates == fix_Rates

        def test_has_premium_property(self, fix_Bond_factory):
            b = fix_Bond_factory(premium=1.5)
            assert hasattr(b, "premium")
            assert b.premium == 1.5

        def test_has_maturity_parameter(self, fix_Bond_factory):
            m = Maturity(months=3)
            b = fix_Bond_factory(maturity=m)
            assert hasattr(b, "_maturity")
            assert b._maturity == m

        def test_has_initial_rate_property(self, fix_Bond_factory):
            b = fix_Bond_factory(initial_rate=5.0)
            assert hasattr(b, "initial_rate")
            assert b.initial_rate == 5.0

        def test_has_maturity_date_property(self, fix_Bond_factory):
            bf = functools.partial(fix_Bond_factory, buy_date=Date(2025, 1, 1))
            b_m3 = bf(maturity=Maturity(months=3))
            assert b_m3.maturity_date == Date(2025, 4, 1)
            b_y1 = bf(maturity=Maturity(years=1))
            assert b_y1.maturity_date == Date(2026, 1, 1)
            b_y1m3 = bf(maturity=Maturity(years=1, months=3))
            assert b_y1m3.maturity_date == Date(2026, 4, 1)

    class TestMethods:

        def test__solve_till_date(self, fix_Bond_factory):
            b = fix_Bond_factory(maturity=Maturity(years=1), buy_date=Date(2025, 1, 1))
            assert b._solve_till_date(RelativeDate(years=1)) == Date(2026, 1, 1)
            assert b._solve_till_date(Date(2025, 6, 12)) == Date(2025, 6, 12)

        def test_interest_table_is_multiindex(self, fix_Bond_factory):
            b = fix_Bond_factory(maturity=Maturity(years=1), buy_date=Date(2023, 1, 1))
            b._setup_interest_table(Date(2025, 1, 1))
            assert isinstance(b.interest_table.index, pd.MultiIndex)
            assert b.interest_table.index.names == ["instance", "period", "date"]
            assert pd.to_datetime(Date(2025, 1, 1)) in b.interest_table.index.get_level_values("date")
            assert pd.to_datetime(Date(2023, 1, 1)) in b.interest_table.index.get_level_values("date")
            assert pd.to_datetime(Date(2024, 2, 29)) in b.interest_table.index.get_level_values("date")

        def test__set_rates_for_initial_period(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2025, 1, 1),
                period=Period.yearly,
                initial_rate=5.0,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=b.maturity_date)
            b._set_rates()
            period1 = b.interest_table.loc[(1, 1), :]
            assert period1.loc[pd.to_datetime(Date(2025, 1, 1)), "rate"] == b.initial_rate
            assert period1.loc[pd.to_datetime(Date(2025, 12, 31)), "rate"] == b.initial_rate

        def test__set_variable_rates_for_all_periods(self, fix_Bond_factory, fix_Rates):
            b = fix_Bond_factory(
                maturity=Maturity(years=2),
                buy_date=Date(2023, 1, 1),
                source_rate_name=RateNames.GUSCPI,
                rates=fix_Rates,
                period=Period.yearly,
                initial_rate=5.0,
                premium=1.0,
                constant_rate = False,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=b.maturity_date)
            b._set_rates()
            p1 = b.interest_table.loc[(1, 1), :]
            p2 = b.interest_table.loc[(1, 2), :]
            print("p1", p1)
            print("p2", p2)
            assert p1.loc[pd.to_datetime(Date(2023, 1, 1)), "rate"] == b.initial_rate
            assert p1.loc[pd.to_datetime(Date(2023, 12, 31)), "rate"] == b.initial_rate
            assert p2.loc[pd.to_datetime(Date(2024, 1, 1)), "rate"] == 6.6 + b.premium
            assert p2.loc[pd.to_datetime(Date(2024, 12, 31)), "rate"] == 6.6 + b.premium
            assert p2.loc[pd.to_datetime(Date(2025, 1, 1)), "rate"] == 6.6 + b.premium

        def test__set_rates_for_constant_rate(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2022, 1, 1),
                period=Period.yearly,
                initial_rate=5.0,
                premium = 0.0,
                constant_rate=True,
                source_rate_name = RateNames.NBPREF,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2025, 1, 1))
            b._set_rates()
            df = b.interest_table
            print(f'rate head {df.loc[(1,1), "rate"].head()}')
            assert all(df.loc[(1,1), "rate"] == b.initial_rate)
            new_rate = b.rates.get_rate_by_date(name=b.source_rate, date=Date(2023, 1, 1))
            print(f'new_rate_1: {new_rate}')
            assert all(df.loc[(2,1), "rate"] == new_rate)
            new_rate = b.rates.get_rate_by_date(name=b.source_rate, date=Date(2024, 1, 1))
            print(f'new_rate_2: {new_rate}')
            assert all(df.loc[(3,1), "rate"] == new_rate)

        def test__set_continuation_premium(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2023, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.yearly,
                continuation_premium=0.1,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2025, 2, 1))
            b._set_continuation_premium()
            df = b.interest_table
            assert df.loc[(1, 1, pd.to_datetime(Date(2024, 1, 1))), "continuation_premium"] == 0.0
            assert df.loc[(2, 1, pd.to_datetime(Date(2024, 1, 1))), "continuation_premium"] == 0.1
            assert df.loc[(3, 1, pd.to_datetime(Date(2025, 1, 1))), "continuation_premium"] == 0.1
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 12, 31))), "continuation_premium"] == 0.0
            assert df.loc[:, "continuation_premium"].sum() == 0.2

        def test__set_capital_first_period(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2023, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.monthly,
                continuation_premium=0.1,
                capitalization=True,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 12, 31))
            b._set_rates()
            g = b._set_capital()
            next(g)
            df = b.interest_table
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 1))), "capital"] == b.initial_capital
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 31))), "capital"] == b.initial_capital
            assert pd.isna(df.loc[(1, 12, pd.to_datetime(Date(2023, 12, 31))), "capital"])

        def test__set_interest_first_period(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2023, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.yearly,
                continuation_premium=0.1,
                capitalization=True,
                initial_rate=5.0,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2025, 2, 1))
            b._set_rates()
            cap_g = b._set_capital()
            int_g = b._set_interest()
            next(cap_g)
            next(int_g)
            daily_interest = round(5.0 / 100 / 365 * 100, 8)
            df = b.interest_table
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 1))), "interest"] == 0.0  # interest allocated to next day
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 6, 6))), "interest"] == daily_interest
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 12, 31))), "interest"] == daily_interest
            assert df.loc[(2, 1, pd.to_datetime(Date(2024, 1, 1))), "interest"] == 0.0  # already next instance

        def test__set_capital_second_period_with_capitalization(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=2),
                buy_date=Date(2022, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.yearly,
                continuation_premium=0.1,
                capitalization=True,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 2, 1))
            b._set_rates()
            cap_g = b._set_capital()
            int_g = b._set_interest()
            next(cap_g)
            next(int_g)  # first period
            next(cap_g)
            df = b.interest_table
            assert df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 1))), "capital"] == 100.0
            assert df.loc[(1, 2, pd.to_datetime(Date(2023, 1, 1))), "capital"] == 105.0
            assert df.loc[(1, 2, pd.to_datetime(Date(2023, 12, 31))), "capital"] == 105.0

        def test__calc_interest_and_capital(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2022, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.yearly,
                continuation_premium=0.1,
                initial_rate=5.0,
                capitalization=False,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 2, 1))
            b._set_rates()
            b._calc_interest_and_capital()
            df = b.interest_table
            assert not df["capital"].isnull().any()
            assert not df["interest"].isnull().any()
            assert (df["capital"] == 100.0).all()
            assert round(df.loc[(1, 1), "interest"].sum(), 6) == 5.0
            # assert df.loc[(1,1),'interest'].sum() == 5.0

            # assert df.loc[:, 'capital'].applymap(np.isreal).values.all()

        def test__set_cumulative_interest(self, fix_Bond_factory):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2022, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.yearly,
                continuation_premium=0.1,
                initial_rate=5.0,
                capitalization=False,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 2, 1))
            b._set_rates()
            b._calc_interest_and_capital()
            b._set_cumulative_interest()
            df = b.interest_table
            assert not df["sum_interest"].isnull().any()
            assert round(df.loc[(1, 1, pd.to_datetime(Date(2023, 1, 1))), "sum_interest"], 6) == 5.0

        def test__set_early_buyout_costs_without_marking_not_applicable(self, fix_Bond_factory):
            b = fix_Bond_factory(
                buy_date=Date(2022, 1, 1),
                maturity=Maturity(years=1),
                period=Period.yearly,
                early_buyout_cost=2.0,
                mark_early_buyout_not_applicable=False,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 12, 31))
            b._set_rates()
            b._calc_interest_and_capital()
            b._set_cumulative_interest()
            b._set_early_buyout_cost()
            df = b.interest_table
            assert df.loc[(1, 1, pd.to_datetime(Date(2022, 12, 2))), "early_buyout_cost"] == b.early_buyout_cost
            assert df.loc[(2, 1, pd.to_datetime(Date(2023, 12, 2))), "early_buyout_cost"] == b.early_buyout_cost
            assert df.loc[(3, 1, pd.to_datetime(Date(2024, 12, 2))), "early_buyout_cost"] == b.early_buyout_cost
            k = (1, 1, pd.to_datetime(Date(2022, 1, 3)))
            assert df.loc[k, "early_buyout_cost"] == df.loc[k, "sum_interest"]
            k = (2, 1, pd.to_datetime(Date(2023, 1, 3)))
            assert df.loc[k, "early_buyout_cost"] == df.loc[k, "sum_interest"]
            k = (3, 1, pd.to_datetime(Date(2024, 1, 3)))
            assert df.loc[k, "early_buyout_cost"] == df.loc[k, "sum_interest"]

        def test__set_early_buyout_costs_with_marking_not_applicable(self, fix_Bond_factory):
            b = fix_Bond_factory(
                buy_date=Date(2022, 1, 1),
                maturity=Maturity(years=1),
                period=Period.yearly,
                early_buyout_cost=2.0,
                mark_early_buyout_not_applicable=True,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 12, 31))
            b._set_rates()
            b._calc_interest_and_capital()
            b._set_cumulative_interest()
            b._set_early_buyout_cost()
            df = b.interest_table

            # check dates where full early_buyout_cost is applicable
            assert df.loc[(1, 1, pd.to_datetime(Date(2022, 12, 2))), "early_buyout_cost"] == b.early_buyout_cost
            assert df.loc[(2, 1, pd.to_datetime(Date(2023, 12, 2))), "early_buyout_cost"] == b.early_buyout_cost
            assert df.loc[(3, 1, pd.to_datetime(Date(2024, 12, 2))), "early_buyout_cost"] == b.early_buyout_cost

            # check dates where it is too late for early buyout
            rd = RelativeDate(days=19)  # -> 2023-12-13; here last day for early buyout is 2023-12-12
            k = (1, 1, pd.to_datetime(Date(2023, 1, 1) - rd))
            assert pd.isna(df.loc[k, "early_buyout_cost"])
            k = (2, 1, pd.to_datetime(Date(2024, 1, 1) - rd))
            assert pd.isna(df.loc[k, "early_buyout_cost"])
            k = (3, 1, pd.to_datetime(Date(2025, 1, 1) - rd))
            assert pd.isna(df.loc[k, "early_buyout_cost"])

            # check dates of last possible early buyout, where full early_buyout_cost is expected
            rd = RelativeDate(days=20)  # -> 2023-12-12; here last day for early buyout is 2023-12-12
            k = (1, 1, pd.to_datetime(Date(2023, 1, 1) - rd))
            assert df.loc[k, "early_buyout_cost"] == b.early_buyout_cost
            k = (2, 1, pd.to_datetime(Date(2024, 1, 1) - rd))
            assert df.loc[k, "early_buyout_cost"] == b.early_buyout_cost
            k = (3, 1, pd.to_datetime(Date(2025, 1, 1) - rd))
            assert df.loc[k, "early_buyout_cost"] == b.early_buyout_cost

            # check first date of possible early buyout, where sum_interest is expected
            rd = RelativeDate(days=7)  # 2023-01-08; here first day for early buyout is 2023-01-08
            k = (1, 1, pd.to_datetime(Date(2022, 1, 1) + rd))
            assert df.loc[k, "early_buyout_cost"] == df.loc[k, "sum_interest"]
            k = (2, 1, pd.to_datetime(Date(2023, 1, 1) + rd))
            assert df.loc[k, "early_buyout_cost"] == df.loc[k, "sum_interest"]
            k = (3, 1, pd.to_datetime(Date(2024, 1, 1) + rd))
            assert df.loc[k, "early_buyout_cost"] == df.loc[k, "sum_interest"]

            # check dates where it is too early for early buyout
            k = (1, 1, pd.to_datetime(Date(2022, 1, 1)))
            assert pd.isna(df.loc[k, "early_buyout_cost"])
            k = (2, 1, pd.to_datetime(Date(2023, 1, 1)))
            assert pd.isna(df.loc[k, "early_buyout_cost"])
            k = (3, 1, pd.to_datetime(Date(2024, 1, 1)))
            assert pd.isna(df.loc[k, "early_buyout_cost"])

        def test__calc_interest_and_capital_for_multiple_periods_and_instances_with_capitalization(
            self, fix_Bond_factory
        ):
            b = fix_Bond_factory(
                maturity=Maturity(years=1),
                buy_date=Date(2022, 1, 1),
                source_rate_name=RateNames.NBPREF,
                period=Period.monthly,
                continuation_premium=0.1,
                capitalization=True,
                initial_rate=6.0,
                premium=0.5,
            )
            b.interest_table_workflow.clear()  # we work manually
            b.get_interest_table(till_date=Date(2024, 12, 31))
            b._set_rates()
            b._calc_interest_and_capital()
            print(b.interest_table)

            df = b.interest_table
            # first periods
            k = (1, 1, pd.to_datetime(Date(2022, 1, 3)))
            assert df.loc[k, "rate"] == b.initial_rate
            assert df.loc[k, "capital"] == b.initial_capital
            temp_interest = b.initial_rate / 100 / 12 / 31 * b.initial_capital
            assert df.loc[k, "interest"] == round(temp_interest, 8)

            k = (2, 1, pd.to_datetime(Date(2023, 1, 3)))
            assert df.loc[k, "rate"] == 6.75 + b.premium
            assert df.loc[k, "capital"] == b.initial_capital
            temp_interest = (6.75 + b.premium) / 100 / 12 / 31 * b.initial_capital
            assert df.loc[k, "interest"] == round(temp_interest, 8)

            # last periods
            k = (1, 12, pd.to_datetime(Date(2022, 12, 3)))
            assert df.loc[k, "rate"] == 6.75 + b.premium
            prev_capital = df.loc[(1, 11, pd.to_datetime(Date(2022, 11, 30))), "capital"]
            prev_interest = df.loc[(1, 11), "interest"].sum()
            temp_capital = round(prev_capital + prev_interest, 2)
            assert df.loc[k, "capital"] == temp_capital
            temp_interest = (6.75 + b.premium) / 100 / 12 / 31 * temp_capital
            assert df.loc[k, "interest"] == round(temp_interest, 8)

            k = (2, 12, pd.to_datetime(Date(2023, 12, 15)))
            assert df.loc[k, "rate"] == 5.75 + b.premium
            prev_capital = df.loc[(2, 11, pd.to_datetime(Date(2023, 11, 30))), "capital"]
            prev_interest = df.loc[(2, 11), "interest"].sum()
            temp_capital = round(prev_capital + prev_interest, 2)
            assert df.loc[k, "capital"] == temp_capital
            # assert df.loc[k, "capital"] == b.initial_capital  # already next bond
            temp_interest = (5.75 + b.premium) / 100 / 12 / 31 * temp_capital
            print("TEST:\n", df.loc[k])
            assert df.loc[k, "interest"] == round(temp_interest, 8)

    def test_get_interest_table(self, fix_Bond_factory):
        b = fix_Bond_factory(
            maturity=Maturity(years=2),
            buy_date=Date(2020, 1, 1),
            source_rate_name=RateNames.GUSCPI,
            period=Period.yearly,
            continuation_premium=0.1,
            capitalization=True,
            initial_rate=6.0,
            premium=0.5,
            early_buyout_cost=2.0,
        )
        till_date = RelativeDate(years=4)
        it = b.get_interest_table(till_date=till_date)
        assert hasattr(b, "interest_table")
        assert isinstance(it, pd.DataFrame)
        df = b.interest_table

        assert pd.to_datetime(Date(2020, 1, 1)) in df.index.get_level_values("date")
        assert pd.to_datetime(Date(2020, 1, 1) + RelativeDate(years=4)) in df.index.get_level_values("date")

        # first days of 1st period, 1st instance,
        k = (1, 1, pd.to_datetime(Date(2020, 1, 1)))  # first day
        assert df.loc[k, "rate"] == b.initial_rate
        assert df.loc[k, "capital"] == b.initial_capital
        assert df.loc[k, "interest"] == 0.0
        assert df.loc[k, "sum_interest"] == 0.0
        assert df.loc[k, "early_buyout_cost"] == 0.0

        k = (1, 1, pd.to_datetime(Date(2020, 1, 2)))  # 2nd day
        assert df.loc[k, "rate"] == b.initial_rate
        assert df.loc[k, "capital"] == b.initial_capital
        temp_rate = round(b.initial_rate / 100 / 366 * b.initial_capital, 8)
        assert df.loc[k, "interest"] == temp_rate
        assert df.loc[k, "sum_interest"] == temp_rate
        assert df.loc[k, "early_buyout_cost"] == temp_rate

        # last day of 1st period end, 1st instance,
        k = (1, 1, pd.to_datetime(Date(2021, 1, 1)))
        assert df.loc[k, "rate"] == b.initial_rate
        assert df.loc[k, "capital"] == b.initial_capital
        temp_rate = round(b.initial_rate / 100 / 366 * b.initial_capital, 8)
        assert df.loc[k, "interest"] == temp_rate
        assert round(df.loc[k, "sum_interest"], 2) == b.initial_rate
        assert round(df.loc[k, "early_buyout_cost"], 2) == b.early_buyout_cost

        # first days of 2nd period, 1st instance,
        k = (1, 2, pd.to_datetime(Date(2021, 1, 1)))  # first day
        temp_rate = 3.0 + b.premium
        assert df.loc[k, "rate"] == temp_rate
        temp_capital = round(b.initial_capital + df.loc[(1, 1), "interest"].sum(), 2)
        assert df.loc[k, "capital"] == temp_capital
        assert df.loc[k, "interest"] == 0.0
        assert round(df.loc[k, "sum_interest"], 2) == b.initial_rate
        assert df.loc[k, "early_buyout_cost"] == b.early_buyout_cost

        k = (1, 2, pd.to_datetime(Date(2021, 1, 2)))  # 2nd day
        print("TEST\n", df.loc[(1, 2), :])
        assert df.loc[k, "rate"] == temp_rate
        assert df.loc[k, "capital"] == temp_capital
        temp_interest = round(temp_rate / 100 / 365 * temp_capital, 8)
        assert df.loc[k, "interest"] == temp_interest
        assert round(df.loc[k, "sum_interest"], 2) == round(temp_interest + df.loc[(1, 1), "interest"].sum(), 2)
        assert df.loc[k, "early_buyout_cost"] == b.early_buyout_cost

    def test_get_interest_table_extends_existing(self, fix_Bond_factory):
        b = fix_Bond_factory(
            maturity=Maturity(years=1),
            buy_date=Date(2020, 1, 1),
            source_rate_name=RateNames.GUSCPI,
            period=Period.yearly,
            continuation_premium=0.1,
            capitalization=True,
            initial_rate=6.0,
            premium=0.5,
            early_buyout_cost=2.0,
        )

        b.get_interest_table(till_date=RelativeDate(years=2))
        temp_dates = b.interest_table.index.get_level_values("date")
        assert pd.to_datetime(Date(2020, 1, 1)) in temp_dates
        assert pd.to_datetime(Date(2020, 1, 1) + RelativeDate(years=2)) in temp_dates

        b.get_interest_table(till_date=RelativeDate(years=4))
        temp_dates = b.interest_table.index.get_level_values("date")
        assert pd.to_datetime(Date(2020, 1, 1)) in temp_dates
        assert pd.to_datetime(Date(2020, 1, 1) + RelativeDate(years=4)) in temp_dates

@pytest.fixture
def fix_profit_interest_table_sample(fix_Rates):
    b = Bond( # resembles ROR0124
        maturity=Maturity(years=1),
        period=Period.monthly,
        buy_date=Date(2023, 1, 1),
        initial_rate=6.75,
        capitalization=False,
        early_buyout_cost=0.5,
        constant_rate=False,
        premium=0.0,
        source_rate_name=RateNames.NBPREF,
        continuation_premium=0.1,
        rates=fix_Rates,
        mark_early_buyout_not_applicable=True,
    )
    b.get_interest_table(till_date=Date(2025, 1, 1))
    return b.interest_table

def test_fix_profit_interest_table_sample(fix_profit_interest_table_sample):
    itdf = fix_profit_interest_table_sample
    assert isinstance(itdf, pd.DataFrame)
    assert len(itdf) > 0
    assert 'interest' in itdf.columns
    assert 'early_buyout_cost' in itdf.columns
    assert 'continuation_premium' in itdf.columns

def test_Profit_init(fix_profit_interest_table_sample):
    itdf = fix_profit_interest_table_sample
    p = Profit(itdf)
    assert hasattr(p, 'interest_table')
    assert isinstance(p.interest_table, pd.DataFrame)
    assert p.interest_table is not itdf # this should be copy

@pytest.fixture
def fix_Profit(fix_profit_interest_table_sample):
    return Profit(fix_profit_interest_table_sample)

def test_fix_Profit(fix_Profit):
    assert isinstance(fix_Profit, Profit)

def test_Profit_attributes(fix_Profit):
    assert hasattr(fix_Profit, 'workflow')
    assert hasattr(fix_Profit, 'interest_table')

def test_Profit__replace_early_buyout_cost_nan_with_zero(fix_Profit):
    nan_mask = pd.isna(fix_Profit.interest_table)
    print('nan_mask',nan_mask.any())
    assert nan_mask.any().any()
    fix_Profit._replace_early_buyout_cost_nan_with_zero()
    new_nan_mask = pd.isna(fix_Profit.interest_table)
    assert not new_nan_mask.any().any() 

def test_Profit__select_columns(fix_Profit):
    cols = ['interest',
           'early_buyout_cost',
           'continuation_premium']
    fix_Profit._select_columns()
    assert fix_Profit.interest_table.columns.tolist() == cols

def test_Profit__set_profits_table(fix_Profit):
    fix_Profit._replace_early_buyout_cost_nan_with_zero()
    fix_Profit._set_profits_table()
    pdf = fix_Profit.profits
    print('pdf',pdf)
    assert 'interest' in pdf.columns
    assert 'early_buyout_cost' in pdf.columns
    assert 'continuation_premium' in pdf.columns
    assert pdf['continuation_premium'].sum() > 0.0
    assert pdf['early_buyout_cost'].sum() > 0.0
    assert pdf['interest'].sum() > 0.0

# def test_Profit__correct_doubled_early_buyout_cost(fix_Profit):
#     fix_Profit._replace_early_buyout_cost_nan_with_zero()
#     fix_Profit._set_profits_table()
#     eb_cost = fix_Profit.profits['early_buyout_cost'].sum()
#     # fix_Profit._correct_doubled_early_buyout_cost()
#     assert fix_Profit.profits['early_buyout_cost'].sum() < eb_cost    

def test_Profit__set_cumulative_cols(fix_Profit):
    fix_Profit._replace_early_buyout_cost_nan_with_zero()
    fix_Profit._set_profits_table()
    fix_Profit._set_cumulative_cols()
    assert 'sum_interest' in fix_Profit.profits.columns
    assert 'sum_continuation_premium' in fix_Profit.profits.columns

def test_Profit__set_total(fix_Profit):
    fix_Profit._replace_early_buyout_cost_nan_with_zero()
    fix_Profit._set_profits_table()
    fix_Profit._set_cumulative_cols()
    # fix_Profit._correct_doubled_early_buyout_cost()
    fix_Profit._set_total()
    pdf = fix_Profit.profits
    assert 'total' in pdf.columns
    assert pdf['total'].sum() > 0.0

def test_Profit_calc_total(fix_Profit):
    p = fix_Profit.calc_total(Date(2025,1,1))
    # is datetime index only:
    assert isinstance(p.index[0],type(pd.to_datetime(Date(2023, 1, 1))))
    
    k = pd.to_datetime(Date(2023, 1, 1))
    assert p.loc[k, 'total'] == 0.0
    assert p.loc[k, 'sum_interest'] == 0.0
    
    k = pd.to_datetime(Date(2023, 2, 1))
    assert round(p.loc[k, 'sum_interest'],2) == 0.56
    assert round(p.loc[k, 'total'],2) == round(0.56 - 0.5,2)
    
    k = pd.to_datetime(Date(2023, 12, 1))
    assert round(p.loc[k, 'sum_interest'],2) == 6.04
    assert round(p.loc[k, 'total'],2) == round(6.04 - 0.5,2)

    k = pd.to_datetime(Date(2023, 12, 31))
    assert round(p.loc[k, 'sum_interest'],2) == round(p.loc[k, 'total'],2)

    k = pd.to_datetime(Date(2024, 1, 1))
    assert round(p.loc[k, 'sum_interest'],2) == 6.52
    assert round(p.loc[k, 'total'],2) == 6.62

    k = pd.to_datetime(Date(2024, 1, 2))
    assert round(p.loc[k, 'sum_interest'],2) == 6.54
    assert round(p.loc[k, 'total'],2) == 6.64