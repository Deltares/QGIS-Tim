import abc
import operator
from typing import Any, Sequence

OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def discard_none(data):
    return [v for v in data if v is not None]


def collect_errors(schemata, data, **kwargs):
    errors = []
    for schema in schemata:
        try:
            schema.validate(data, **kwargs)
        except ValidationError as e:
            errors.append(str(e))

    if errors:
        raise ValidationError("\n\t".join(errors))


class ValidationError(Exception):
    pass


class BaseSchema(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def validate(self):
        pass


# Schemata for a single value


class Optional(BaseSchema):
    def __init__(self, *schemata):
        self.schemata = schemata

    def validate(self, data, **kwargs):
        if data is None:
            return
        collect_errors(self.schemata, data, **kwargs)
        return


class Required(BaseSchema):
    def __init__(self, *schemata):
        self.schemata = schemata

    def validate(self, data, **kwargs):
        if data is None:
            raise ValidationError("a value is required.")
        collect_errors(self.schemata, data, **kwargs)
        return


class Positive:
    def validate(self, value):
        if value < 0:
            raise ValidationError(f"Non-positive value: {value}")
        return


class Time(BaseSchema):
    def validate(self, data, **kwargs):
        start = kwargs["start"]
        end = kwargs["end"]
        if not (start < data < end):
            raise ValidationError(
                f"time does not fall in model time window: {start} to {end}"
            )
        return


class AllOrNone(BaseSchema):
    def __init__(self, *variables: Sequence[str]):
        self.variables = variables

    def validate(self, data):
        present = [data[v] is not None for v in self.variables]
        if any(present) != all(present):
            raise ValidationError(
                "Exactly all or none of the following variables must be "
                f"provided: {self.variables}"
            )
        return


class Xor(BaseSchema):
    "One or the other should be provided"

    def __init__(self, x: str, y: str):
        self.x = x
        self.y = y

    def validate(self, data):
        if not ((data[self.x] is None) ^ (data[self.y] is None)):
            raise ValidationError(f"Either {self.x} or {self.y} should be provided.")
        return


class NotBoth(BaseSchema):
    def __init__(self, x: str, y: str):
        self.x = x
        self.y = y

    def validate(self, data):
        if (data[self.x] is not None) and (data[self.y] is not None):
            raise ValidationError(f"Both {self.x} and {self.y} should not be provided.")
        return


class Membership(BaseSchema):
    def __init__(self, members_key: str):
        self.members_key = members_key

    def validate(self, data, **kwargs):
        if data is None:
            return
        member_values = kwargs[self.members_key]
        if data not in member_values:
            raise ValidationError(
                f"Value {data} not found in {self.members_key}: {member_values}"
            )
        return


# Schemata for collections of values


class AllRequired(BaseSchema):
    def __init__(self, *schemata):
        self.schemata = schemata

    def validate(self, data, **kwargs):
        missing = [i + 1 for i, v in enumerate(data) if v is not None]
        if missing:
            raise ValidationError(f"No values provided at rows: {missing}")

        collect_errors(self.schemata, data, **kwargs)
        return


class OffsetAllRequired(BaseSchema):
    def __init__(self, *schemata):
        self.schemata = schemata

    def validate(self, data, **kwargs):
        missing = [i + 2 for i, v in enumerate(data[1:]) if v is not None]
        if missing:
            raise ValidationError(f"No values provided at rows: {missing}")

        collect_errors(self.schemata, data, **kwargs)
        return


class AllOptional(BaseSchema):
    def __init__(self, *schemata):
        self.schemata = schemata

    def validate(self, data, **kwargs):
        missing = [i + 1 for i, v in enumerate(data) if v is not None]
        if len(missing) == len(data):
            return

        collect_errors(self.schemata, data, **kwargs)
        return


class Range(BaseSchema):
    def validate(self, data):
        expected = list(range(len(data)))
        if not data == expected:
            raise ValidationError(f"Expected {expected}, received: {data}")
        return


class Increasing(BaseSchema):
    def validate(self, data):
        data = discard_none(data)
        monotonic = all(a <= b for a, b in zip(data, data[1:]))
        if not monotonic:
            raise ValidationError(f"Values are not increasing: {data}")
        return


class StrictlyIncreasing(BaseSchema):
    def validate(self, data):
        data = discard_none(data)
        monotonic = all(a < b for a, b in zip(data, data[1:]))
        if not monotonic:
            raise ValidationError(
                f"Values are not strictly increasing (no repeated values): {data}"
            )
        return


class Decreasing(BaseSchema):
    def validate(self, data):
        data = discard_none(data)
        monotonic = all(a >= b for a, b in zip(data, data[1:]))
        if not monotonic:
            raise ValidationError(f"Values are not decreasing: {data}")
        return


class StrictlyDecreasing(BaseSchema):
    def validate(self, data):
        data = discard_none(data)
        monotonic = all(a > b for a, b in zip(data, data[1:]))
        if not monotonic:
            raise ValidationError(
                f"Values are not strictly decreasing (no repeated values): {data}"
            )
        return


class AllGreaterEqual(BaseSchema):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def validate(self, data):
        x = data[self.x]
        y = data[self.y]
        wrong = [i + 1 for i, (a, b) in zip(x, y) if a < b]
        if wrong:
            raise ValidationError(
                f"{self.x} is not greater or requal to {self.y} at rows: {wrong}"
            )
        return


class FirstOnly(BaseSchema):
    """Exclusively the first value must be provided."""

    def validate(self, data):
        if any(v is not None for v in data[1:]):
            raise ValidationError("Only the first value may be filled in.")
        return


# Global schemata


class SemiConfined(BaseSchema):
    def validate(self, data):
        semiconf_data = {
            "aquitard_c": data["aquitard_c"][0],
            "semiconf_top": data["semiconf_top"][0],
            "semiconf_head": data["semiconf_head"][0],
        }
        present = [v is not None for v in semiconf_data.values()]
        if any(present) != all(present):
            variables = ", ".join(semiconf_data.keys())
            raise ValidationError(
                "To enable a semi-confined top, the first row must be fully "
                f"filled in for {variables}. To disable semi-confined top, none "
                f"of the values must be filled in. Found: {semiconf_data}"
            )
        return


class ValueSchema(BaseSchema, abc.ABC):
    """
    Base class for AllValueSchema or AnyValueSchema.
    """

    def __init__(
        self,
        operator: str,
        other: Any,
    ):
        self.operator = OPERATORS[operator]
        self.operator_str = operator
        self.other = other


class AllValue(ValueSchema):
    def validate(self, data, **kwargs):
        error = ValidationError(
            f"Not all values comply with criterion: {self.operator_str} {self.other}"
        )
        if isinstance(self.other, str):
            other_obj = kwargs[self.other]
            if any(self.operator(a, b) for a, b in zip(data, other_obj)):
                raise error
        else:
            if any(self.operator(v, self.other) for v in data):
                raise error
        return


class InLayer(BaseSchema):
    def validate(self, data, **kwargs):
        allowed_layers = kwargs["layers"]
        for value in data:
            if value not in allowed_layers:
                raise ValidationError(
                    f"Layer {value} is not in aquifer layers: {allowed_layers}"
                )


class SingleRow(BaseSchema):
    def validate(self, data, **kwargs):
        if len(data) != 1:
            raise ValidationError("Constant may contain only one row.")
        super().validate(data, **kwargs)
