import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def main():
    pdf_url = "https://www.commbank.com.au/content/dam/commbank/about-us/shareholders/pdfs/results/fy24/cba-annual-report-2024.pdf"

    # 不需要浏览器，禁用 headless browser 即可
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        download_pdfs=True,
        extract_pdf_text=True,
        output_format="md"
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(pdf_url, config=run_config)
        print(result.markdown.raw_markdown[:1000])  # 打印前1000字，避免太长

asyncio.run(main())
