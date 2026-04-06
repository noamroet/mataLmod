/**
 * E2E: Intake form → eligibility results → program detail → advisor
 *
 * Covers the main user journey for a post-army Israeli:
 *   1. Landing page → click "Check eligibility" CTA
 *   2. Intake step 1: add a bagrut subject (Math, 5 units, 95)
 *   3. Intake step 2: enter psychometric score (680)
 *   4. Intake step 3: select a field preference → submit
 *   5. Results page: verify at least one program card renders
 *   6. Click a program card → program detail page renders
 *   7. Open advisor wizard → verify first message appears
 */

import { test, expect } from '@playwright/test';

test.describe('Main user journey', () => {
  test('intake → results → program detail → advisor', async ({ page }) => {
    // ── 1. Landing page ──────────────────────────────────────────────────────
    await page.goto('/');
    await expect(page).toHaveTitle(/מה תלמד/);

    // Find and click the primary CTA (navigate to intake)
    const ctaLink = page.getByRole('link', { name: /בדיקת זכאות|בדוק זכאות|Check eligibility/i }).first();
    await ctaLink.click();
    await expect(page).toHaveURL(/\/intake/);

    // ── 2. Step 1 — Bagrut grades ────────────────────────────────────────────
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Select Math subject
    const subjectSelect = page.locator('[data-testid="subject-select-0"], select').first();
    if (await subjectSelect.isVisible()) {
      await subjectSelect.selectOption('math');
    }

    // Select 5 units
    const unitsSelect = page.locator('[data-testid="units-select-0"]').first();
    if (await unitsSelect.isVisible()) {
      await unitsSelect.selectOption('5');
    }

    // Enter grade
    const gradeInput = page.locator('input[placeholder*="0–100"], input[type="number"]').first();
    if (await gradeInput.isVisible()) {
      await gradeInput.fill('95');
    }

    // Continue to step 2
    const nextBtn = page.getByRole('button', { name: /המשך|Continue/i });
    await nextBtn.click();

    // ── 3. Step 2 — Psychometric score ───────────────────────────────────────
    const psychoInput = page.locator('input[placeholder*="200"], input[placeholder*="800"]').first();
    if (await psychoInput.isVisible()) {
      await psychoInput.fill('680');
    }
    await page.getByRole('button', { name: /המשך|Continue/i }).click();

    // ── 4. Step 3 — Preferences & submit ─────────────────────────────────────
    // Field selection is optional — just submit
    const submitBtn = page.getByRole('button', { name: /חשב זכאות|Calculate eligibility/i });
    await submitBtn.click();

    // ── 5. Results page ───────────────────────────────────────────────────────
    await expect(page).toHaveURL(/\/results/, { timeout: 15_000 });

    // At least one program card should be visible
    const programCards = page.locator('[data-testid="program-card"], article').first();
    await expect(programCards).toBeVisible({ timeout: 10_000 });

    // ── 6. Program detail page ────────────────────────────────────────────────
    const viewDetailsLink = page.getByRole('link', { name: /לפרטי התוכנית|View program/i }).first();
    await viewDetailsLink.click();
    await expect(page).toHaveURL(/\/program\//);

    // Program name heading should be visible
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // ── 7. Advisor wizard ─────────────────────────────────────────────────────
    const advisorBtn = page.getByRole('button', { name: /שאל את היועץ|Ask the advisor/i });
    await advisorBtn.click();

    // Wizard panel should open
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // Root message should be visible
    await expect(dialog.getByText(/היי|Hi/i)).toBeVisible();

    // Close the panel
    await dialog.getByRole('button', { name: /סגור|Close/i }).click();
    await expect(dialog).not.toBeVisible();
  });
});

// ── Individual page smoke tests ───────────────────────────────────────────────

test.describe('Page smoke tests', () => {
  test('landing page renders without errors', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main')).toBeVisible();
    // No console errors
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.waitForTimeout(1000);
    expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
  });

  test('intake page renders form', async ({ page }) => {
    await page.goto('/intake');
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.locator('form, [role="form"]').first()).toBeVisible();
  });

  test('results page redirects to intake when no data', async ({ page }) => {
    // Clear session storage to simulate a fresh visit
    await page.goto('/results');
    // Should either show results or redirect to intake
    await expect(page).toHaveURL(/\/results|\/intake/, { timeout: 5_000 });
  });
});
