import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginScreen } from "../../src/components/LoginScreen";

describe("LoginScreen", () => {
  it("shows the documented demonstration credentials", () => {
    render(
      <LoginScreen
        demoEmail="demo@traceguard.local"
        demoPassword="Demo@123"
        backendHint="python -m uvicorn backend.app.main:app --port 8000"
        onSubmit={async () => {}}
      />,
    );

    expect(screen.getByLabelText("Email")).toHaveValue("demo@traceguard.local");
    expect(screen.getByLabelText("Password")).toHaveValue("Demo@123");
    expect(screen.getByText(/demo@traceguard\.local/)).toBeInTheDocument();
    expect(screen.getByText(/uvicorn/)).toBeInTheDocument();
  });

  it("submits the entered credentials", async () => {
    const onSubmit = vi.fn(async () => {});
    render(
      <LoginScreen
        demoEmail="demo@traceguard.local"
        demoPassword="Demo@123"
        backendHint="hint"
        onSubmit={onSubmit}
      />,
    );

    await userEvent.clear(screen.getByLabelText("Email"));
    await userEvent.type(screen.getByLabelText("Email"), "operator@example.local");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(onSubmit).toHaveBeenCalledWith("operator@example.local", "Demo@123");
  });

  it("reports a rejected sign-in", async () => {
    render(
      <LoginScreen
        demoEmail="demo@traceguard.local"
        demoPassword="Demo@123"
        backendHint="hint"
        onSubmit={async () => {
          throw new Error("401 Incorrect email or password.");
        }}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByTestId("login-error")).toHaveTextContent("Incorrect email or password");
  });
});
