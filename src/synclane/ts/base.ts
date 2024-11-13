const ANY_DATE: Date = new Date();
const TIMEZONE_OFFSET_IN_MS: number = ANY_DATE.getTimezoneOffset() * 60000;

export function strToDate(d: string): Date {
    let dt = new Date(d);
    return new Date(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate());
}
export function dateToStr(d: Date): string {
    return new Date(d.getTime() - TIMEZONE_OFFSET_IN_MS)
        .toISOString()
        .split("T")[0];
}
export function setHeaders(
    headersInit: HeadersInit,
    headersToSet: Record<string, string>,
) {
    let headers = headersInit;
    if (headers === undefined) {
        headers = headersToSet;
    } else if (headers instanceof Headers) {
        for (const name in headersToSet) {
            headers.set(name, headersToSet[name]);
        }
    } else if (Array.isArray(headers)) {
        for (const name in headersToSet) {
            headers.push([name, headersToSet[name]]);
        }
    } else {
        for (const name in headersToSet) {
            headers[name] = headersToSet[name];
        }
    }
}
interface RpcConfig {
    url?: string;
    initFetch?: (init: RequestInit) => RequestInit;
    readResponse?: (response: Response) => void;
}
export let rpcConfig: RpcConfig = {};

export class AbortableRequest<T> {
    public $promise: Promise<T>;
    private controller: AbortController;
    public abort() { this.controller.abort(); }

    constructor($promise: Promise<T>, controller: AbortController) {
        this.$promise = $promise;
        this.controller = controller;
    }
}
let REQUEST_COUNTER = 1;
function fetchAndPrepare<U>(
    init: RequestInit,
    primitiveToResult: (data: any) => U,
): Promise<U> {
    return new Promise((resolve, reject) => {
        if (rpcConfig.url === undefined) {
            return reject("rpcConfig.url is not initialized");
        }
        return fetch(rpcConfig.url, init)
            .then((response) => {
                if (rpcConfig.readResponse) {
                    rpcConfig.readResponse(response);
                }
                return response.json();
            })
            .then(
                (data) => {
                    if (data.result === undefined) {
                        reject(data.error);
                    } else {
                        resolve(primitiveToResult(data.result));
                    }
                },
                (err) => reject(err),
            );
    });
}
export function abortableFetch<T, U>(
    method: string,
    params: T,
    paramsToPrimitive: (params: T) => any,
    primitiveToResult: (data: any) => U,
): AbortableRequest<U> {
    let controller = new AbortController();
    let headers = new Headers();
    headers.set("Accept", "application/json");
    headers.set("Content-Type", "application/json;charset=UTF-8");
    let init: RequestInit = {
        method: "POST",
        headers: headers,
        signal: controller.signal,
        body: JSON.stringify({
            id: REQUEST_COUNTER++,
            method: method,
            params: paramsToPrimitive(params),
        }),
    };

    init.signal = controller.signal;
    if (rpcConfig && rpcConfig.initFetch !== undefined) {
        init = rpcConfig.initFetch(init);
    }

    return new AbortableRequest<U>(
        fetchAndPrepare(init, primitiveToResult),
        controller,
    );
}

// ===========================================================================
// ===========================================================================
