import json
from decimal import Decimal
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union

import pytest
from pydantic import BaseModel, ValidationError, constr

from synclane import AbstractProcedure, AbstractRpc, ProcedureNotFound
from synclane._export import TsExporter

from .base import dumb_rpc_cls, rpc_cls


def test_success(rpc_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        uid: str
        name: constr(min_length=1)

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(uid=in_.uid, name="John")

    rpc = rpc_cls().register(GetUser)

    result = rpc.call(
        {
            "id": 1,
            "method": "GetUser",
            "params": {"uid": "7fa8d"},
        },
        None,
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "uid": "7fa8d"},
    }

    result = rpc.call(
        {
            "id": 1,
            "method": "missing",
            "params": {"uid": "7fa8d"},
        },
        None,
    )
    assert result == {
        "error": {"code": -32601, "message": "Method not found"},
        "id": 1,
        "jsonrpc": "2.0",
    }

    result = rpc.call(
        {
            "id": 1,
            "method": "GetUser",
            "params": {},
        },
        None,
    )
    # fmt: off
    assert result == { "error": { "code": -32600, "details": [ { "input": {}, "loc": ("uid",), "msg": "Field required", "type": "missing", } ], "message": "Validation error", }, "id": 1, "jsonrpc": "2.0", }
    # fmt: on

    result = rpc.call(
        {},
        None,
    )
    # fmt: off
    assert result == { "error": { "code": -32600, "details": [ { "input": {}, "loc": ("id",), "msg": "Field required", "type": "missing", }, { "input": {}, "loc": ("method",), "msg": "Field required", "type": "missing", }, { "input": {}, "loc": ("params",), "msg": "Field required", "type": "missing", }, ], "message": "Validation error", }, "id": None, "jsonrpc": "2.0", }
    # fmt: on


def test_complex_types(rpc_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        params: UserParams
        name: str

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(params=in_, name="John")

    rpc = rpc_cls().register(GetUser)

    result = rpc.call(
        {
            "id": 1,
            "method": "GetUser",
            "params": {"uid": "7fa8d"},
        },
        None,
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "params": {"uid": "7fa8d"}},
    }


def test_exceptions(dumb_rpc_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        uid: str
        name: str

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return dict(uid=in_.uid, name="John")

    class GetUser2(AbstractProcedure):
        @staticmethod
        def call(in_: UserParams, context) -> UserDetails:
            return dict(uid=in_.uid, name="John")

    rpc = dumb_rpc_cls().register(GetUser, GetUser2)
    with pytest.raises(ValidationError):
        result = rpc.call(
            {
                "id": 1,
                "method": "GetUser",
                "params": {},
            },
            None,
        )
    result = rpc.call(
        {
            "id": 1,
            "method": "GetUser",
            "params": {"uid": "7fa8d"},
        },
        None,
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "uid": "7fa8d"},
    }
    result = rpc.call(
        {
            "id": 1,
            "method": "GetUser2",
            "params": {"uid": "78d"},
        },
        None,
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "uid": "78d"},
    }

    class GetBad(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return {}

    rpc.register(GetBad)
    with pytest.raises(ValidationError):
        result = rpc.call(
            {
                "id": 1,
                "method": "GetBad",
                "params": {"uid": "7fa8d"},
            },
            None,
        )

    class UnauthorizedException(Exception):
        pass

    def is_authorized(context):
        if "user" not in context:
            raise UnauthorizedException

    class AuthorizedGet(AbstractProcedure):
        PERMISSIONS = (is_authorized,)

        @classmethod
        def call(cls, in_: UserParams, context) -> dict:
            return {}

    rpc.register(AuthorizedGet)

    with pytest.raises(ValueError):
        rpc.register(AuthorizedGet)

    with pytest.raises(UnauthorizedException):
        rpc.call(
            {
                "id": 1,
                "method": "AuthorizedGet",
                "params": {"uid": "7fa8d"},
            },
            {},
        )

    assert rpc.call(
        {
            "id": 1,
            "method": "AuthorizedGet",
            "params": {"uid": "7fa8d"},
        },
        {"user": 1},
    ) == {"id": 1, "jsonrpc": "2.0", "result": {}}

    with pytest.raises(ValueError):

        class GetBad2(AbstractProcedure):
            def call(self, in_: UserParams, context):
                return {}

    with pytest.raises(ValueError):

        class GetBad3(AbstractProcedure):
            def call(self, in_, context) -> dict:
                return {}

    with pytest.raises(ValueError):

        class GetBad4(AbstractProcedure):
            def call(self):
                return {}

    with pytest.raises(ValueError):

        class GetBad5(AbstractProcedure):
            @staticmethod
            def call() -> dict:
                return {}
