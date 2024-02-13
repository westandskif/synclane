import abc
import inspect
from datetime import date
from typing import (
    Any,
    Dict,
    GenericAlias,
    List,
    Tuple,
    TypedDict,
    TypeVar,
    _GenericAlias,
)

from pydantic import BaseModel, RootModel


class BaseRpcException(Exception):
    pass


class ProcedureNotFound(BaseRpcException):
    pass


def ensure_pydantic_model(some_type):
    return (
        some_type if issubclass(some_type, BaseModel) else RootModel[some_type]
    )


class ProcedureMeta(abc.ABCMeta):
    def __new__(meta_cls, name, bases, dict_):
        cls = super().__new__(meta_cls, name, bases, dict_)
        cls.name = name
        cls.in_type, cls.out_type = meta_cls.get_in_n_out_models(cls.call)
        return cls

    @staticmethod
    def get_in_n_out_models(method):
        signature = inspect.signature(method)
        return_annotation = signature.return_annotation
        if return_annotation is inspect.Signature.empty:
            raise ValueError(
                "missing return annotation", method, return_annotation
            )

        in_type = None
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            in_type = param.annotation
            break

        if in_type is None or in_type is inspect.Signature.empty:
            raise ValueError("missing input type annotation", method, in_type)

        return ensure_pydantic_model(in_type), ensure_pydantic_model(
            return_annotation
        )


class AbstractProcedure(metaclass=ProcedureMeta):
    DTYPES = ("user",)
    PERMISSIONS = ()

    def _call(self, raw_data, context):
        self.check_permissions(context)
        in_ = self.in_type.model_validate(raw_data)
        pump_result = self.call(in_, context)
        return self.out_type.model_validate(pump_result)

    def check_permissions(self, context):
        for permission in self.PERMISSIONS:
            permission(context)

    @abc.abstractmethod
    def call(self, in_: str, context) -> str:
        raise NotImplementedError


# {
#     "jsonrpc": "2.0",
#     "method": "subtract",
#     "params": {"subtrahend": 23, "minuend": 42},
#     "id": 3,
# }


class RpcRequest(BaseModel):
    # jsonrpc: str
    id: int
    method: str
    params: Any


class AbstractRpc(abc.ABC):
    __slots__ = ["procedures"]

    def __init__(self):
        self.procedures = {}

    def register(self, *procedures):
        for procedure in procedures:
            name = procedure.name
            if name in self.procedures:
                raise ValueError(
                    "non unique procedure name",
                    self.procedures[name],
                    procedure,
                )
            self.procedures[name] = procedure()
        return self

    def call(self, raw_data, context):
        request_id = None
        try:
            rpc_request = RpcRequest.model_validate(raw_data)
            request_id = rpc_request.id
            if rpc_request.method not in self.procedures:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": "Method not found"},
                    "id": request_id,
                }
            result = self.procedures[rpc_request.method]._call(
                rpc_request.params, context
            )
            return {
                "jsonrpc": "2.0",
                "result": result.model_dump(),
                "id": request_id,
            }
        except Exception as e:
            data = self.prepare_exception(raw_data, context, e)
            if data is None:
                raise
            return {
                "jsonrpc": "2.0",
                "error": data,
                "id": request_id,
            }

    @abc.abstractmethod
    def prepare_exception(self, raw_data, context, exc):
        raise NotImplementedError
