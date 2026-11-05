import { type NextRequest, NextResponse } from "next/server";

// O backend grava o token nesse cookie. Este front só checa a presença para
// redirecionar; a validação de verdade acontece no backend.
const ACCESS_COOKIE = "access_token";
const LEGACY_COOKIE = "dashboard_auth_token";

const PUBLIC_ROUTES = ["/login"] as const;
const PUBLIC_PREFIXES = ["/_next", "/favicon", "/static", "/images"] as const;

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_ROUTES.some((route) => pathname === route)) return true;
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  const token =
    request.cookies.get(ACCESS_COOKIE)?.value ??
    request.cookies.get(LEGACY_COOKIE)?.value;

  if (!token) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json(
        { error: "Unauthorized", message: "Missing or invalid authorization" },
        { status: 401 },
      );
    }
    const loginUrl = new URL("/login", request.url);
    // Preserva caminho e query para o usuário voltar à mesma tela após o login.
    const search = request.nextUrl.search;
    const fullPath = search ? `${pathname}${search}` : pathname;
    // Só caminhos relativos internos, para evitar open redirect.
    if (fullPath.startsWith("/") && !fullPath.startsWith("//")) {
      loginUrl.searchParams.set("callbackUrl", fullPath);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
