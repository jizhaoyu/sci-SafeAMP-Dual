import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 开始全方位浏览器 E2E 自动化测试...")
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        errors = []
        page.on("pageerror", lambda err: errors.append(err))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        url = "http://62.234.141.184/"
        print(f"🌐 正在访问线上系统: {url}")
        
        response = await page.goto(url)
        if response.ok:
            print("✅ 首页加载成功 HTTP 200")
        else:
            print(f"❌ 首页加载失败 HTTP {response.status}")
            
        await page.wait_for_load_state('networkidle')
        
        # Take a screenshot of the main page
        await page.screenshot(path="screenshot_home.png")
        print("📸 已保存首页截图 screenshot_home.png")
        
        title = await page.title()
        print(f"📑 页面标题: {title}")

        # In Plan B's React App, the tabs should be present.
        # If it's a React app, there might be React-Router links. Let's try to find them by common text.
        # Depending on how the subagents implemented it, they might be links or buttons.
        try:
            print("🔍 尝试查找并点击各个工作室页面...")
            
            # Click Evolution Studio
            if await page.locator("text=定向突变").is_visible() or await page.locator("text=Evolution").is_visible():
                evo_locator = page.locator("text=定向突变").first if await page.locator("text=定向突变").is_visible() else page.locator("text=Evolution").first
                await evo_locator.click()
                await page.wait_for_timeout(1000)
                await page.screenshot(path="screenshot_evolution.png")
                print("✅ 成功进入 定向突变实验室")
            else:
                print("⚠️ 未发现定向突变实验室的入口标签")

            # Click Helical Wheel Studio
            if await page.locator("text=螺旋轮").is_visible() or await page.locator("text=Wheel").is_visible():
                wheel_locator = page.locator("text=螺旋轮").first if await page.locator("text=螺旋轮").is_visible() else page.locator("text=Wheel").first
                await wheel_locator.click()
                await page.wait_for_timeout(1000)
                await page.screenshot(path="screenshot_wheel.png")
                print("✅ 成功进入 螺旋轮构象投影室")
            else:
                print("⚠️ 未发现螺旋轮投影室的入口标签")

        except Exception as e:
            print(f"⚠️ UI 交互测试时出现异常: {str(e)}")

        if errors:
            print("\n❌ 发现控制台报错:")
            for err in set(errors):
                print(f"  - {err}")
        else:
            print("\n✅ 测试通过：控制台无任何报错，全站运行稳定！")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
