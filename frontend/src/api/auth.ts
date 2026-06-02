import { request, setAuth, User } from "./client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }).then((res) => {
      setAuth(res.access_token, res.user);
      return res;
    }),
  me: () => request<User>("/auth/me"),
};
