"use client";

import {
  ThemeProvider as NextThemesProvider,
  type ThemeProviderProps,
} from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute={["class", "data-theme"]}
      defaultTheme="light"
      disableTransitionOnChange
      enableSystem
      storageKey="prototipo-psp-theme"
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
