import logging
from datetime import date, datetime
from enum import Enum
from typing import Generic, List, Optional, TypeVar

from fastapi import FastAPI, Request
from pydantic import BaseModel, ValidationError, conint

from synclane import (
    AbstractAsyncProcedure,
    AbstractAsyncRpc,
    AbstractProcedure,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


############################################################
############# DEFINE PROCEDURES ############################


class GetObjectParams(BaseModel):
    uid: str


class AccessLevel(Enum):
    BASIC = 1
    ADMIN = 2


class UserDetails(BaseModel):
    uid: str
    name: str
    created: datetime
    dob: date
    access_level: AccessLevel


def is_authorized(context):
    # context can be anything; let it be a request here
    if context.headers.get("x-jwt-token", "") != "secret":
        raise UnauthorizedError


class GetUser(AbstractProcedure):
    PERMISSIONS = (is_authorized,)

    def call(self, in_: GetObjectParams, context) -> UserDetails:
        return UserDetails(
            uid=in_.uid,
            name="John",
            created=datetime.fromtimestamp(0),
            dob=date(1970, 1, 1),
            access_level=AccessLevel.BASIC,
        )


# LET'S ADD FAKE PAGINATION AND MAKE IT ASYNC JUST FOR EXAMPLE
class Params(BaseModel):
    page: conint(gt=0)
    created_after: Optional[datetime] = None
    dob_after: Optional[date] = None


T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    has_next: bool
    has_prev: bool
    data: List[T]


class GetUsers(AbstractAsyncProcedure):
    PERMISSIONS = (is_authorized,)

    async def call_async(self, in_: Params, context) -> Paginated[UserDetails]:
        return {
            "has_next": True,
            "has_prev": False,
            "data": [
                UserDetails(
                    uid="4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07",
                    name="John",
                    created=in_.created_after,
                    dob=in_.dob_after,
                    access_level=AccessLevel.BASIC,
                )
            ],
        }


############################################################
######## DEFINE RPC AND REGISTER PROCEDURES ################
class UnauthorizedError(Exception):
    pass


class Rpc(AbstractAsyncRpc):
    def prepare_exception(self, raw_data, context, exc):
        # it can be anything, but the below tries to adhere to
        # https://www.jsonrpc.org/specification
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
        logger.exception(exc)
        return {
            "code": -1,
            "message": "Internal server error",
        }


rpc = Rpc().register(GetUsers, GetUser)


############################################################
############# DUMP TS ######################################
rpc.ts_dump("src/out.ts")

############################################################
############# CONNECT TO API ENDPOINT ######################
app = FastAPI()


@app.post("/")
async def read_root(request: Request):
    # for sync version of rpc:
    # >>> rpc.call(await request.body(), request)

    return await rpc.call_async(
        await request.body(),  # always full body as is
        request,  # anything to be passed to procedures as context
    )
