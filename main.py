import asyncio
from typing import Any, Coroutine
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from datetime import datetime
from re import search
from prisma import Prisma
from prisma.enums import Status
from prisma.models import Dividende, Stock

date = datetime.now().strftime("%d-%m-%Y")

option = Options()
option.add_argument("--no-sandbox")
option.add_argument("--disable-gpu")
option.add_argument("--log-level=1")
option.add_experimental_option('excludeSwitches', ['enable-logging'])


async def main():
    db = Prisma(auto_register=True)
    await db.connect()

    pathExe = ChromeDriverManager(path=r".\\Drivers").install()
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
            dateExDividendeData: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[3]/span[2]').text
            datePaymentData: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[4]/span[2]').text
            dividendePerShareData: str = driver.find_element(
                By.XPATH, f'//*[@id="ec-reports-table"]/tbody/tr[{idx}]/td[6]/span[2]').text

            if (symbol != ""):
                dateExDividende: datetime = datetime.min
                datePayment: datetime = datetime.min
                dividendePerShare: float = .0

                if (search(r"\d{4}-\d{2}-\d{2}", dateExDividendeData)):
                    dateExDiv: list[str] = dateExDividendeData.split("-")
                    dateExDividende = datetime(
                        int(dateExDiv[0]), int(dateExDiv[1]), int(dateExDiv[2]))

                if (search(r"\d{4}-\d{2}-\d{2}", datePaymentData)):
                    datePay: list[str] = datePaymentData.split("-")
                    datePayment = datetime(
                        int(datePay[0]), int(datePay[1]), int(datePay[2]))

                if (dividendePerShareData != ''):
                    dividendePerShare = float(dividendePerShareData)

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
                else:
                    await Stock.prisma().update(
                        where={
                            'symbol': symbol
                        },
                        data={
                            'status': Status.NOT_CHANGED,
                        }
                    )
                
                findBySymbolDividende: Dividende | None = await db.dividende.find_unique(
                    where={
                        'stockSymbol': symbol
                    }
                )
                findByAllDataDividende: Dividende | None = await db.dividende.find_first(
                    where={
                        'stockSymbol': symbol,
                        'dateExDividende': dateExDividende,
                        'datePayment': datePayment,
                        'dividendePerShare': dividendePerShare,
                    }
                )

                if (findBySymbolDividende == None and findByAllDataDividende == None):
                    await Dividende.prisma().create(
                        data={
                            'stockSymbol': symbol,
                            'dateExDividende': dateExDividende,
                            'datePayment': datePayment,
                            'dividendePerShare': dividendePerShare,
                            'status': Status.NEW
                        }
                    )
                elif (findBySymbolDividende != None and findByAllDataDividende == None):
                    await Dividende.prisma().update(
                        where={
                            'stockSymbol': symbol,
                        },
                        data={
                            'dateExDividende': dateExDividende,
                            'datePayment': datePayment,
                            'dividendePerShare': dividendePerShare,
                            'status': Status.NEW
                        }
                    )
                else:
                    await Dividende.prisma().update(
                        where={
                            'stockSymbol': symbol
                        },
                            data={
                            'status': Status.NOT_CHANGED,
                        }
                    )

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
