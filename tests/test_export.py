import json
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union
from enum import Enum

import pytest
from pydantic import BaseModel, ValidationError, constr

from synclane import AbstractProcedure, AbstractRpc, ProcedureNotFound
from synclane._export import RpcContext, TsExporter

from .base import check_ts, dumb_rpc_cls, rpc_cls
import sys

SUPPORTS_NEW_UNION = sys.version_info[0:2] > (3, 9)


def test_export_types_to_ts(rpc_cls):
    T = TypeVar("T")

    class Model1(BaseModel):
        a: str
        b: list[int]

    class Model2(BaseModel, Generic[T]):
        a: constr(min_length=1)
        b: list[T]

    exporter = TsExporter(rpc_cls(), RpcContext(url="abc"))
    for type_, expected in [
        (str, "string"),
        (bool, "boolean"),
        (int, "number"),
        (float, "number"),
        (dict, "any"),
        (tuple, "Array<any>"),
        (list, "Array<any>"),
        (list[str], "Array<string>"),
        (tuple[bool], "[boolean]"),
        (Optional[str], "string | undefined"),
        (
            (str | None) if SUPPORTS_NEW_UNION else Optional[str],
            "string | undefined",
        ),
        (Dict[str, bool], "{ [k: string]: boolean}"),
        (list[Model1], "Array<Model1>"),
        (Model2[int], "Model2<number>"),
        (list[Model2[list[Model1]]], "Array<Model2<Array<Model1>>>"),
    ]:
        assert exporter.root_type_to_interface(type_) == expected

    assert (
        exporter.name_to_interface_def["Model1"]
        == "{a: string, b: Array<number>}"
    )
    assert (
        exporter.name_to_interface_def["Model2<T>"]
        == "{a: string, b: Array<T>}"
    )

    for type_ in [
        (str | int) if SUPPORTS_NEW_UNION else Union[str, int],
        Union[int, str],
        Decimal,
        list[Decimal],
        list[int, str],
        tuple[int, str, ...],
    ]:
        with pytest.raises(TypeError):
            exporter.root_type_to_interface(type_)
        with pytest.raises(TypeError):
            exporter.root_primitive_to_ts(type_, "x", "x")
        with pytest.raises(TypeError):
            exporter.root_ts_to_primitive(type_, "x", "x")

    for instance_ in [TypeVar("T")]:
        with pytest.raises(TypeError):
            exporter.root_primitive_to_ts(type_, "x", "x")
        with pytest.raises(TypeError):
            exporter.root_ts_to_primitive(type_, "x", "x")


def test_complex_export_ts(rpc_cls):
    T = TypeVar("T")

    class UserParams(BaseModel):
        uid: str
        created: (
            (datetime | None) if SUPPORTS_NEW_UNION else Optional[datetime]
        )
        start_dts: list[date]
        start_dts2: tuple[date, int]
        start_dts3: tuple[date, ...]
        tuple_simple: tuple[str, int]
        tuple_variadic: tuple[str, ...]
        mapping: dict[int, str]
        mapping2: dict[int, date]

    class Tag(BaseModel, Generic[T]):
        tag_name: str
        tag_value: T
        created: datetime
        flag: bool
        number: int
        rate: float
        raw: dict
        opt: (str | None) if SUPPORTS_NEW_UNION else Optional[str]
        tuple_simple: tuple[T, int]
        tuple_variadic: tuple[T, ...]
        list_simple: list[T]
        mapping: dict[int, str]
        mapping2: dict[int, date]

    class UserDetails(BaseModel):
        uid: str
        tags: list[Tag[int]]
        other_tags: list[Tag[date]]

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(uid=in_.uid, name="John")

    rpc = rpc_cls().register(GetUser)

    assert check_ts(
        TsExporter(rpc, RpcContext(url="abc")).write(
            "generated_output_complex.ts"
        )
    )


def test_simple_export_ts(rpc_cls):
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    class UserParams(BaseModel):
        uids: list[str]
        color: Color

    class UserDetails(UserParams):
        age: int

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            pass

    rpc = rpc_cls().register(GetUser)

    assert check_ts(
        TsExporter(rpc, RpcContext(url="abc")).write(
            "generated_output_simple.ts"
        )
    )
