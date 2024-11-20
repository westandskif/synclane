import json
import sys
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError, constr

from synclane import (
    AbstractAsyncProcedure,
    AbstractProcedure,
    AbstractRpc,
    ProcedureNotFound,
)
from synclane._export import TsExporter

from .base import check_ts, dumb_rpc_cls, rpc_async_cls, rpc_cls


SUPPORTS_NEW_UNION = sys.version_info[0:2] > (3, 9)
SUPPORTS_LIST_GENERIC = sys.version_info[0:2] >= (3, 9)
SUPPORTS_LITERAL = sys.version_info[0:2] >= (3, 8)

if SUPPORTS_LITERAL:
    from typing import Literal


def test_export_types_to_ts(rpc_cls):
    T = TypeVar("T")

    class Model1(BaseModel):
        a: str
        b: List[int]

    class Model2(BaseModel, Generic[T]):
        a: constr(min_length=1)
        b: List[T]

    exporter = TsExporter(rpc_cls())
    for type_, expected in [
        (str, "string"),
        (UUID, "string"),
        (bool, "boolean"),
        (int, "number"),
        (float, "number"),
        (dict, "any"),
        (tuple, "Array<any>"),
        (list, "Array<any>"),
        (List[str], "Array<string>"),
        (list[str] if SUPPORTS_NEW_UNION else List[str], "Array<string>"),
        (Tuple[bool], "[boolean]"),
        (tuple[bool] if SUPPORTS_NEW_UNION else Tuple[bool], "[boolean]"),
        (Optional[str], "string | undefined"),
        (
            (str | None) if SUPPORTS_NEW_UNION else Optional[str],
            "string | undefined",
        ),
        (Dict[str, bool], "{ [k: string]: boolean}"),
        (List[Model1], "Array<Model1>"),
        (Model2[int], "Model2<number>"),
        (List[Model2[List[Model1]]], "Array<Model2<Array<Model1>>>"),
    ]:
        assert exporter.root_type_to_interface(type_) == expected

    if SUPPORTS_LITERAL:
        assert (
            exporter.root_type_to_interface(Literal["abc", "cde"])
            == '"abc" | "cde"'
        )

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
        List[Decimal],
        list[int, str] if SUPPORTS_LIST_GENERIC else List[Decimal],
        tuple[int, str, ...] if SUPPORTS_LIST_GENERIC else List[Decimal],
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
        uid2: UUID
        flag_optional: bool = False
        created: (
            (datetime | None) if SUPPORTS_NEW_UNION else Optional[datetime]
        )
        type_: Literal["u", "p"] if SUPPORTS_LITERAL else str = "u"
        start_dts: List[date]
        start_dts2: Tuple[date, int]
        start_dts3: Tuple[date, ...]
        tuple_simple: Tuple[str, int]
        tuple_variadic: Tuple[str, ...]
        mapping: Dict[int, str]
        mapping2: Dict[int, date]

    class Tag(BaseModel, Generic[T]):
        tag_name: str
        tag_value: T
        created: datetime
        flag: bool
        flag_optional: bool = False
        number: int
        rate: float
        raw: dict
        opt: (str | None) if SUPPORTS_NEW_UNION else Optional[str]
        tuple_simple: tuple[T, int] if SUPPORTS_NEW_UNION else Tuple[T, int]
        tuple_variadic: tuple[T, ...] if SUPPORTS_NEW_UNION else Tuple[T, ...]
        list_simple: List[T]
        mapping: Dict[int, str]
        mapping2: Dict[int, date]

    class UserDetails(BaseModel):
        uid: str
        tags: List[Tag[int]]
        other_tags: List[Tag[date]]
        type_: Literal["u", "p"] if SUPPORTS_LITERAL else str = "u"

    class GetUser(AbstractProcedure):
        def call(self, in_: Tuple[UserParams], context) -> List[UserDetails]:
            return [UserDetails(uid=in_.uid, name="John")]

    rpc = rpc_cls().register(GetUser)

    assert check_ts(rpc.ts_dump("generated_output_complex.ts"))


def test_simple_export_ts(rpc_async_cls):
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    class UserParams(BaseModel):
        uids: list[str] if SUPPORTS_NEW_UNION else List[str]
        color: Color

    class UserDetails(UserParams):
        age: int

    class GetUser(AbstractAsyncProcedure):
        async def call_async(self, in_: UserParams, context) -> UserDetails:
            pass

    rpc = rpc_async_cls().register(GetUser)

    assert check_ts(rpc.ts_dump("generated_output_simple.ts"))
