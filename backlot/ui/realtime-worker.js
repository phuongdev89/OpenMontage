// One SSE socket for every Backlot tab on this origin, including Library.
const clients = new Map();
let source = null;

function stopIfUnused() {
  if (!clients.size && source) {
    source.close();
    source = null;
  }
}

function send(port, data) {
  try { port.postMessage(data); }
  catch { clients.delete(port); }
}

self.onconnect = event => {
  const port = event.ports[0];
  port.onmessage = event => {
    if (event.data === 'leave') {
      clients.delete(port);
      stopIfUnused();
      return;
    }
    clients.set(port, Date.now());
    if (!source) {
      source = new EventSource('/api/library/events');
      source.onmessage = event => {
        for (const client of clients.keys()) send(client, event.data);
        stopIfUnused();
      };
    }
    if (event.data === 'join') send(port, '{"type":"hello"}');
  };
  port.start();
};

// pagehide handles normal navigation; leases clean up crashed/closed tabs.
setInterval(() => {
  const cutoff = Date.now() - 120000;
  for (const [port, seen] of clients) {
    if (seen < cutoff) { clients.delete(port); port.close(); }
  }
  stopIfUnused();
}, 30000);
