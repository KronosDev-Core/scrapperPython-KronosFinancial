import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from datetime import datetime
from re import search
from prisma import Prisma
from prisma.enums import Status, BuyStatus
from prisma.models import Dividend, Stock
from json import dumps

date = datetime.now().strftime("%d-%m-%Y")

option = Options()
option.add_argument("--no-sandbox")
option.add_argument("--disable-gpu")
option.add_argument("--log-level=1")
option.add_experimental_option('excludeSwitches', ['enable-logging'])


async def main():
    db = Prisma(auto_register=True)
    await db.connect()

    await Dividend.prisma().update_many(
        data={
            'status': Status.NOT_CHANGED
        },
        where={
            'status': {
                'not': Status.NOT_CHANGED
            }
        }
    )

    await Stock.prisma().update_many(
        data={
            'status': Status.NOT_CHANGED
        },
        where={
            'status': {
                'not': Status.NOT_CHANGED
            }
        }
    )

    counter: dict[str, int] = {
        'stock': {
            'new': 0,
            'updated': 0,
            'notChanged': 0,
        },
        'dividend': {
            'new': 0,
            'updated': 0,
            'notChanged': 0,
        }
    }

    pathExe = ChromeDriverManager(path=r"Drivers").install()
    with webdriver.Chrome(service=ChromeService(pathExe), options=option) as driver:
        driver.get("https://www.etoro.com/fr/investing/dividend-calendar/")
        driver.implicitly_wait(5)
        driver.find_element(
            By.XPATH, '//*[@id="onetrust-accept-btn-handler"]').click()
        driver.implicitly_wait(5)
        driver.find_element(By.XPATH, '//*[@id="ec-load-more"]').click()
        driver.implicitly_wait(5)

        for idx in range(1, len(driver.find_elements(By.XPATH, '//*[@id="ec-reports-table"]/tbody/tr'))+1):
            symbol: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[1]/a/div/span[1]').text
            name: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[1]/a/div/span[2]').text
            sector: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[2]/span[2]').text
            dateExDividendData: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[3]/span[2]').text
            datePaymentData: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[4]/span[2]').text
            dividendPerShareData: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[6]/span[2]').text

            if (symbol != ""):
                dateExDividend: datetime = datetime.min
                datePayment: datetime = datetime.min
                dividendPerShare: float = .0

                if (search(r"\d{4}-\d{2}-\d{2}", dateExDividendData)):
                    dateExDiv: list[str] = dateExDividendData.split("-")
                    dateExDividend = datetime(
                        int(dateExDiv[0]), int(dateExDiv[1]), int(dateExDiv[2]))

                if (search(r"\d{4}-\d{2}-\d{2}", datePaymentData)):
                    datePay: list[str] = datePaymentData.split("-")
                    datePayment = datetime(
                        int(datePay[0]), int(datePay[1]), int(datePay[2]))

                if (dividendPerShareData != ''):
                    dividendPerShare = float(dividendPerShareData)

                findBySymbolStock: Stock | None = await Stock.prisma().find_unique(
                    where={
                        'symbol': symbol
                    }
                )

                findByAllDataStock: Stock | None = await Stock.prisma().find_first(
                    where={
                        'symbol': symbol,
                        'name': name,
                        'sector': sector,
                    }
                )

                if (findBySymbolStock == None and findByAllDataStock == None):
                    await Stock.prisma().create(
                        data={
                            'symbol': symbol,
                            'name': name,
                            'sector': sector,
                            'price': 0.0,
                            'status': Status.NEW,
                        }
                    )
                    counter['stock']['new'] += 1
                elif (findBySymbolStock != None and findByAllDataStock == None):
                    await Stock.prisma().update(
                        where={
                            'symbol': symbol
                        },
                        data={
                            'name': name,
                            'sector': sector,
                            'status': Status.UPDATED,
                        }
                    )
                    counter['stock']['updated'] += 1
                else:
                    counter['stock']['notChanged'] += 1

                findBySymbolDividend: Dividend | None = await Dividend.prisma().find_first(
                    where={
                        'stockSymbol': symbol
                    }
                )

                findByOrDateDataDividend: Dividend | None = await Dividend.prisma().find_first(
                    where={
                        'stockSymbol': symbol,
                        'OR': [
                            {'dateExDividend': dateExDividend},
                            {'datePayment': datePayment},
                        ]
                    }
                )

                findByAllDataDividend: Dividend | None = await Dividend.prisma().find_first(
                    where={
                        'stockSymbol': symbol,
                        'dateExDividend': dateExDividend,
                        'datePayment': datePayment,
                        'dividendPerShare': dividendPerShare,
                    }
                )

                # not found or found by symbol
                if (not (findBySymbolDividend and findByAllDataDividend and findByOrDateDataDividend)) or (findBySymbolDividend and (not findByAllDataDividend) and (not findByOrDateDataDividend)):
                    await Dividend.prisma().create(
                        data={
                            'dateExDividend': dateExDividend,
                            'datePayment': datePayment,
                            'dividendPerShare': dividendPerShare,
                            'status': Status.NEW,
                            'stockSymbol': symbol
                        }
                    )
                    counter['dividend']['new'] += 1
                # find by symbol and one of the two dates
                elif findByOrDateDataDividend and (not findByAllDataDividend):
                    await Dividend.prisma().update_many(
                        data={
                            'dateExDividend': dateExDividend,
                            'datePayment': datePayment,
                            'dividendPerShare': dividendPerShare,
                            'status': Status.UPDATED,
                            'stockSymbol': symbol
                        },
                        where={
                            'stockSymbol': symbol,
                            'OR': [
                                {'dateExDividend': dateExDividend},
                                {'datePayment': datePayment},
                            ]
                        }
                    )
                    counter['dividend']['updated'] += 1
                else:
                    counter['dividend']['notChanged'] += 1

    await db.disconnect()
    print(f"Stocks: {counter['stock']['new']} new, {counter['stock']['updated']} updated, {counter['stock']['notChanged']} not changed")
    print(f"Dividends: {counter['dividend']['new']} new, {counter['dividend']['updated']} updated, {counter['dividend']['notChanged']} not changed")
    # and total stats
    print(f"Total: {counter['stock']['new'] + counter['stock']['updated'] + counter['stock']['notChanged']} stocks, {counter['dividend']['new'] + counter['dividend']['updated'] + counter['dividend']['notChanged']} dividends")

if __name__ == "__main__":
    asyncio.run(main())
