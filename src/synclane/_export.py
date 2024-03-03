"""Defines exporter to Typescript."""

import abc
import os
import sys
from datetime import date, datetime
from enum import Enum
from inspect import isclass
from itertools import cycle
from typing import MutableMapping, Sequence, TypeVar, Union  # type: ignore

from pydantic import BaseModel

from ._base import AbstractAsyncRpc, AbstractRpc


_NUMBERS = iter(cycle(range(1000)))


def get_next_number():
    return next(_NUMBERS)


if sys.version_info[0:2] < (3, 9):
    from typing import _GenericAlias  # type: ignore # pragma: no cover

    _GENERIC_TYPES = (_GenericAlias,)  # pragma: no cover

    def is_parametrized_generic(
        type_, _generic_types=(_GenericAlias,)
    ):  # pragma: no cover
        return isinstance(type_, _generic_types)

else:
    from typing import GenericAlias, _GenericAlias  # type: ignore

    _GENERIC_TYPES = (GenericAlias, _GenericAlias)

    def is_parametrized_generic(
        type_, _generic_types=(GenericAlias, _GenericAlias)
    ):
        return isinstance(type_, _generic_types)


if sys.version_info[0:2] <= (3, 9):
    NoneType = type(None)

    def is_union(type_):
        return is_parametrized_generic(type_) and type_.__origin__ is Union

else:

    from types import NoneType, UnionType  # pragma: no cover

    def is_union(type_):  # pragma: no cover
        return (
            isinstance(type_, UnionType)
            or is_parametrized_generic(type_)
            and type_.__origin__ is Union
        )


# CodeGenCtx = namedtuple("CodeGenCtx", ["is_union", "is_union_last"])
# CODE_GEN_GLOBAL = threading.local()
# CODE_GEN_CTX_STACK = CODE_GEN_GLOBAL.ctx_stack = [
#     CodeGenCtx(is_union=False, is_union_last=False)
# ]
#
#
# class CodeGenLayer:
#     def __init__(self, **kwargs):
#         self.kwargs = kwargs
#
#     def __enter__(self):
#         CODE_GEN_GLOBAL.ctx_stack.push(
#             CODE_GEN_GLOBAL.ctx_stack[0]._replace(self.kwargs)
#         )
#
#     def __exit__(self, exc_type, exc_value, tb):
#         CODE_GEN_GLOBAL.ctx_stack.pop()
#
#     @classmethod
#     def get_current(cls) -> CodeGenCtx:
#         return CODE_GEN_CTX_STACK[-1]


class CodeLines:
    """Code lines wrapper, keeping track of code with mutations."""

    __slots__ = ["lines", "mutate"]

    def __init__(self, lines, mutate):
        self.lines = lines
        self.mutate = mutate

    def get_joined(self):
        if self.mutate:
            return "\n".join(self.lines)

    def add(self, code_lines: "CodeLines"):
        self.lines.extend(code_lines.lines)
        self.mutate = self.mutate or code_lines.mutate

    @classmethod
    def concat(cls, code_lines_objs):
        result = CodeLines([], False)
        for obj in code_lines_objs:
            result.add(obj)
        return result

    @classmethod
    def naive(cls, src, dest):
        if src == dest:
            return cls([], False)
        return cls([f"{dest} = {src}"], False)


class BaseTsExporter:
    """Exporter to Typescript."""

    handlers: "Sequence[TypeHandler]" = ()

    def __init__(self, rpc: Union[AbstractAsyncRpc, AbstractRpc]):
        self.rpc = rpc
        self.name_to_interface_def: MutableMapping[str, str] = {}
        self.name_to_enum_def: MutableMapping[str, str] = {}

    def to_code_pieces(self):
        with open(
            os.path.join(os.path.dirname(__file__), "ts/base.ts"),
            encoding="utf-8",
        ) as f:
            yield f.read()

        function_defs = []
        prepare_params_defs = {}
        prepare_result_defs = {}
        for ts_name, procedure in self.rpc.procedures.items():
            in_type_def = self.root_type_to_interface(procedure.in_type)
            out_type_def = self.root_type_to_interface(procedure.out_type)

            prepare_params_defs[ts_name] = (
                """function _%(ts_name)sParamsToPrimitive(params: %(in_type_def)s): any {
let preparedParams: any;
%(ts_to_primitive_code)s
return preparedParams;
}"""
                % {
                    "ts_name": ts_name,
                    "in_type_def": in_type_def,
                    "ts_to_primitive_code": self.root_ts_to_primitive(
                        procedure.in_type, "params", "preparedParams"
                    ).get_joined()
                    or "preparedParams = params",
                }
            )
            prepare_result_defs[ts_name] = (
                """function _%(ts_name)sPrimitiveToResult(data: any): %(out_type_def)s {
%(primitive_to_ts_code)s
return data;
}"""
                % {
                    "ts_name": ts_name,
                    "out_type_def": out_type_def,
                    "primitive_to_ts_code": self.root_primitive_to_ts(
                        procedure.out_type, "data", "data"
                    ).get_joined()
                    or "",
                }
            )

            function_defs.append(
                """export function call%(ts_name)s(params: %(in_type_def)s): AbortableRequest<%(out_type_def)s> {
    return abortableFetch<%(in_type_def)s, %(out_type_def)s>("%(ts_name)s", params, _%(ts_name)sParamsToPrimitive, _%(ts_name)sPrimitiveToResult);
}"""
                % {
                    "in_type_def": in_type_def,
                    "out_type_def": out_type_def,
                    "ts_name": ts_name,
                }
            )

        for name, enum_def in self.name_to_enum_def.items():
            yield "\n"
            yield f"export enum {name} {enum_def}"

        for name, interface_def in self.name_to_interface_def.items():
            yield "\n"
            yield f"export interface {name} {interface_def}\n"

        for code in prepare_params_defs.values():
            yield "\n"
            yield code

        for code in prepare_result_defs.values():
            yield "\n"
            yield code

        for code in function_defs:
            yield "\n"
            yield code

    def write(self, filename):
        dir_name = os.path.dirname(filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)  # pragma: no cover

        with open(filename, "w", encoding="utf-8") as f:
            for piece in self.to_code_pieces():
                f.write(piece)
        return filename

    def name_interface(self, name, interface_def):
        self.name_to_interface_def[name] = interface_def
        return name

    def name_enum(self, name, enum_def):
        self.name_to_enum_def[name] = enum_def
        return name

    def root_type_to_interface(self, type_):
        result = None
        for handler in self.handlers:
            result = handler.type_to_interface(self, type_)
            if result is not None:
                return result

        raise TypeError("unsupported type", type_)

    def root_ts_to_primitive(self, type_, src, dest) -> CodeLines:
        result = None
        for handler in self.handlers:
            result = handler.ts_to_primitive(self, type_, src, dest)
            if result is not None:
                return result

        raise TypeError("unsupported type", type_)

    def root_primitive_to_ts(self, type_, src, dest) -> CodeLines:
        result = None
        for handler in self.handlers:
            result = handler.primitive_to_ts(self, type_, src, dest)
            if result is not None:
                return result

        raise TypeError("unsupported type", type_)


class TypeHandler(metaclass=abc.ABCMeta):
    """Base type handler to export python types to typescript ones."""

    @abc.abstractmethod
    def type_to_interface(self, exporter, type_):
        pass

    @abc.abstractmethod
    def ts_to_primitive(self, exporter, type_, src, dest):
        pass

    @abc.abstractmethod
    def primitive_to_ts(self, exporter, type_, src, dest):
        pass


class SimpleTypeHandler(TypeHandler):
    """Exports simple python types to typescript ones."""

    simple_types = {
        str: "string",
        bool: "boolean",
        int: "number",
        float: "number",
        dict: "any",
        tuple: "Array<any>",
        list: "Array<any>",
        NoneType: "undefined",
    }

    def type_to_interface(self, exporter, type_):
        if type_ in self.simple_types:
            return self.simple_types[type_]

    def ts_to_primitive(self, exporter, type_, src, dest):
        if type_ in self.simple_types:
            return CodeLines.naive(src, dest)

    def primitive_to_ts(self, exporter, type_, src, dest):
        if type_ in self.simple_types:
            return CodeLines.naive(src, dest)


class DateHandler(TypeHandler):
    """Exports python dates to typescript ones."""

    def type_to_interface(self, exporter, type_):
        if not isclass(type_):
            return
        if issubclass(type_, date):
            return "Date"

    def ts_to_primitive(self, exporter, type_, src, dest):
        if not isclass(type_):
            return
        if issubclass(type_, datetime):
            return CodeLines([f"{dest} = {src}.toISOString()"], True)
        if issubclass(type_, date):
            return CodeLines([f"{dest} = dateToStr({src})"], True)

    def primitive_to_ts(self, exporter, type_, src, dest):
        if not isclass(type_):
            return
        if issubclass(type_, datetime):
            return CodeLines([f"{dest} = new Date({src})"], True)
        if issubclass(type_, date):
            return CodeLines([f"{dest} = strToDate({src})"], True)


class PydanticModelHandler(TypeHandler):
    """Exports pydantic models to typescript interfaces."""

    def _is_supported(self, type_):
        return isclass(type_) and issubclass(type_, BaseModel)

    def type_to_interface(self, exporter, type_):
        if not self._is_supported(type_):
            return

        if type_.__pydantic_root_model__:
            return exporter.root_type_to_interface(
                type_.model_fields["root"].annotation
            )

        if type_.__pydantic_generic_metadata__["origin"]:
            origin = type_.__pydantic_generic_metadata__["origin"]
            name = exporter.root_type_to_interface(origin)
            return "{}<{}>".format(
                origin.__name__,
                ", ".join(
                    [
                        exporter.root_type_to_interface(arg)
                        for arg in type_.__pydantic_generic_metadata__["args"]
                    ]
                ),
            )

        elif type_.__pydantic_generic_metadata__["parameters"]:
            name = "{}<{}>".format(
                type_.__name__,
                ", ".join(
                    param.__name__
                    for param in type_.__pydantic_generic_metadata__[
                        "parameters"
                    ]
                ),
            )
            return exporter.name_interface(
                name,
                self._model_to_def(exporter, type_),
            )
        else:
            return exporter.name_interface(
                type_.__name__,
                self._model_to_def(exporter, type_),
            )

    def ts_to_primitive(self, exporter, type_, src, dest):
        if not self._is_supported(type_):
            return

        if type_.__pydantic_root_model__:
            return exporter.root_ts_to_primitive(
                type_.model_fields["root"].annotation, src, dest
            )

        code_lines = CodeLines(
            [f"{dest} = {{}}"],
            False,
        )

        for field_name, field_info in type_.model_fields.items():
            code_lines.add(
                exporter.root_ts_to_primitive(
                    field_info.annotation,
                    f"{src}.{field_name}",
                    f"{dest}.{field_name}",
                )
            )
        return code_lines

    def primitive_to_ts(self, exporter, type_, src, dest):
        if not self._is_supported(type_):
            return

        if type_.__pydantic_root_model__:
            return exporter.root_primitive_to_ts(
                type_.model_fields["root"].annotation, src, dest
            )

        code_lines = CodeLines([], False)

        for field_name, field_info in type_.model_fields.items():
            code_lines.add(
                exporter.root_primitive_to_ts(
                    field_info.annotation,
                    f"{src}.{field_name}",
                    f"{dest}.{field_name}",
                )
            )
        return code_lines

    def _model_to_def(self, exporter, type_):
        return "{%s}" % ", ".join(
            [
                "{}: {}".format(
                    field_name,
                    exporter.root_type_to_interface(field_info.annotation),
                )
                for field_name, field_info in type_.model_fields.items()
            ]
        )


class UnionHandler(TypeHandler):
    """Exports python union types to typescript ones."""

    def _is_supported(self, type_):
        if not is_union(type_):
            return False

        args = type_.__args__
        if len(args) == 2 and NoneType in args:
            return True

        raise TypeError("union of two or more not none types is unsupported")

    def type_to_interface(self, exporter, type_):
        if self._is_supported(type_):
            return " | ".join(
                [
                    exporter.root_type_to_interface(arg)
                    for arg in type_.__args__
                ]
            )

    def ts_to_primitive(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            args = type_.__args__
            not_none_type = args[0] if args[1] is NoneType else args[1]
            code_lines = CodeLines([f"if ({src} !== undefined) {{"], False)
            code_lines.add(
                exporter.root_ts_to_primitive(not_none_type, src, dest)
            )
            code_lines.lines.append("}")
            return code_lines

    def primitive_to_ts(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            args = type_.__args__
            not_none_type = args[0] if args[1] is NoneType else args[1]
            code_lines = CodeLines(
                [
                    f"if ({src} === null) {{ {dest} = undefined; }} else {{",
                ],
                True,
            )
            code_lines.add(
                exporter.root_primitive_to_ts(not_none_type, src, dest)
            )
            code_lines.lines.append("}")
            return code_lines


class TypeVarHandler(TypeHandler):
    """Exports python type vars to typescript ones."""

    def type_to_interface(self, exporter, type_):
        if isinstance(type_, TypeVar):
            return type_.__name__

    def ts_to_primitive(self, exporter, type_, src, dest):
        pass

    def primitive_to_ts(self, exporter, type_, src, dest):
        pass


class GenericListHandler(TypeHandler):
    """Exports python generic lists to typescript arrays."""

    def _is_supported(self, type_):
        if is_parametrized_generic(type_) and type_.__origin__ is list:
            args = type_.__args__
            if len(args) != 1:
                raise TypeError("lists expect only one type")
            return True
        return False

    def type_to_interface(self, exporter, type_):
        if self._is_supported(type_):
            return (
                f"Array<{exporter.root_type_to_interface(type_.__args__[0])}>"
            )

    def ts_to_primitive(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            args = type_.__args__
            index_name = f"i{get_next_number()}"

            code_lines = CodeLines(
                [f"{dest} = []", f"for (var {index_name} in {src}) {{"], False
            )
            code_lines.add(
                exporter.root_ts_to_primitive(
                    args[0],
                    f"{src}[{index_name}]",
                    f"{dest}[{index_name}]",
                )
            )
            if code_lines.mutate:
                code_lines.lines.append("}")
                return code_lines

            return CodeLines.naive(src, dest)

    def primitive_to_ts(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            args = type_.__args__
            index_name = f"i{get_next_number()}"
            code_lines = CodeLines(
                [f"for (var {index_name} in {src}) {{"], False
            )
            code_lines.add(
                exporter.root_primitive_to_ts(
                    args[0],
                    f"{src}[{index_name}]",
                    f"{dest}[{index_name}]",
                )
            )
            if code_lines.mutate:
                code_lines.lines.append("}")
                return code_lines

            return CodeLines.naive(src, dest)


class GenericTupleHandler(TypeHandler):
    """Exports python generic tuples to typescript arrays."""

    def _is_supported(self, type_):
        if is_parametrized_generic(type_) and type_.__origin__ is tuple:
            args = type_.__args__
            if Ellipsis in args and len(args) != 2:
                raise TypeError("variadic tuples expect only one type")
            return True
        return False

    def type_to_interface(self, exporter, type_):
        if self._is_supported(type_):
            args = type_.__args__
            if Ellipsis in args:
                non_ellipsis_type = args[0] if args[1] is Ellipsis else args[1]
                return f"Array<{exporter.root_type_to_interface(non_ellipsis_type)}>"

            else:
                return "[{}]".format(
                    ", ".join(
                        [exporter.root_type_to_interface(arg) for arg in args]
                    )
                )

    def ts_to_primitive(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            if Ellipsis in type_.__args__:
                args = type_.__args__
                index_name = f"i{get_next_number()}"

                code_lines = CodeLines(
                    [
                        f"{dest} = []",
                        f"for (var {index_name} in {src}) {{",
                    ],
                    False,
                )
                code_lines.add(
                    exporter.root_ts_to_primitive(
                        args[0] if args[1] is Ellipsis else args[1],
                        f"{src}[{index_name}]",
                        f"{dest}[{index_name}]",
                    )
                )
                if code_lines.mutate:
                    code_lines.lines.append("}")
                    return code_lines

                return CodeLines.naive(src, dest)

            else:
                value_name = f"v{get_next_number()}"
                code_lines = CodeLines(
                    [f"let {value_name}: any;", f"{dest} = []"], False
                )
                for index, arg in enumerate(type_.__args__):
                    code_lines.add(
                        exporter.root_ts_to_primitive(
                            arg,
                            f"{src}[{index}]",
                            f"{value_name}",
                        )
                    )
                    code_lines.lines.append(f"{dest}.push({value_name})")

                if code_lines.mutate:
                    return code_lines

                return CodeLines.naive(src, dest)

    def primitive_to_ts(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            if Ellipsis in type_.__args__:
                args = type_.__args__
                index_name = f"i{get_next_number()}"
                code_lines = CodeLines(
                    [f"for (var {index_name} in {src}) {{"], False
                )
                code_lines.add(
                    exporter.root_primitive_to_ts(
                        args[0] if args[1] is Ellipsis else args[1],
                        f"{src}[{index_name}]",
                        f"{dest}[{index_name}]",
                    )
                )
                if code_lines.mutate:
                    code_lines.lines.append("}")
                    return code_lines

                return CodeLines.naive(src, dest)

            else:
                return CodeLines.concat(
                    exporter.root_primitive_to_ts(
                        arg,
                        f"{src}[{index}]",
                        f"{dest}[{index}]",
                    )
                    for index, arg in enumerate(type_.__args__)
                )


class GenericDictHandler(TypeHandler):
    """Exports python generic dicts to typescript ones."""

    def _is_supported(self, type_):
        return is_parametrized_generic(type_) and type_.__origin__ is dict

    def type_to_interface(self, exporter, type_):
        if self._is_supported(type_):
            interface_key = exporter.root_type_to_interface(type_.__args__[0])
            interface_value = exporter.root_type_to_interface(
                type_.__args__[1]
            )
            return f"{{ [k: {interface_key}]: {interface_value}}}"
        pass

    def ts_to_primitive(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            key_name = f"k{get_next_number()}"
            prepared_key_name = f"k{get_next_number()}"
            code_lines = CodeLines(
                [
                    f"let {prepared_key_name}: any;",
                    f"{dest} = {{}}",
                    f"for (var {key_name} in {src}) {{",
                ],
                False,
            )
            code_lines.add(
                exporter.root_ts_to_primitive(
                    type_.__args__[0],
                    f"{key_name}",
                    f"{prepared_key_name}",
                )
            )
            code_lines.add(
                exporter.root_ts_to_primitive(
                    type_.__args__[1],
                    f"{src}[{key_name}]",
                    f"{dest}[{prepared_key_name}]",
                )
            )
            if code_lines.mutate:
                code_lines.lines.append("}")
                return code_lines

            return CodeLines.naive(src, dest)
        pass

    def primitive_to_ts(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            key_name = f"k{get_next_number()}"
            prepared_key_name = f"k{get_next_number()}"
            code_lines = CodeLines(
                [
                    f"let {prepared_key_name}: any",
                    f"for (var {key_name} in {src}) {{",
                ],
                False,
            )
            code_lines.add(
                exporter.root_primitive_to_ts(
                    type_.__args__[0],
                    f"{key_name}",
                    f"{prepared_key_name}",
                )
            )
            code_lines.add(
                exporter.root_primitive_to_ts(
                    type_.__args__[1],
                    f"{src}[{key_name}]",
                    f"{dest}[{prepared_key_name}]",
                )
            )
            if code_lines.mutate:
                code_lines.lines.append("}")
                return code_lines

            return CodeLines.naive(src, dest)
        pass


class EnumHandler(TypeHandler):
    """Exports python enums to typescript ones."""

    def _is_supported(self, type_):
        return isclass(type_) and issubclass(type_, Enum)

    def type_to_interface(self, exporter, type_):
        if self._is_supported(type_):
            return exporter.name_enum(
                type_.__name__,
                "{%s}"
                % ", ".join(
                    f"{item.name} = {repr(item.value)}" for item in type_
                ),
            )

    def ts_to_primitive(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            return CodeLines.naive(src, dest)

    def primitive_to_ts(self, exporter, type_, src, dest):
        if self._is_supported(type_):
            return CodeLines.naive(src, dest)


class TsExporter(BaseTsExporter):
    handlers = (
        SimpleTypeHandler(),
        DateHandler(),
        GenericListHandler(),
        GenericTupleHandler(),
        GenericDictHandler(),
        EnumHandler(),
        UnionHandler(),
        TypeVarHandler(),
        PydanticModelHandler(),
    )
