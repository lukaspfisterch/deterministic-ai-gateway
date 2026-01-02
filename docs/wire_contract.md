# Wire Contract Notes

## Tail Semantics

`GET /tail?since=<index>` streams events where `event.index > since`.

If the `Last-Event-Id` header is provided by the client, the server treats it as the effective `since` value.

Events are emitted as SSE envelopes:

- `id: <index>`
- `event: envelope`
- `data: <json>`

## Ingress Acknowledgement

`POST /ingress/intent` responds immediately after the INTENT is appended. The response is an acknowledgement and does not include execution output.
