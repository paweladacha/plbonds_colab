import os
from typing import Union
import dateutil
from datetime import date
import pandas as pd

import logging

# Create a custom logger
logger = logging.getLogger(__name__)

# Configure the logger
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if os.getenv('DEBUG', 'False').lower() in ('true', '1', 't'):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


class Maturity(dateutil.relativedelta.relativedelta):

    def __init__(self, years=None, months=None, **kwargs):  # kwargs is needed for arithmetic operations
        kwargs = dict()
        for k, v in zip(("years", "months"), (years, months)):
            if v is not None:
                kwargs[k] = v
        if kwargs:
            super().__init__(**kwargs)
        else:
            raise TypeError("One of parameters should be passed: `years` | `months`")


class RelativeDate(dateutil.relativedelta.relativedelta):

    def __init__(self, years=None, months=None, days=None, **kwargs):  # kwargs is needed for arithmetic operations
        kwargs = dict()
        for k, v in zip(("years", "months", "days"), (years, months, days)):
            if v is not None:
                kwargs[k] = v
        if kwargs:
            super().__init__(**kwargs)
        else:
            raise TypeError("One of parameters should be passed: `years` | `months` | `days`")


class Date(date):

    def __new__(cls, year, month=None, day=None):
        if not month:
            month = 1
        if not day:
            day = 1
        return super().__new__(cls, year, month, day)

    def end_of_month(self):
        if self.month == 12:
            return self.__class__(self.year, 12, 31)
        else:
            return self.__class__(self.year, self.month + 1) - RelativeDate(days=1)

    def start_of_month(self):
        return self.__class__(self.year, self.month, day=1)

    def end_of_year(self):
        return self.__class__(self.year, month=12, day=31)

    def start_of_year(self):
        return self.__class__(self.year, month=1, day=1)

    def number_of_days_in_year(self):
        year = self.year
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 366  # Leap year has 366 days
        else:
            return 365  # Non-leap year has 365 days

    @classmethod
    def from_pd_timestamp(cls, pd_timestamp):
        return cls(pd_timestamp.year, pd_timestamp.month, pd_timestamp.day)


class Period:
    monthly = RelativeDate(months=1)
    yearly = RelativeDate(years=1)
    daily = RelativeDate(days=1)


class RateNames:
    GUSCPI = "GUS:CPI"
    NBPREF = "NBP:REF"


class Rates:

    def __init__(self, init_data: pd.DataFrame = None, methods_dict: dict = None, default_method = RateNames.NBPREF):

        if init_data is None:
            self.data = pd.DataFrame(index=pd.DatetimeIndex([]))
        else:
            self.data = init_data

        if methods_dict is None:
            self.methods_dict = self.RateGetMethods().get_methods_dict()
        elif isinstance(methods_dict, dict):
            self.methods_dict = methods_dict
        else:
            raise TypeError(f"methods_dict should be a dict, got {type(methods_dict)}")

        self.default_method = default_method

    def _prep_dataframe(self, start=None, end=None):
        assert (start is not None) or (end is not None), "None of parameters `start`, `end` was passed"

        if (start is None) or (len(self.data.index) and pd.to_datetime(start) > self.data.index[0]):
            start = self.data.index[0]

        if (end is None) or (len(self.data.index) and pd.to_datetime(end) < self.data.index[-1]):
            end = self.data.index[-1]

        self.data = self.data.reindex(pd.date_range(start=start, end=end, freq="D"))

    def _solve_date_args(self, start, end) -> (Date, Date):
        if start is None:
            assert len(self.data.index) > 0, "`start` should be passed when it is the first rate set."
            start = Date.from_pd_timestamp(self.data.index[0])

        if end is None:
            assert len(self.data.index) > 0, "`end` should be passed when it is the first rate set."
            end = Date.from_pd_timestamp(self.data.index[-1])

        return start, end

    def _get_monthly_periods(self, start, end):
        starts = pd.date_range(start=start.start_of_month(), end=end.start_of_month(), freq="MS").normalize()
        ends = pd.date_range(start.end_of_month(), end=end.end_of_month(), freq="ME").normalize()
        return starts, ends

    def _get_yearly_periods(self, start, end):
        starts = pd.date_range(start=start.start_of_year(), end=end.start_of_year(), freq="YS").normalize()
        ends = pd.date_range(start=start.end_of_year(), end=end.end_of_year(), freq="YE").normalize()
        return starts, ends

    def set_rates_periodicaly(self, name, values, period=Period.monthly, start: Date = None, end: Date = None):

        start, end = self._solve_date_args(start, end)
        assert start < end, f"End date should be latter than start date: {start} < {end}"

        if period is None or period == Period.daily:
            assert isinstance(
                values, (int, float)
            ), "When no `period` passed, or different than monthly | yearly, it is assumed that value will be single number"
            start, end = map(pd.to_datetime, (start, end))
            self._prep_dataframe(start, end)
            self.data.loc[start:end, name] = values
        else:
            if period == Period.monthly:
                start, end = start.start_of_month(), end.end_of_month()
                starts, ends = self._get_monthly_periods(start, end)
            elif period == Period.yearly:
                start, end = start.start_of_year(), end.end_of_year()
                starts, ends = self._get_yearly_periods(start, end)

            self._prep_dataframe(start, end)

            assert (
                len(values) == len(starts) == len(ends)
            ), f"Number of values and periods differ: len(values):{len(values)} == len(starts):{len(starts)} == len(ends):{len(ends)}"
            for v, s, e in zip(values, starts, ends):
                self.data.loc[s:e, name] = v

    def set_rates_continuously(self, name, values, dates, extended_range=None):
        if extended_range is not None:
            assert len(extended_range) in (
                1,
                2,
            ), f"`extended_range` should be a tuple of Dates of length 1 or 2: len(extended_range):{len(extended_range)}"

        self._prep_dataframe(min(dates), max(dates))

        dates = [*dates, self.data.index[-1]]
        for v, (s, e) in zip(values, zip(dates[:-1], dates[1:])):
            self.data.loc[pd.to_datetime(s) : pd.to_datetime(e), name] = v

        def extend_edge_rates(name, values, dates, extended_range):
            if (len(extended_range) == 1) or (extended_range[1] is None):
                self._prep_dataframe(start=extended_range[0])
                self.data.loc[pd.to_datetime(extended_range[0]) : pd.to_datetime(dates[0]), name] = values[0]
            elif extended_range[0] is None:
                self._prep_dataframe(end=extended_range[1])
                self.data.loc[pd.to_datetime(dates[-1]) : pd.to_datetime(extended_range[1]), name] = values[-1]
            else:
                self._prep_dataframe(start=extended_range[0], end=extended_range[1])
                self.data.loc[pd.to_datetime(extended_range[0]) : pd.to_datetime(dates[0]), name] = values[0]
                self.data.loc[pd.to_datetime(dates[-1]) : pd.to_datetime(extended_range[1]), name] = values[-1]

        if extended_range is not None:
            extend_edge_rates(name, values, dates, extended_range)

    def extend_rate_to_past(self, date, name):
        up_to_date = self.data.index[0]
        val = self.data.loc[up_to_date, name]
        start, end = self._solve_date_args(start=date, end=None)
        self._prep_dataframe(start=date, end=None)
        self.data.loc[pd.to_datetime(date) : up_to_date, name] = val

    def extend_rate_to_future(self, date, name):
        from_date = self.data.index[-1]
        val = self.data.loc[from_date, name]
        start, end = self._solve_date_args(start=None, end=date)
        self._prep_dataframe(start=None, end=date)
        self.data.loc[from_date : pd.to_datetime(date), name] = val

    class RateGetMethods:

        @staticmethod
        def GUSCPI(date: Date):
            return pd.to_datetime(date - RelativeDate(months=2))

        @staticmethod
        def NBPREF(date: Date):
            return pd.to_datetime(date - RelativeDate(days=1))

        def get_methods_dict(self):
            return {RateNames.GUSCPI: self.GUSCPI, RateNames.NBPREF: self.NBPREF}

    def get_rate_by_date(self, name, date: Date):
        md = self.methods_dict
        if name not in md:
            logger.warning(f"Rate method for {name} is not supported, using method for {self.default_method}")
            method = md[self.default_method]
            # raise KeyError(f"Rate name {name} not available (available: {md.keys()})")
        else:
            method = md[name]

        src_date = method(date)
        try:
            rate = self.data.loc[src_date, name]
            if rate < 0:
                rate = 0
            return rate

        except KeyError as e:
            raise KeyError(
                f"Rate {name} not available for date {src_date} (given date: {date}) (available dates: {self.data[name].first_valid_index()} - {self.data[name].last_valid_index()})"
            ) from e


class Bond:

    def __init__(
        self,
        maturity: Maturity,
        initial_rate: float,
        source_rate_name: RateNames,
        premium: float,
        period: Period = Period.yearly,
        buy_date: Date = None,
        capitalization: bool = False,
        continuation_premium: float = 0.1,
        rates: Rates = None,
        intial_capital=100.0,
        early_buyout_cost=0.0,
        mark_early_buyout_not_applicable=False,
        constant_rate=False,
    ):

        self.buy_date = Date.today() if buy_date is None else buy_date
        self._maturity = maturity
        self.interest_table = None
        self.period = period
        self.initial_rate = initial_rate
        self.source_rate = source_rate_name
        self.capitalization = capitalization
        self.initial_capital = intial_capital
        self.continuation_premium = continuation_premium
        self.premium = premium
        self.rates = rates
        self.early_buyout_cost = early_buyout_cost
        self.mark_early_buyout_not_applicable = mark_early_buyout_not_applicable
        self.constant_rate = constant_rate
        self.interest_table_workflow = [
            self._set_rates,
            self._calc_interest_and_capital,
            self._set_cumulative_interest,
            self._set_early_buyout_cost,
            self._set_continuation_premium,
        ]

    @property
    def maturity_date(self):
        return self.buy_date + self._maturity

    def _solve_till_date(self, till_date) -> Date:  # -> interface
        if isinstance(till_date, Date):
            assert (
                self.buy_date < till_date
            ), f"When using Date as till_date ({till_date}), date should be latter than buy_date ({self.buy_date})"
            end_date = till_date
        elif isinstance(till_date, RelativeDate):
            end_date = self.buy_date + till_date

        return end_date  # this should fail

    def _create_interest_table_index(self, end_date):
        # Below we calculate using `while` loop because we want to be precise and use calendar
        # Applying correct logic in `date` classes is overkill here.
        start_date = self.buy_date
        maturity = self._maturity
        period = self.period

        periods_per_maturity = 0
        cur_date = start_date
        while cur_date < (start_date + maturity):
            periods_per_maturity += 1
            cur_date += period

        instances_per_request_date_range = 0
        cur_date = start_date
        while cur_date < end_date:
            instances_per_request_date_range += 1
            cur_date += maturity
        
        logger.debug(
            f'Bond._create_interest_table_index\n'
            f'instances_per_request_date_range : {instances_per_request_date_range}\n'
            f'periods_per_maturity: {periods_per_maturity}'
            )
        
        index_frames = []
        for instance in range(1, instances_per_request_date_range + 1):
            for period_ind in range(1, periods_per_maturity + 1):
                period_start = start_date + (instance - 1) * maturity + (period_ind - 1) * period
                period_end = min([period_start + period, period_start+maturity])
                
                logger.debug(
                    f'Bond._create_interest_table_index\n'
                    f'instance:{instance}, period{period_ind}, '
                    f'period_start:{period_start}, period_end:{period_end} '
                    )

                date_range = pd.date_range(
                    period_start, period_end, freq="D"
                ).normalize()  # periods should overlap; .normalize to make sure hour is midnight - we do not need time
                df_dates = pd.DataFrame({"instance": instance, "period": period_ind, "date": date_range})
                index_frames.append(df_dates)

        return pd.MultiIndex.from_frame(pd.concat(index_frames, ignore_index=True))

    def _setup_interest_table(self, end_date):
        if self.interest_table is None:
            df_index = self._create_interest_table_index(end_date)
            self.interest_table = pd.DataFrame(index=df_index)
        elif self.interest_table.index.get_level_values("date")[-1] < pd.to_datetime(end_date):
            df_index = self._create_interest_table_index(end_date)
            self.interest_table = self.interest_table.reindex(df_index)

        return self.interest_table

    def _set_rates(self):
        itdf = self.interest_table
        if self.constant_rate:
            for instance, group in itdf.groupby(level="instance"):
                start_date = group.index[0][2]
                rate = self.rates.get_rate_by_date(name=self.source_rate, date=start_date)
                itdf.loc[(instance,), "rate"] = rate + self.premium
            
            itdf.loc[(1,), "rate"] = self.initial_rate
        else:
            for (instance, period), group in itdf.groupby(level=["instance", "period"]):
                start_date = group.index[0][2]
                rate = self.rates.get_rate_by_date(name=self.source_rate, date=start_date)
                itdf.loc[(instance, period), "rate"] = rate + self.premium

            itdf.loc[(1, 1), "rate"] = self.initial_rate

    def _set_continuation_premium(self):
        itdf = self.interest_table
        itdf.loc[:, "continuation_premium"] = 0.0
        for instance in itdf.index.get_level_values("instance").unique()[1:]:  # skip first instance
            first_date = itdf.xs(instance, level="instance").index[0][1]  # [0][1] because only `period/date` left
            itdf.loc[(instance, 1, first_date), "continuation_premium"] = self.continuation_premium

    def _capitalize(self, instance, period):
        return round(self.interest_table.loc[(instance, period), "interest"].sum(), 2)

    def _set_capital(self):
        itdf = self.interest_table
        instances = itdf.index.get_level_values("instance").unique()
        periods = itdf.index.get_level_values("period").unique()
        cur_capital = self.initial_capital
        logger.debug(f"Bond._set_capital: set_capital 1st: instances: {instances}")
        
        for instance in instances:
            for period in periods:
                logger.debug(f"Bond._set_capital: loop: instance{instance}; period {period}")
                
                if period == 1:
                    cur_capital = self.initial_capital
                elif self.capitalization:
                    cur_capital += self._capitalize(instance, period - 1)

                itdf.loc[(instance, period), "capital"] = round(cur_capital, 2)
                logger.debug(f"Bond._set_capital: loop: row: {(instance, period, cur_capital)}")
                
                yield

    def _set_interest(self):
        itdf = self.interest_table
        itdf.loc[:, "interest"] = 0.0
        for instance in itdf.index.get_level_values("instance").unique():
            instance_df = itdf.xs(instance, level="instance")
            periods_index = instance_df.index.get_level_values("period")
            for period in periods_index.unique():

                period_df = instance_df.loc[period]
                rates = period_df["rate"] / 100.0  # convert to percent
                capital = period_df["capital"]
                logger.debug(f"Bond._set_interest: instance: {instance}, period: {period}")

                if self.period == Period.yearly:
                    num_days = (Date.from_pd_timestamp(period_df.index[-1]) - RelativeDate(days=1)).number_of_days_in_year()
                    interest = (rates / num_days) * capital
                elif self.period == Period.monthly:
                    num_days = len(period_df) - 1  # -1 because of period overlap
                    interest = (rates / 12 / num_days) * capital
                else:
                    raise TypeError(f"Period {self.period} is not supported")

                interest.iloc[0] = 0.0  # because interest are allocated next day
                itdf.loc[(instance, period), "interest"] = interest.values.round(8)  # assigning np.array
                yield

    def _calc_interest_and_capital(self):
        for _ in zip(self._set_capital(), self._set_interest()):
            pass  # these are generators

    def _set_cumulative_interest(self):
        for instance in self.interest_table.index.get_level_values("instance").unique():
            self.interest_table.loc[(instance), "sum_interest"] = (
                self.interest_table.loc[(instance), "interest"].cumsum().values
            )

    def _set_early_buyout_cost(self):
        def create_target_index(instance, index):
            return pd.MultiIndex.from_tuples(map(lambda ind: (instance, *ind), index))

        itdf = self.interest_table
        for instance in itdf.index.get_level_values("instance").unique():
            k = (instance, slice(None), slice(None))
            itdf.loc[k, "early_buyout_cost"] = itdf.loc[k, "sum_interest"].combine(self.early_buyout_cost, min)

            if self.mark_early_buyout_not_applicable:
                instance_df = self.interest_table.xs(instance, level="instance")
                first_7_days_idx = create_target_index(instance, instance_df.index[:7])
                last_20_days_idx = create_target_index(instance, instance_df.index[-20:])

                itdf.loc[first_7_days_idx, "early_buyout_cost"] = pd.NA
                itdf.loc[last_20_days_idx, "early_buyout_cost"] = pd.NA

    def get_interest_table(self, till_date: Union[Date, RelativeDate] = None):

        end_date = self._solve_till_date(till_date)
        logger.debug(f"get_interest_table: end_date:{end_date}")
        
        self._setup_interest_table(end_date)
        for method in self.interest_table_workflow:
            method()

        return self.interest_table


class Profit:
    def __init__(self, interest_table: pd.DataFrame):
        self.interest_table = interest_table.copy()
        self.workflow = [
            self._select_columns,
            self._replace_early_buyout_cost_nan_with_zero,
            self._set_profits_table,
            self._set_cumulative_cols,
            # self._correct_doubled_early_buyout_cost,
            self._set_total,
            ]
        self.profits = pd.DataFrame(index=self.interest_table.index)

    def _select_columns(self):
        cols = ['interest',
               'early_buyout_cost',
               'continuation_premium']
        self.interest_table = self.interest_table[cols]
    
    def _replace_early_buyout_cost_nan_with_zero(self):
        nan_mask = pd.isna(self.interest_table['early_buyout_cost'])
        self.interest_table.loc[nan_mask, 'early_buyout_cost'] = 0.0

    def _set_profits_table(self):
        self.profits = self.interest_table.groupby(level=["date"]).max() # .max because for overlap dates only early_buyout_cost can repeat
    
    # def _correct_doubled_early_buyout_cost(self):
    #     max_eb_cost = self.interest_table['early_buyout_cost'].max()
    #     mask = self.profits['early_buyout_cost'] > max_eb_cost
    #     self.profits.loc[mask, 'early_buyout_cost'] = max_eb_cost

    def _set_cumulative_cols(self):
        self.profits.loc[:, 'sum_interest'] = self.profits['interest'].cumsum()
        self.profits.loc[:, 'sum_continuation_premium'] = self.profits['continuation_premium'].cumsum()
        
    def _set_total(self):
        p = self.profits
        p_sum = p['sum_interest'] - p['early_buyout_cost'] + p['sum_continuation_premium']
        self.profits.loc[:, 'total'] = p_sum

    def calc_total(self, till_date: Union[Date, RelativeDate]):
        for method in self.workflow:
            method()
        
        return self.profits