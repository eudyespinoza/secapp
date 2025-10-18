import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display homepage', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('SecureApprove');
    await expect(page.locator('text=Enterprise-grade passwordless')).toBeVisible();
  });

  test('should navigate to login page', async ({ page }) => {
    await page.click('text=Sign In');
    await expect(page).toHaveURL('/auth/login');
    await expect(page.locator('h1')).toContainText('Sign In');
  });

  test('should navigate to registration page', async ({ page }) => {
    await page.click('text=Get Started');
    await expect(page).toHaveURL('/auth/register');
    await expect(page.locator('h1')).toContainText('Create Account');
  });

  test('should validate email format on registration', async ({ page }) => {
    await page.goto('/auth/register');
    
    await page.fill('input[name="email"]', 'invalid-email');
    await page.fill('input[name="firstName"]', 'John');
    await page.fill('input[name="lastName"]', 'Doe');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('text=Invalid email')).toBeVisible();
  });

  test('should show WebAuthn registration flow', async ({ page }) => {
    await page.goto('/auth/register');
    
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="firstName"]', 'John');
    await page.fill('input[name="lastName"]', 'Doe');
    
    // Mock WebAuthn API
    await page.evaluate(() => {
      // @ts-ignore
      window.navigator.credentials = {
        create: async () => ({
          id: 'mock-credential-id',
          rawId: new ArrayBuffer(32),
          response: {
            attestationObject: new ArrayBuffer(256),
            clientDataJSON: new ArrayBuffer(128),
          },
          type: 'public-key',
        }),
      };
    });
    
    await page.click('button[type="submit"]');
    
    // Should show WebAuthn prompt
    await expect(page.locator('text=Register Biometric')).toBeVisible();
  });
});

test.describe('Approval Request Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-token');
    });
  });

  test('should display dashboard when authenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should create new approval request', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('text=New Request');
    
    await expect(page).toHaveURL('/requests/new');
    
    await page.fill('input[name="title"]', 'Test Approval Request');
    await page.fill('textarea[name="description"]', 'This is a test request');
    await page.selectOption('select[name="priority"]', 'high');
    
    await page.click('button[type="submit"]');
    
    await expect(page.locator('text=Request created')).toBeVisible();
  });

  test('should approve request with WebAuthn', async ({ page }) => {
    await page.goto('/requests/123');
    
    // Mock WebAuthn authentication
    await page.evaluate(() => {
      // @ts-ignore
      window.navigator.credentials = {
        get: async () => ({
          id: 'mock-credential-id',
          rawId: new ArrayBuffer(32),
          response: {
            authenticatorData: new ArrayBuffer(37),
            clientDataJSON: new ArrayBuffer(128),
            signature: new ArrayBuffer(64),
          },
          type: 'public-key',
        }),
      };
    });
    
    await page.click('button:has-text("Approve")');
    
    await expect(page.locator('text=Request approved')).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have no accessibility violations on homepage', async ({ page }) => {
    await page.goto('/');
    
    // Check for basic accessibility
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    
    // Check for alt text on images
    const images = await page.locator('img').all();
    for (const img of images) {
      await expect(img).toHaveAttribute('alt');
    }
    
    // Check for proper heading hierarchy
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/');
    
    // Tab through focusable elements
    await page.keyboard.press('Tab');
    let focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT']).toContain(focused || '');
  });
});

test.describe('Performance', () => {
  test('should load homepage within 2 seconds', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(2000);
  });

  test('should have optimized images', async ({ page }) => {
    await page.goto('/');
    
    const images = await page.locator('img').all();
    for (const img of images) {
      const src = await img.getAttribute('src');
      // Next.js should optimize images
      expect(src).toContain('/_next/image') || expect(src).toContain('.svg');
    }
  });
});
