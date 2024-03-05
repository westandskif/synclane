import {
    callGetUsers,
    callGetUser,
    AccessLevel,
    rpcConfig,
} from "../src/out";

test("API client", async () => {
    rpcConfig.url = "http://backend:8000";
    let created_after = new Date();
    let dob_after = new Date(2000, 0, 1);

    // example of adding authentication
    // init is fetch options - https://developer.mozilla.org/en-US/docs/Web/API/fetch
    rpcConfig.initFetch = (init: RequestInit) => {
        let headers = (init.headers = init.headers || {});
        headers["X-Jwt-Token"] = "secret";
        return init;
    };

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
    expect(
        callGetUser({ uid: "4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07" }).$promise,
    ).resolves.toEqual({
        uid: "4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07",
        name: "John",
        created: new Date(created_after.getTimezoneOffset() * 60000),
        dob: new Date(1970, 0, 1),
        access_level: AccessLevel.BASIC,
    }
    );

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
});
