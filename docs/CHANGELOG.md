## 0.6.1 (2024-12-15)

 - turned functions to arrow functions in the generated ts client

## 0.6.0 (2024-11-20)

 - added support for python's typing.Literal

## 0.5.0 (2024-11-19)

 - added support for ts optional fields (with default value on py side)

## 0.4.0 (2024-11-13)

 - added `UUID` support on py-side

## 0.3.0 (2024-11-13)

- added `setHeaders(headersInit: HeadersInit, headersToSet: Record<string, string>)` to ts client
- added `readResponse?: (response: Response) => void;` to `RpcConfig`

## 0.2.2 (2024-10-29)

- handled connection error properly (as promise rejection)


## 0.2.0 (2024-03-17)

**Incompatible changes**

- changed `rpc.call` and `rpc.call_async` to return bytes instead of python
  dicts/lists


## 0.1.0

Initial version.
