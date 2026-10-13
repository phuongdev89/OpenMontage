import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const listeners = new Map();
globalThis.document = {
  hidden: false,
  addEventListener: (type, fn) => listeners.set(type, fn),
  removeEventListener: type => listeners.delete(type),
};
globalThis.EventSource = class { close() { this.closed = true; } };
const code = await readFile(new URL('../../backlot/ui/lib.js', import.meta.url), 'utf8');
const { subscribe } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let calls = 0, active = 0, maxActive = 0;
let release;
const source = subscribe('/events', async () => {
  calls++; active++; maxActive = Math.max(active, maxActive);
  if (calls === 1) await new Promise(resolve => { release = resolve; });
  active--;
});
const event = type => source.onmessage({ data: JSON.stringify({ type }) });
event('hello');
await sleep(300);
assert.equal(calls, 1, 'hello must refetch after reconnect');
event('change'); event('change');
await sleep(300);
release();
await sleep(20);
assert.equal(calls, 2, 'a change during a pending fetch must cause a trailing fetch');
assert.equal(maxActive, 1, 'refreshes must not race');
event('heartbeat');
await sleep(300);
assert.equal(calls, 2, 'heartbeat must not redraw');
listeners.get('visibilitychange')();
await sleep(300);
assert.equal(calls, 3, 'returning to a tab must reconcile');
event('change');
source.close();
await sleep(300);
assert.equal(calls, 3, 'close must cancel refresh timers');
assert.equal(listeners.size, 0);
console.log('PASS: reconnect, bursts, single flight, visibility, cleanup');
