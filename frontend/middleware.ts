import createMiddleware from 'next-intl/middleware';
import { NextResponse, NextRequest } from 'next/server';

const intlMiddleware = createMiddleware({
  locales: ['es', 'en', 'pt-BR'],
  defaultLocale: 'es',
  localeDetection: true,
  localePrefix: 'always'
});

export default function middleware(req: NextRequest) {
  // Force absolute redirect from 127.0.0.1 -> localhost (WebAuthn RP ID must be 'localhost')
  const hostHeader = req.headers.get('host') || '';
  const host = hostHeader.split(':')[0];
  if (host === '127.0.0.1') {
    const url = req.nextUrl;
    const abs = `http://localhost:3000${url.pathname}${url.search}`;
    const html = `<!doctype html><html><head><meta http-equiv="refresh" content="0; url=${abs}" /></head><body><script>location.replace(${JSON.stringify(abs)});</script></body></html>`;
    return new NextResponse(html, {
      status: 200,
      headers: { 'content-type': 'text/html; charset=utf-8' }
    });
  }
  return (intlMiddleware as any)(req);
}

export const config = {
  // Exclude api, _next and any static file with an extension from locale handling
  matcher: [
    '/',
    // Use supported negative lookahead pattern for Next.js route matchers
    '/((?!api|_next|_vercel|.*\\..*).*)'
  ]
};
