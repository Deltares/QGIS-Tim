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
ErrorList = List[str]


def format(data) -> str:
    return ", ".join(map(str, data))


# Base classes


class BaseSchema(abc.ABC):
    """Base class for single value."""

    def __init__(self):
        pass

    @abc.abstractmethod
    def validate(self, data, other) -> MaybeError:
        pass

    def validate_many(self, data, other) -> ErrorList:
        errors = []
        for value in data:
            error = self.validate(value, other)
            if error is not None:
                errors.append(error)

        return errors


class ConsistencySchema(BaseSchema, abc.ABC):
    pass


class IterableSchema(abc.ABC):
    """Base class for collection of values."""

    def __init__(self, *schemata):
        self.schemata = schemata

    def validate_many(self, data, other) -> ErrorList:
        error = self.validate(data, other)
        if error:
            return [error]
        else:
            return []


class SchemaContainer(abc.ABC):
    def __init__(self, *schemata):
        self.schemata = schemata

    @abc.abstractmethod
    def validate(self):
        pass

    def _validate_schemata(self, data, other=None) -> ErrorList:
        errors = []
        for schema in self.schemata:
            _error = schema.validate(data, other)
            if _error:
                errors.append(_error)
        return errors


class IterableSchemaContainer(abc.ABC):
    def __init__(self, *schemata):
        self.schemata = schemata

    @abc.abstractmethod
    def validate(self):
        pass

    def _validate_schemata(self, data, other=None) -> ErrorList:
        errors = []
        for schema in self.schemata:
            _errors = schema.validate_many(data, other)
            if _errors:
                errors.extend(_errors)
        return errors


# Schema containers for a single value.


class OptionalFirstOnly(SchemaContainer):
    """Exclusively the first value may be provided."""

    def validate(self, data, other=None) -> ErrorList:
        if any(v is not None for v in data[1:]):
            return ["Only the first value may be filled in."]
        elif data[0] is None:
            return []
        else:
            return self._validate_schemata(data[0], other)


class RequiredFirstOnly(SchemaContainer):
    """Exclusively the first value must be provided."""

    def validate(self, data, other=None) -> ErrorList:
        if data[0] is None:
            return ["The first value must be filled in."]
        elif any(v is not None for v in data[1:]):
            return ["Only the first value may be filled in."]
        else:
            return self._validate_schemata(data[0], other)


class Optional(SchemaContainer):
    def validate(self, data, other=None) -> ErrorList:
        if data is None:
            return []
        return self._validate_schemata(data, other)


class Required(SchemaContainer):
    def validate(self, data, other=None) -> ErrorList:
        if data is None:
            return ["a value is required."]
        return self._validate_schemata(data, other)


# SchemataContainer for multiple values.


class AllRequired(IterableSchemaContainer):
    def validate(self, data, other=None) -> ErrorList:
        missing = [i + 1 for i, v in enumerate(data) if v is None]
        if missing:
            return [f"No values provided at row(s): {format(missing)}"]
        return self._validate_schemata(data, other)


class OffsetAllRequired(IterableSchemaContainer):
    def validate(self, data, other=None) -> ErrorList:
        missing = [i + 2 for i, v in enumerate(data[1:]) if v is None]
        if missing:
            return [f"No values provided at row(s): {format(missing)}"]
        if data[0] is None:
            return self._validate_schemata(data[1:], other)
        else:
            return self._validate_schemata(data, other)


class AllOptional(IterableSchemaContainer):
    def validate(self, data, other=None) -> ErrorList:
        missing = [i + 1 for i, v in enumerate(data) if v is None]
        if len(missing) == len(data):
            return []
        return self._validate_schemata(data, other)


# Schemata for a single value.


class Positive(BaseSchema):
    def validate(self, data, _=None) -> MaybeError:
        if data < 0:
            return f"Non-positive value: {data}"
        return None


class AllOrNone(BaseSchema):
    def __init__(self, *variables: Sequence[str]):
        self.variables = variables

    def validate(self, data, _=None) -> MaybeError:
        present = [data.get(v) is not None for v in self.variables]
        if any(present) != all(present):
            vars = ", ".join(self.variables)
            return (
                "Exactly all or none of the following variables must be "
                f"provided: {vars}"
            )
        return None


class NotBoth(BaseSchema):
    def __init__(self, x: str, y: str):
        self.x = x
        self.y = y

    def validate(self, data, _=None) -> MaybeError:
        if (data.get(self.x) is not None) and (data.get(self.y) is not None):
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


class CircularGeometry(BaseSchema):
    def validate(self, data, _=None) -> MaybeError:
        coordinates = data
        # Compute centroid.
        n_vertex = len(data)
        x_mean = 0.0
        y_mean = 0.0
        for x, y in coordinates:
            x_mean += x / n_vertex
            y_mean += y / n_vertex
        # Compute distances to centroid.
        distances = [(x - x_mean) ** 2 + (y - y_mean) ** 2 for (x, y) in coordinates]
        min_distance = min(distances) ** 0.5
        max_distance = max(distances) ** 0.5
        # Accept 1% deviation in squared distance from a circle.
        if (max_distance - min_distance) > (0.01 * min_distance):
            return "Geometry is not circular."
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
            return f"{self.x} is not greater or equal to {self.y} at row(s): {format(wrong)}"
        return None


class AtleastOneTrue(IterableSchema):
    def validate(self, data, _=None) -> MaybeError:
        if not any(value for value in data):
            return "Atleast one row value must be true."
        return None


# Consistency schemata


class SemiConfined(ConsistencySchema):
    def validate(self, data, _=None) -> MaybeError:
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
        semitop = data["semiconf_top"][0]
        if semitop is not None and semitop <= data["aquifer_top"][0]:
            return "semiconf_top must be greater than first aquifer_top."
        if "rate" in data:
            if data["rate"][0] is not None and semitop:
                return "A rate cannot be given when a semi-confined is enabled."
        return None


class SingleRow(ConsistencySchema):
    def validate(self, data, _=None) -> MaybeError:
        nrow = len(data)
        if nrow != 1:
            return f"Table must contain one row, found {nrow} rows."
        return None
