import { chromium } from '@playwright/test';

const config = {
  url: 'http://192.168.2.13/dashboard/branch-conflict',
  username: 'Administrator',
  password: 'Ali@sukaIs1BigwoguaCyancook@sukaIs1Bigwogua'
};

async function login(page) {
  await page.goto(config.url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  const hasPasswordField = await page.locator('input[type="password"]').count() > 0;
  if (hasPasswordField) {
    await page.locator('input[type="text"]').first().fill(config.username);
    await page.locator('input[type="password"]').fill(config.password);
    const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
    if (await submitButton.count() > 0) {
      await submitButton.click();
    } else {
      await page.locator('input[type="password"]').press('Enter');
    }
    await page.waitForTimeout(3000);
  }
}

async function getBranchStatus(page) {
  await page.waitForSelector('table', { timeout: 10000 });

  const rows = await page.locator('table tbody tr').all();
  const results = [];

  for (const row of rows) {
    const cells = await row.locator('td').allTextContents();
    if (cells.length > 0) {
      results.push({
        branch: cells[1]?.trim() || '',
        autoMerge: cells[2]?.trim() || '',
        clientBuild: cells[3]?.trim() || '',
        clientData: cells[4]?.trim() || '',
        serverBuild: cells[5]?.trim() || '',
        serverData: cells[6]?.trim() || '',
        editorSmoke: cells[7]?.trim() || '',
        status: cells[8]?.trim() || ''
      });
    }
  }

  return results;
}

async function resolveConflict(page, branchName) {
  const rows = await page.locator('table tbody tr').all();

  for (const row of rows) {
    const text = await row.textContent();
    if (text.includes(branchName)) {
      const resolveButton = row.locator('button:has-text("解决"), button:has-text("Resolve")');
      if (await resolveButton.count() > 0) {
        await resolveButton.click();
        await page.waitForTimeout(2000);
        return { success: true, message: `已触发 ${branchName} 的冲突解决` };
      }
    }
  }

  return { success: false, message: `未找到 ${branchName} 的冲突解决按钮` };
}

export { login, getBranchStatus, resolveConflict };
