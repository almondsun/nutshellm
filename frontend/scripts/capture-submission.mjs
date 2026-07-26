import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright-core";

const baseUrl = process.argv[2] || "http://127.0.0.1:8012";
const outputDir = resolve(process.argv[3] || "../docs/screenshots");
await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
  headless: true,
});

try {
  const page = await browser.newPage({
    viewport: { width: 1800, height: 1200 },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator(".run-button").first().click();
  await page.locator(".results").waitFor({ state: "visible", timeout: 120_000 });
  await page.locator(".recharts-wrapper").waitFor({
    state: "visible",
    timeout: 15_000,
  });

  await page.locator(".run-section").evaluate((element) => {
    window.scrollTo({ top: element.offsetTop, behavior: "instant" });
  });
  await page.screenshot({
    path: resolve(outputDir, "02-result-evidence.png"),
    animations: "disabled",
  });

  const firstDecision = page.locator(".segments details").first();
  await firstDecision.evaluate((element) => {
    element.open = true;
  });
  await page.locator(".segments").evaluate((element) => {
    const top = element.getBoundingClientRect().top + window.scrollY - 30;
    window.scrollTo({ top, behavior: "instant" });
  });
  await page.screenshot({
    path: resolve(outputDir, "03-context-decisions.png"),
    animations: "disabled",
  });
} finally {
  await browser.close();
}
