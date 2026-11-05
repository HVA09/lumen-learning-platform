import { useState } from "react";
import { useTranslation } from "react-i18next";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import LanguageToggle from "../components/LanguageToggle";
import i18n from "../i18n";
import useDirection from "./useDirection";

function DirectionHarness() {
  const [lang, setLang] = useState("ar");
  const { i18n: translation } = useTranslation();

  useDirection();

  const changeLanguage = (nextLang) => {
    setLang(nextLang);
    void translation.changeLanguage(nextLang);
  };

  return <LanguageToggle lang={lang} setLang={changeLanguage} />;
}

describe("useDirection", () => {
  beforeEach(async () => {
    await act(async () => {
      await i18n.changeLanguage("ar");
    });
  });

  it("switches the document between RTL Arabic and LTR English", async () => {
    const user = userEvent.setup();
    render(<DirectionHarness />);

    await waitFor(() => {
      expect(document.documentElement).toHaveAttribute("dir", "rtl");
      expect(document.documentElement).toHaveAttribute("lang", "ar");
    });

    await user.click(screen.getByRole("button", { name: "English" }));

    await waitFor(() => {
      expect(document.documentElement).toHaveAttribute("dir", "ltr");
      expect(document.documentElement).toHaveAttribute("lang", "en");
      expect(screen.getByText("Language")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "العربية" }));

    await waitFor(() => {
      expect(document.documentElement).toHaveAttribute("dir", "rtl");
      expect(document.documentElement).toHaveAttribute("lang", "ar");
      expect(screen.getByText("اللغة")).toBeInTheDocument();
    });
  });
});
