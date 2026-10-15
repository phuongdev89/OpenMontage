import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const feeds = [];
const timers = [];
const context = {
  self: {}, Date, Map,
  setInterval: fn => timers.push(fn),
  EventSource: class {
    constructor(url) { this.url = url; feeds.push(this); }
    close() { this.closed = true; }
  },
};
vm.runInNewContext(await readFile(new URL('../../backlot/ui/realtime-worker.js', import.meta.url), 'utf8'), context);
function client() {
  const messages = [];
  const port = { postMessage: value => messages.push(value), start() {}, close() {} };
  context.self.onconnect({ ports: [port] });
  port.onmessage({ data: 'join' });
  return { port, messages };
}
const clients = Array.from({ length: 10 }, client);
assert.equal(feeds.length, 1, 'ten tabs must reserve only one SSE socket');
assert.equal(feeds[0].url, '/api/library/events');
const changed = '{"type":"change","project_id":"Film"}';
feeds[0].onmessage({ data: changed });
for (const c of clients) assert.equal(c.messages.at(-1), changed);
for (const c of clients.slice(0, -1)) c.port.onmessage({ data: 'leave' });
assert.ok(!feeds[0].closed, 'remaining tab still receives updates');
clients.at(-1).port.onmessage({ data: 'leave' });
assert.ok(feeds[0].closed, 'last tab releases SSE');
const next = client();
assert.equal(feeds.length, 2, 'opening another tab reconnects');
context.Date = { now: () => Date.now() + 130000 };
timers[0]();
assert.ok(feeds[1].closed, 'expired leases release crashed tabs');
console.log('PASS: ten-tab sharing, broadcast, close, reconnect, expired lease');
