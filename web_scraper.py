import asyncio
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError

async def get_page_data(page):
    """从当前页面提取表格数据"""
    data = []
    table_xpath = "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div[1]/div/div[2]/table"
    
    try:
        await page.wait_for_selector(f"xpath={table_xpath}", timeout=10000)
        rows = await page.query_selector_all(f"xpath={table_xpath}/tbody/tr")
        
        for row in rows:
            cols = await row.query_selector_all("td")
            if len(cols) < 5:
                continue

            rank = await cols[0].inner_text()
            
            # 根据用户提供的精确XPath进行解析
            school_name_element = await cols[1].query_selector("xpath=./div/div[2]/div[1]/div/div/span")
            school_name = await school_name_element.inner_text() if school_name_element else ""
            
            school_prop_element = await cols[1].query_selector("xpath=./div/div[2]/p")
            school_prop = await school_prop_element.inner_text() if school_prop_element else ""

            city = await cols[2].inner_text()
            school_type = await cols[3].inner_text()
            total_score = await cols[4].inner_text()
            
            data.append({
                "排名": rank.strip(),
                "学校名称": school_name.strip(),
                "省市": city.strip(),
                "类型": school_type.strip(),
                "总分": total_score.strip(),
                "学校性质": school_prop.strip(),
            })
    except TimeoutError:
        print("在当前页面没有找到表格。")
    
    return data

async def main():
    """主函数，用于启动浏览器、导航和抓取数据"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Reverting to headless for efficiency
        page = await browser.new_page()
        
        url = "https://www.shanghairanking.cn/rankings/bcur/202510"
        print(f"正在访问: {url}")
        try:
            await page.goto(url, timeout=60000)
        except TimeoutError:
            print("页面加载超时。")
            await browser.close()
            return

        all_data = []
        page_num = 1

        while True:
            print(f"正在抓取第 {page_num} 页...")
            page_data = await get_page_data(page)
            if not page_data:
                print(f"在第 {page_num} 页没有获取到数据，抓取结束。")
                break
            
            all_data.extend(page_data)
            
            # 查找下一页按钮
            next_button_xpath = "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div[1]/div/ul/li[contains(@class, 'ant-pagination-next')]"
            next_button = await page.query_selector(f"xpath={next_button_xpath}")
            
            if not next_button:
                print("未找到'下一页'按钮，抓取结束。")
                break

            is_disabled = "ant-pagination-disabled" in (await next_button.get_attribute("class") or "")
            if is_disabled:
                print("到达最后一页，抓取结束。")
                break
            
            await next_button.click()
            # 等待页面跳转或内容加载
            await page.wait_for_timeout(2000) # 简单等待，也可以换成更可靠的等待网络或特定元素的方式
            page_num += 1

        print(f"总共抓取了 {len(all_data)} 条数据。")

        if all_data:
            df = pd.DataFrame(all_data)
            output_file = "university_rankings_2025.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"数据已成功保存到 {output_file}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 