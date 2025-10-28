from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def get_large_carousel_images(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)  # espera JS carregar

    image_urls = set()

    # localiza os thumbs (miniaturas)
    thumbs = driver.find_elements(By.CSS_SELECTOR, 'img')  # ajuste o seletor se necessário

    for thumb in thumbs:
        try:
            thumb.click()
            time.sleep(1)  # espera imagem principal atualizar
            large_img = driver.find_element(By.CSS_SELECTOR, '.fotorama__stage__frame.fotorama__active img')
            image_urls.add(large_img.get_attribute('src'))
        except Exception:
            continue

    driver.quit()
    return list(image_urls)

# Exemplo de uso
url = "https://nissei.com/py/apple-iphone-14-a2884"
print(get_large_carousel_images(url))

# Meu nome é Laura, sou assistente virtual da Fernando Rorato Tech. Estou aqui para ajudar no que for preciso!
