import pymongo
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from datetime import datetime
from re import search

date = datetime.now().strftime("%d-%m-%Y")

option = Options()
option.add_argument("--no-sandbox")
option.add_argument("--disable-gpu")
option.add_argument("--log-level=1")
option.add_experimental_option('excludeSwitches', ['enable-logging'])

conn_str = "mongodb://localhost:27017/"
client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)

try:
    client.server_info()
except Exception:
    print("Unable to connect to the server.")

db = client['KronosFinancial']
dividende = db['dividendes']

def main():
    pathExe = ChromeDriverManager(path=r".\\Drivers").install()
    with webdriver.Chrome(service=ChromeService(pathExe), options=option) as driver:
        driver.get("https://www.etoro.com/fr/investing/dividend-calendar/")
        driver.implicitly_wait(5)
        driver.find_element(
            By.XPATH, '//*[@id="onetrust-accept-btn-handler"]').click()
        driver.implicitly_wait(5)
        driver.find_element(By.XPATH, '//*[@id="ec-load-more"]').click()
        driver.implicitly_wait(5)
        for e in driver.find_elements(By.XPATH, '//*[@id="ec-reports-table"]/tbody/tr'):
            val = e.text.split("\n")
            if (val[0] == 'BDJ'):
                print(val)

            if (val != [""]):
                data = {
                    "Symbol": val[0],
                    "Date_ExDiv": None,
                    "Date_Paiement": None,
                    "Dividende": float(val[-2]),
                }

                if (val[-5] == '-' or not search(r"\d{4}-\d{2}-\d{2}", val[-5])):
                    data["Date_ExDiv"] = ''
                else:
                    dateExDiv = val[-5].split("-")
                    data["Date_ExDiv"] = datetime(
                        int(dateExDiv[0]), int(dateExDiv[1]), int(dateExDiv[2]))

                if (val[-4] == '-' or not search(r"\d{4}-\d{2}-\d{2}", val[-4])):
                    data["Date_Paiement"] = ''
                else:
                    datePaiement = val[-4].split("-")
                    data["Date_Paiement"] = datetime(
                        int(datePaiement[0]), int(datePaiement[1]), int(datePaiement[2]))

                req = dividende.find_one({"Symbol": val[0]})
                if (req == None):
                    dividende.insert_one(data)
                else:
                    dividende.find_one_and_replace({"Symbol": val[0]}, data)


if __name__ == "__main__":
    main()
