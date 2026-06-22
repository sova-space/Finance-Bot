import http from 'node:http';
import { URL } from 'node:url';

const publicPort = Number(process.env.PORT || 8080);
const financeTarget = process.env.FINANCE_API_TARGET || 'http://127.0.0.1:9100';
const hermesTarget = process.env.HERMES_DASHBOARD_TARGET || 'http://127.0.0.1:9121';

const financePrefixes = [
  '/app',
  '/accounts',
  '/budgets',
  '/buy-list',
  '/debts',
  '/forecast',
  '/goals',
  '/health',
  '/income',
  '/pockets',
  '/recurring',
  '/sync',
  '/transactions',
  '/trips',
  '/fx',
  '/bot',
  '/docs',
  '/redoc',
  '/openapi.json',
];

function redirect(res, location) {
  res.writeHead(302, { Location: location });
  res.end();
}

function proxy(req, res, targetBase, options = {}) {
  const incomingUrl = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
  let path = incomingUrl.pathname + incomingUrl.search;
  if (options.stripPrefix && incomingUrl.pathname.startsWith(options.stripPrefix)) {
    const strippedPath = incomingUrl.pathname.slice(options.stripPrefix.length) || '/';
    path = strippedPath + incomingUrl.search;
  }

  const target = new URL(path, targetBase);
  const headers = { ...req.headers, host: target.host };
  if (options.forwardedPrefix) {
    headers['x-forwarded-prefix'] = options.forwardedPrefix;
  }

  const proxyReq = http.request(
    target,
    {
      method: req.method,
      headers,
    },
    (proxyRes) => {
      const responseHeaders = { ...proxyRes.headers };
      if (responseHeaders.location && options.rewriteLocationPrefix) {
        const location = String(responseHeaders.location);
        if (location.startsWith('/')) {
          responseHeaders.location = `${options.rewriteLocationPrefix}${location}`;
        }
      }
      res.writeHead(proxyRes.statusCode || 502, responseHeaders);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end(`Proxy error: ${error.message}\n`);
  });

  req.pipe(proxyReq);
}

function isFinancePath(pathname) {
  return financePrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname;

  if (pathname === '/') return redirect(res, '/app');
  if (pathname === '/chat') return redirect(res, '/hermes/chat');
  if (pathname === '/sessions') return redirect(res, '/hermes/sessions');

  if (pathname === '/hermes') return redirect(res, '/hermes/');
  if (pathname.startsWith('/hermes/')) {
    return proxy(req, res, hermesTarget, {
      stripPrefix: '/hermes',
      forwardedPrefix: '/hermes',
      rewriteLocationPrefix: '/hermes',
    });
  }

  if (isFinancePath(pathname)) {
    return proxy(req, res, financeTarget);
  }

  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('Not found\n');
});

server.listen(publicPort, '0.0.0.0', () => {
  console.log(`Finance route server listening on 0.0.0.0:${publicPort}`);
  console.log(`Finance UI/API target: ${financeTarget}`);
  console.log(`Hermes Dashboard target: ${hermesTarget}`);
});
