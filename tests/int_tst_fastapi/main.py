from datetime import date, datetime
from enum import Enum

from fastapi import FastAPI, Request
from pydantic import BaseModel, ValidationError, constr

from synclane import AbstractProcedure, AbstractRpc, RpcContext, TsExporter


######## ERROR HANDLING #########################
class UnauthorizedError(Exception):
    pass


def is_authorized(context):
    if context.headers.get("x-jwt-token", "") != "secret":
        raise UnauthorizedError


class Rpc(AbstractRpc):
    def prepare_exception(self, raw_data, context, exc):
        if isinstance(exc, ValidationError):
            return {
                "code": -32600,
                "message": "Validation error",
                "details": exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=True,
                ),
            }
        if isinstance(exc, UnauthorizedError):
            return {
                "code": -32000,
                "message": "unauthorized",
            }
        return {
            "code": -1,
            "message": "Internal server error",
        }


############# PROCEDURE #########################
class UserParams(BaseModel):
    uid: constr(min_length=1)
    start_ts: datetime
    dob: date


class AccessLevel(Enum):
    BASIC = 1
    ADMIN = 2


class UserDetails(BaseModel):
    uid: str
    name: str
    start_ts: datetime
    dob: date
    access_level: AccessLevel


class GetUser(AbstractProcedure):
    PERMISSIONS = (is_authorized,)

    def call(self, in_: UserParams, context) -> UserDetails:
        return UserDetails(
            name="John", access_level=AccessLevel.BASIC, **in_.dict()
        )


rpc = Rpc().register(GetUser)

############# EXPORTING TS ######################
TsExporter(rpc, RpcContext(url="http://backend:8000")).write("src/out.ts")


app = FastAPI()


@app.post("/")
async def read_root(request: Request):
    return rpc.call(await request.body(), request)
