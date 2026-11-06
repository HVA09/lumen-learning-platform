import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  request: vi.fn(),
}));

vi.mock("./api", () => ({ default: api }));

import { changePassword, deleteAccount, getCurrentUser, updateProfile } from "./usersApi";

const previousPassword = "previous-fixture";
const nextPassword = "replacement-fixture";

describe("users API adapters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the current user's profile", async () => {
    const user = { id: 3, email: "learner@example.com" };
    api.get.mockResolvedValueOnce({ data: user });

    await expect(getCurrentUser()).resolves.toEqual(user);
    expect(api.get).toHaveBeenCalledWith("/users/me");
  });

  it("updates the current user's profile fields", async () => {
    const fields = { display_name: "Learner" };
    const updated = { id: 3, display_name: "Learner" };
    api.patch.mockResolvedValueOnce({ data: updated });

    await expect(updateProfile(fields)).resolves.toEqual(updated);
    expect(api.patch).toHaveBeenCalledWith("/users/me", fields);
  });

  it("sends password changes using the API's snake-case fields", async () => {
    const result = { updated: true };
    api.post.mockResolvedValueOnce({ data: result });

    await expect(changePassword(previousPassword, nextPassword)).resolves.toEqual(result);
    expect(api.post).toHaveBeenCalledWith("/users/me/change-password", {
      current_password: previousPassword,
      new_password: nextPassword,
    });
  });

  it("deletes the account through a DELETE request with the password body", async () => {
    api.request.mockResolvedValueOnce({});

    await expect(deleteAccount("ConfirmPass123")).resolves.toBeUndefined();
    expect(api.request).toHaveBeenCalledWith({
      method: "DELETE",
      url: "/users/me",
      data: { password: "ConfirmPass123" },
    });
  });
});
