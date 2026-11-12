import { z } from "zod";

export const TokenRefreshSchema = z.object({
  access_token: z.string(),
  expires_in: z.number(),
});

export const SessionSchema = z.object({
  username: z.string(),
  role: z.string(),
  display_name: z.string(),
  email: z.string().optional(),
  exp: z.number().optional(),
});
