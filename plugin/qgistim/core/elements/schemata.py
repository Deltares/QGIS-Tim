import abc
from collections import defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from qgistim.core.schemata import (
    ConsistencySchema,
    IterableSchemaContainer,
    SchemaContainer,
)


class ValidationData(NamedTuple):
    schemata: Dict[str, SchemaContainer]
    consistency_schemata: Tuple[ConsistencySchema]
    name: str
    data: Dict[str, Any]
    other: Optional[Dict[str, Any]] = None


class SchemaBase(abc.ABC):
    # TODO: check for presence of columns
    timml_schemata: Dict[str, Union[SchemaContainer, IterableSchemaContainer]] = {}
    timml_consistency_schemata: Tuple[ConsistencySchema] = ()
    ttim_schemata: Dict[str, Union[SchemaContainer, IterableSchemaContainer]] = {}
    ttim_consistency_schemata: Tuple[ConsistencySchema] = ()
    timeseries_schemata: Dict[str, Union[SchemaContainer, IterableSchemaContainer]] = {}

    @staticmethod
    def _validate_table(vd: ValidationData) -> Dict[str, List]:
        errors = defaultdict(list)
        for variable, schema in vd.schemata.items():
            _errors = schema.validate(vd.data[variable], vd.other)
            if _errors:
                errors[f"{vd.name} {variable}"].extend(_errors)

        # The consistency schema rely on the row input being valid.
        # Hence, they are tested second.
        if not errors:
            for schema in vd.consistency_schemata:
                _error = schema.validate(vd.data, vd.other)
                if _error:
                    errors[vd.name].append(_error)

        return errors

    @classmethod
    def validate_timeseries(
        cls, name: str, data: Dict[str, Any], other=None
    ) -> Dict[str, List]:
        vd = ValidationData(cls.timeseries_schemata, (), name, data, other)
        return cls._validate_table(vd)

    @classmethod
    def validate_timml(
        cls, name: str, data: Dict[str, Any], other=None
    ) -> Dict[str, List]:
        vd = ValidationData(
            cls.timml_schemata, cls.timml_consistency_schemata, name, data, other
        )
        return cls._validate(vd)

    @classmethod
    def validate_ttim(
        cls, name: str, data: Dict[str, Any], other=None
    ) -> Dict[str, List]:
        vd = ValidationData(
            cls.ttim_schemata, cls.ttim_consistency_schemata, name, data, other
        )
        return cls._validate(vd)

    @abc.abstractclassmethod
    def _validate(vd: ValidationData) -> Dict[str, List]:
        pass


class TableSchema(SchemaBase, abc.ABC):
    """
    Schema for Tabular data, such as Aquifer properties.
    """

    @classmethod
    def _validate(
        cls,
        vd: ValidationData,
    ) -> Dict[str, List]:
        return cls._validate_table(vd)


class RowWiseSchema(SchemaBase, abc.ABC):
    """
    Schema for entries that should be validated row-by-row, such as Wells.
    """

    @staticmethod
    def _validate(vd: ValidationData) -> Dict[str, List]:
        errors = defaultdict(list)

        for i, row in enumerate(vd.data):
            row_errors = defaultdict(list)

            for variable, schema in vd.schemata.items():
                _errors = schema.validate(row[variable], vd.other)
                if _errors:
                    row_errors[variable].extend(_errors)

            # Skip consistency tests if the individual values are not good.
            if not row_errors:
                for schema in vd.consistency_schemata:
                    _error = schema.validate(row, vd.other)
                    if _error:
                        row_errors["Row:"].append(_error)

            if row_errors:
                errors[f"Row {i + 1}:"] = row_errors

        return errors


class SingleRowSchema(RowWiseSchema, abc.ABC):
    """
    Schema for entries that should contain only one row, which should be
    validated as a row, such as Constant, Domain, Uniform Flow.
    """

    @staticmethod
    def _validate(vd: ValidationData) -> Dict[str, List]:
        nrow = len(vd.data)
        if nrow != 1:
            return {
                vd.name: [
                    f"Table must contain a single row. Table contains {nrow} rows."
                ]
            }
        return RowWiseSchema._validate(vd)
