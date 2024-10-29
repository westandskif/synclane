// --8<-- [start:imports]
import {
    callGetUsers,
    callGetUser,
    AccessLevel,
    rpcConfig,
} from "../src/out";
// --8<-- [end:imports]

test("API client", async () => {
    rpcConfig.url = "http://backend-missing:8000";
    console.log("TESTING: ", rpcConfig.url);
    expect(
        callGetUsers({ page: 1, created_after: new Date(), dob_after: new Date() }).$promise.then(() => 1, () => 2),
    ).resolves.toEqual(2);
    rpcConfig.url = undefined;

    for (let backend of [
        { url: "http://backend-django:8000", framework: "django" },
        { url: "http://backend-fastapi:8000", framework: "fastapi" }
    ]) {
        console.log("TESTING: ", backend);

        let created_after = new Date();
        let dob_after = new Date(2000, 0, 1);

        // --8<-- [start:rpc_config]

        rpcConfig.url = backend.url;

        // example of adding authentication
        // init is fetch options - https://developer.mozilla.org/en-US/docs/Web/API/fetch
        rpcConfig.initFetch = (init: RequestInit) => {
            let headers = (init.headers = init.headers || {});
            headers["X-Jwt-Token"] = "secret";
            return init;
        };
        // --8<-- [end:rpc_config]

        expect(
            callGetUsers({ page: 1, created_after: created_after, dob_after: dob_after }).$promise,
        ).resolves.toEqual({
            has_next: true, has_prev: false, data: [{
                uid: "4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07",
                name: "John",
                created: created_after,
                dob: dob_after,
                access_level: AccessLevel.BASIC,
            }]
        });
        // --8<-- [start:get_user]
        expect(
            callGetUser({ uid: "4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07" }).$promise,
        ).resolves.toEqual({
            uid: "4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07",
            name: "John",
            created: new Date(new Date(0).getTimezoneOffset() * 60000),
            dob: new Date(1970, 0, 1),
            access_level: AccessLevel.BASIC,
        });
        // --8<-- [end:get_user]

        // validation error
        expect(
            callGetUsers({ page: 0, created_after: created_after, dob_after: dob_after }).$promise,
        ).rejects.toEqual({
            code: -32600,
            message: "Validation error",
            details: [
                {
                    type: "greater_than",
                    msg: "Input should be greater than 0",
                    input: 0,
                    loc: ["page"],
                },
            ],
        });

        // breaking authentication
        rpcConfig.initFetch = (init: RequestInit) => {
            let headers = (init.headers = init.headers || {});
            headers["X-Jwt-Token"] = "secret-bad";
            return init;
        };
        expect(
            callGetUsers({ page: 1, created_after: created_after, dob_after: dob_after }).$promise,
        ).rejects.toEqual({ code: -32000, message: "unauthorized" });
    }
});
