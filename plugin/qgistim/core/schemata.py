import abc
import operator
from typing import List, Sequence, Union

OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


MaybeError = Union[None, str]
MaybeErrorList = Union[None, List[str]]


def format(data) -> str:
    return ", ".join(map(str, data))


def discard_none(data):
    return [v for v in data if v is not None]


class BaseSchema(abc.ABC):
    """Base class for single value."""

    def __init__(self):
        pass

    @abc.abstractmethod
    def validate(self, data, other) -> MaybeError:
        pass

    def validate_many(self, data, other) -> MaybeErrorList:
        errors = []
        for value in data:
            error = self.validate(value, other)
            if error is not None:
                errors.append(error)

        if errors:
            return errors
        else:
            return None


class IterableSchema(BaseSchema, abc.ABC):
    """Base class for collection of values."""

    def validate_many(self, data, other) -> MaybeErrorList:
        error = self.validate(data, other)
        if error:
            if isinstance(error, list):
                return error
            else:
                return [error]
        else:
            return None


class SchemaContainer(IterableSchema):
    def __init__(self, *schemata):
        self.schemata = schemata

    def _validate_schemata(self, data, other=None) -> MaybeErrorList:
        errors = []
        for schema in self.schemata:
            if isinstance(data, list):
                _errors = schema.validate_many(data, other)
                if _errors:
                    errors.extend(_errors)
            else:
                _error = schema.validate(data, other)
                if _error:
                    errors.append(_error)

        if errors:
            return errors

        return None


# SchemataContainer for a single value.


class Optional(SchemaContainer):
    def validate(self, data, other=None) -> MaybeError:
        if data is None:
            return None
        return self._validate_schemata(data, other)


class Required(SchemaContainer):
    def validate(self, data, other=None) -> MaybeError:
        if data is None:
            return "a value is required."
        return self._validate_schemata(data, other)


# SchemataContainer for multiple values.


class AllRequired(SchemaContainer):
    def validate(self, data, other=None) -> MaybeErrorList:
        missing = [i + 1 for i, v in enumerate(data) if v is None]
        if missing:
            return [f"No values provided at rows: {format(missing)}"]
        return self._validate_schemata(data, other)


class OffsetAllRequired(SchemaContainer):
    def validate(self, data, other=None) -> MaybeErrorList:
        missing = [i + 2 for i, v in enumerate(data[1:]) if v is None]
        if missing:
            return [f"No values provided at rows: {format(missing)}"]
        if data[0] is None:
            return self._validate_schemata(data[1:], other)
        else:
            return self._validate_schemata(data, other)


class AllOptional(SchemaContainer):
    def validate(self, data, other=None) -> MaybeErrorList:
        missing = [i + 1 for i, v in enumerate(data) if v is None]
        if len(missing) == len(data):
            return None
        return self._validate_schemata(data, other)


# Schemata for a single value.


class Positive(BaseSchema):
    def validate(self, data, _=None) -> MaybeError:
        if data < 0:
            return f"Non-positive value: {data}"
        return None


class Time(BaseSchema):
    def validate(self, data, other=None) -> MaybeError:
        start = other["start"]
        end = other["end"]
        if not (start < data < end):
            return f"time does not fall in model time window: {start} to {end}"
        return None


class AllOrNone(BaseSchema):
    def __init__(self, *variables: Sequence[str]):
        self.variables = variables

    def validate(self, data, _=None) -> MaybeError:
        present = [data[v] is not None for v in self.variables]
        if any(present) != all(present):
            vars = ", ".join(self.variables)
            return (
                "Exactly all or none of the following variables must be "
                f"provided: {vars}"
            )
        return None


class Xor(BaseSchema):
    "One or the other should be provided"

    def __init__(self, x: str, y: str):
        self.x = x
        self.y = y

    def validate(self, data, _=None) -> MaybeError:
        if not ((data[self.x] is None) ^ (data[self.y] is None)):
            return f"Either {self.x} or {self.y} should be provided, not both."
        return None


class NotBoth(BaseSchema):
    def __init__(self, x: str, y: str):
        self.x = x
        self.y = y

    def validate(self, data, _=None) -> MaybeError:
        if (data[self.x] is not None) and (data[self.y] is not None):
            return f"Either {self.x} or {self.y} should be provided, not both."
        return None


class Membership(BaseSchema):
    def __init__(self, members_key: str):
        self.members_key = members_key

    def validate(self, data, other=None) -> MaybeError:
        if data is None:
            return None
        member_values = other[self.members_key]
        if data not in member_values:
            return (
                f"Value {data} not found in {self.members_key}: {format(member_values)}"
            )
        return None


# Schemata for a collection of values.


class Range(IterableSchema):
    def validate(self, data, _=None) -> MaybeError:
        expected = list(range(len(data)))
        if not data == expected:
            return f"Expected {format(expected)}; received {format(data)}"
        return None


class Increasing(IterableSchema):
    def validate(self, data, _=None) -> MaybeError:
        monotonic = all(a <= b for a, b in zip(data, data[1:]))
        if not monotonic:
            return f"Values are not increasing: {format(data)}"
        return None


class StrictlyIncreasing(IterableSchema):
    def validate(self, data, _=None) -> MaybeError:
        monotonic = all(a < b for a, b in zip(data, data[1:]))
        if not monotonic:
            return f"Values are not strictly increasing (no repeated values): {format(data)}"
        return None


class Decreasing(IterableSchema):
    def validate(self, data, _=None) -> MaybeError:
        monotonic = all(a >= b for a, b in zip(data, data[1:]))
        if not monotonic:
            return f"Values are not decreasing: {format(data)}"
        return None


class StrictlyDecreasing(IterableSchema):
    def validate(self, data, _=None) -> MaybeError:
        monotonic = all(a > b for a, b in zip(data, data[1:]))
        if not monotonic:
            return f"Values are not strictly decreasing (no repeated values): {format(data)}"
        return None


class AllGreaterEqual(IterableSchema):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def validate(self, data, _=None) -> MaybeError:
        x = data[self.x]
        y = data[self.y]
        wrong = [i + 1 for i, (a, b) in enumerate(zip(x, y)) if a < b]
        if wrong:
            return (
                f"{self.x} is not greater or equal to {self.y} at rows: {format(wrong)}"
            )
        return None


class FirstOnly(SchemaContainer):
    """Exclusively the first value must be provided."""

    def validate(self, data, other=None) -> Union[MaybeError, MaybeErrorList]:
        if any(v is not None for v in data[1:]):
            return "Only the first value may be filled in."
        return self._validate_schemata(data[0], other)


# Consistency schemata


class SemiConfined(IterableSchema):
    def validate(self, data, other) -> MaybeError:
        semiconf_data = {
            "aquitard_c": data["aquitard_c"][0],
            "semiconf_top": data["semiconf_top"][0],
            "semiconf_head": data["semiconf_head"][0],
        }
        present = [v is not None for v in semiconf_data.values()]
        if any(present) != all(present):
            variables = format(semiconf_data.keys())
            values = format(semiconf_data.values())
            return (
                "To enable a semi-confined top, the first row must be fully "
                f"filled in for {variables}. To disable semi-confined top, none "
                f"of the values must be filled in. Found: {values}"
            )
        if data["semiconf_top"][0] <= other["aquifer_top"][0]:
            return "semiconf_top must be greater than first aquifer_top."
        return None


class SingleRow(IterableSchema):
    def validate(self, data, other=None) -> MaybeError:
        if len(data) != 1:
            return "Constant may contain only one row."
