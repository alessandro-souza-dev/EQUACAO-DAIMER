from selenium import webdriver

from selenium.webdriver.common.by import By

from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import Select

import pandas as pd

import numpy as np

import re

import time

from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException, TimeoutException

import matplotlib.pyplot as plt

import os
from pathlib import Path

from typing import Any, cast

from openpyxl import Workbook

from openpyxl.styles import NamedStyle

from openpyxl.utils.dataframe import dataframe_to_rows

from dotenv import dotenv_values



# Carregar o .env do mesmo diretÃ³rio que o script

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAP_DIR = Path(SCRIPT_DIR)
DAIMER_WORKBOOK = SCRAP_DIR / 'Dados_Daimer.xlsx'
ENSAIOS_WORKBOOK = SCRAP_DIR / 'Dados_Ensaios.xlsx'

env_path = os.path.join(SCRIPT_DIR, '.env')

if not os.path.exists(env_path):

    raise FileNotFoundError(f"Arquivo .env nao encontrado em: {env_path}")

env_values = dotenv_values(env_path)

print(f"[env] .env carregado: {env_path}")



def normalizar_valor_env(valor: Any) -> str:

    if valor is None:

        return ""

    texto = str(valor).strip()

    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in {'"', "'"}:

        texto = texto[1:-1].strip()

    return texto


def obter_valor_env(*chaves: str, obrigatorio: bool = True) -> str | None:

    for chave in chaves:

        valor = normalizar_valor_env(env_values.get(chave))

        if valor:

            return valor

    if obrigatorio:

        raise RuntimeError(

            f"Valor ausente no arquivo scraping/.env para uma das chaves: {', '.join(chaves)}"

        )

    return None


def preencher_input_texto(elemento: Any, valor: str) -> None:

    driver = elemento.parent

    try:

        elemento.click()

    except ElementClickInterceptedException:

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].focus();", elemento)

    try:

        elemento.clear()

    except Exception:

        pass

    elemento.send_keys(Keys.CONTROL, "a")

    elemento.send_keys(Keys.DELETE)

    elemento.send_keys(valor)

    valor_atual = (elemento.get_attribute("value") or "").strip()

    if valor_atual == valor:

        return

    driver.execute_script(

        """
        const element = arguments[0];
        const value = arguments[1];
        element.focus();
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
        """,

        elemento,

        valor,

    )

    valor_atual = (elemento.get_attribute("value") or "").strip()

    if valor_atual != valor:

        raise RuntimeError("Nao foi possivel preencher o campo com o valor esperado do .env.")


def mascarar_usuario(usuario: str) -> str:

    if "@" not in usuario:

        return f"***({len(usuario)})"

    prefixo, dominio = usuario.split("@", 1)

    prefixo_mascarado = prefixo[:2] + "***" if prefixo else "***"

    return f"{prefixo_mascarado}@{dominio}"


def extrair_textos_td_por_xpath(browser: webdriver.Chrome, tabela_xpath: str, tentativas: int = 3) -> list[str]:

    ultimo_erro: Exception | None = None

    for tentativa in range(1, tentativas + 1):

        try:

            textos = browser.execute_script(

                """
                const xpath = arguments[0];
                const resultado = document.evaluate(
                    xpath,
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null,
                );
                const tabela = resultado.singleNodeValue;
                if (!tabela) {
                    return null;
                }
                return Array.from(tabela.querySelectorAll('td')).map((celula) =>
                    (celula.innerText || celula.textContent || '').trim()
                );
                """,

                tabela_xpath,

            )

            if textos is None:

                raise RuntimeError("Tabela nao encontrada no DOM atual.")

            return [str(texto) for texto in textos]

        except Exception as erro:

            ultimo_erro = erro

            if tentativa == tentativas:

                break

            time.sleep(0.5)

    assert ultimo_erro is not None

    raise RuntimeError(f"Nao foi possivel ler a tabela apos {tentativas} tentativas.") from ultimo_erro


def clicar_xpath_quando_presente(browser: webdriver.Chrome, xpath: str, timeout: int = 10):

    elemento = WebDriverWait(browser, timeout).until(

        EC.presence_of_element_located((By.XPATH, xpath))

    )

    browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)

    browser.execute_script("arguments[0].click();", elemento)

    return elemento


SITE_URL_ENV = obter_valor_env('SITE_URL', obrigatorio=False)

USERNAME: str = cast(str, obter_valor_env('DAIMER_EMAIL', 'USERNAME'))

PASSWORD: str = cast(str, obter_valor_env('DAIMER_PASSWORD', 'PASSWORD'))

print("[env] credenciais obtidas exclusivamente do arquivo .env.")

print(f"[env] usuario selecionado: {mascarar_usuario(USERNAME)}")


BASE_URL = SITE_URL_ENV or 'https://daimer.data.com.br/'
MAX_BROWSER_START_RETRIES = 5
PAGE_LOAD_TIMEOUT_SECONDS = 60



# ConfiguraÃ§Ãµes do ChromeDriver

chrome_options = webdriver.ChromeOptions()

# --incognito garante sessao isolada; nao combinar com --user-data-dir (incompativel Chrome 147+)
chrome_options.add_argument("--incognito")
chrome_options.page_load_strategy = "eager"

chrome_options.add_argument("--window-size=1920,1080")

# Flags de estabilidade essenciais para Chrome automatizado
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-software-rasterizer")
chrome_options.add_argument("--disable-extensions")

chrome_options.add_argument("--disable-features=PasswordManagerOnboarding,AutofillServerCommunication,PasswordLeakDetection")

# Nota: add_experimental_option("prefs") e incompativel com --incognito no Chrome 147+
# O modo incognito ja desativa passwords e autofill automaticamente


def criar_browser() -> webdriver.Chrome:

    novo_browser = webdriver.Chrome(options=chrome_options)

    novo_browser.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SECONDS)

    novo_browser.maximize_window()

    try:
        novo_browser.execute_script("if(document.body) document.body.style.zoom='80%';")
    except Exception:
        pass

    return novo_browser


def abrir_site_com_retry(browser: webdriver.Chrome, contexto: str, tentativas: int = MAX_BROWSER_START_RETRIES) -> webdriver.Chrome:

    ultimo_erro: Exception | None = None

    browser_atual = browser

    for tentativa in range(1, tentativas + 1):

        try:

            browser_atual.get(BASE_URL)

            WebDriverWait(browser_atual, 20).until(

                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='E-mail']"))

            )

            return browser_atual

        except Exception as erro:

            ultimo_erro = erro

            print(

                f"[browser] Falha ao abrir {BASE_URL} em {contexto} "

                f"(tentativa {tentativa}/{tentativas}): {type(erro).__name__}: {erro}"

            )

            try:

                browser_atual.quit()

            except Exception:

                pass

            if tentativa == tentativas:

                break

            espera = 10 * tentativa  # 10s, 20s, 30s, 40s...
            print(f"[browser] A aguardar {espera}s antes de nova tentativa...")
            time.sleep(espera)

            browser_atual = criar_browser()

    assert ultimo_erro is not None

    raise RuntimeError(f"Nao foi possivel abrir o site DAIMER em {contexto} apos {tentativas} tentativas.") from ultimo_erro



# Inicialize o webdriver Chromium (Chrome) usando o ChromeDriver

browser = criar_browser()



# Abrir o site

browser = abrir_site_com_retry(browser, "inicio")



# Insira o login

login_field = browser.find_element(By.XPATH, "//input[@placeholder='E-mail']")

preencher_input_texto(login_field, USERNAME)



# Insira a sen

password_field = browser.find_element(

    By.XPATH, "//input[@placeholder='Senha']")

preencher_input_texto(password_field, PASSWORD)



# Encontre o elemento usando o XPath fornecido e clique via JS para evitar intercepÃ§Ã£o

button = WebDriverWait(browser, 10).until(

    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Enviar')]"))

)

browser.execute_script("arguments[0].click();", button)



# Aguarde um curto perÃ­odo para garantir que a pÃ¡gina esteja totalmente carregada

time.sleep(2)



try:

    # Localize o elemento <select> usando XPath e clique nele

    clicar_xpath_quando_presente(

        browser,

        "/html/body/app-root/div/div/sidepanel/aside[1]/div[3]/div[2]/div/a[3]/div/i",

    )

except Exception as e:

    browser.save_screenshot("erro_menu.png")

    print(f"Erro ao encontrar menu. URL atual: {browser.current_url}")

    print(browser.page_source[:500])

    raise e



# Aguarde atÃ© que o dropdown seja clicÃ¡vel

clicar_xpath_quando_presente(

    browser,

    "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist",

)



# Lista para armazenar todos os itens do dropdown

all_items_list = []

os_alvo_raw_inicial = os.environ.get("DAIMER_OS_ALVO", "").strip()



# Loop externo para iterar sobre as letras do alfabeto

if os_alvo_raw_inicial:

    all_items_list = [

        item.strip()

        for item in re.split(r"[;,\s]+", os_alvo_raw_inicial)

        if item.strip()

    ]

    print(f"[filtro] DAIMER_OS_ALVO ativo: usando lista direta com {len(all_items_list)} OS.")

else:

    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':

        # Insira a letra atual no campo de entrada

        input_element = WebDriverWait(browser, 5).until(

            EC.element_to_be_clickable(

                (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/input"))

        )

        input_element.clear()

        input_element.send_keys(letter)



        # Aguarde X segundos antes de capturar os itens

        time.sleep(2)



        try:

            # Localize a lista de itens no dropdown

            dropdown_items = WebDriverWait(browser, 2).until(

                EC.presence_of_all_elements_located(

                    (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/div/*"))

            )



            # Localize o elemento que contÃ©m os itens no dropdown

            items_container = WebDriverWait(browser, 2).until(

                EC.presence_of_element_located(

                    (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist"))

            )



            # Obtenha todos os itens do dropdown

            dropdown_items = items_container.find_elements(By.XPATH, "./div/*")



            # Armazene os itens do dropdown na lista mestra

            for item in dropdown_items:

                item_text = item.text

                if item_text:

                    all_items_list.append(item_text)

        except Exception as e:

            # Lidar com exceÃ§Ã£o se nÃ£o houver itens no dropdown

            print(f"NÃ£o foram encontrados itens para a letra {letter}: {str(e)}")



# Lista para armazenar os dados

dados: list[list[Any]] = []



# Lista para armazenar os dados de ensaios elÃ©tricos

dados_ensaios: list[dict[str, Any]] = []



# Carregar dados jÃ¡ existentes nos Excel para retomar de onde parou

_colunas_daimer = ["NR_OS", "Criado", "Preenchido", "Submetido", "Processado", "Revisado",

                   "Disponibilizado", "Aprovado", "Cliente", "Planta", "Setor",

                   "Tag da Máquina(NS)", "Tipo de Equipamento", "Tipo de Diagnóstico",

                   "Serviço de Campo", "Kit_Utilizado"]

_colunas_dados_maquina_daimer = [

    'Tipo de Serviço', 'Nome', 'Data de Instalação', 'Número de saídas',

    'Número de polos', 'Rotação (RPM)', 'Potência', 'Frequência (Hz)',

    'Tensão Estator (V)', 'Corrente Estator (A)', 'Tensão Excitação (Vcc)',

    'Corrente Excitação (Acc)', 'Tensão PMG (V)', 'Corrente PMG (A)',

    'Fabricante', 'Tipo', 'Modelo', 'Número de Série', 'Ligação [Y/∆]',

    'Carcaça', 'Fabricado em', 'Grau de Proteção (IP)', 'Rendimento (%)',

    'Fator de Serviço', 'Fator de Potência', 'Regime', 'Classe Isol [A,B,F,H]',

    '∆T (°C)',

]

_colunas_daimer = _colunas_daimer + _colunas_dados_maquina_daimer

_colunas_ensaios = [

    'NR_OS', 'Tipo de Equipamento', 'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H',

    'Grau de Envelhecimento GEI (Anos)', 'GEI - Referência',

    'Avaliação Global', 'Avaliação Global - Referência',

    'Grau de Deterioração (D10)', 'D10 - Referência',

    'Grau de Contaminação (D20)', 'D20 - Referência',

]

_colunas_dados_maquina = [

    'Máquina - Cliente', 'Máquina - Planta', 'Máquina - Setor',

    'Máquina - Tag/No de Série', 'Máquina - Tipo do Equipamento',

    'Máquina - Tipo de Diagnose', 'Máquina - Tipo de Serviço',

    'Máquina - Nome', 'Máquina - Data de Instalação',

    'Máquina - Número de Saídas', 'Máquina - Número de Polos',

    'Máquina - Rotação (RPM)', 'Máquina - Potência',

    'Máquina - Potência Unidade', 'Máquina - Frequência (Hz)',

    'Máquina - Tensão Estator (V)', 'Máquina - Corrente Estator (A)',

    'Máquina - Tensão Excitação (Vcc)', 'Máquina - Corrente Excitação (Acc)',

    'Máquina - Tensão PMG (V)', 'Máquina - Corrente PMG (A)',

    'Máquina - Fabricante', 'Máquina - Tipo', 'Máquina - Modelo',

    'Máquina - Número de Série', 'Máquina - Ligação [Y/∆]',

    'Máquina - Carcaça', 'Máquina - Fabricado em',

    'Máquina - Grau de Proteção (IP)', 'Máquina - Rendimento (%)',

    'Máquina - Fator de Serviço', 'Máquina - Fator de Potência',

    'Máquina - Fator de Potência Unidade', 'Máquina - Regime',

    'Máquina - Classe Isol [A,B,F,H]', 'Máquina - ∆T (°C)',

]

_colunas_ensaios = _colunas_ensaios + _colunas_dados_maquina

_mapeamento_rotulos_dados_maquina = {

    'Cliente': [('Máquina - Cliente', 'valor')],

    'Planta': [('Máquina - Planta', 'valor')],

    'Setor': [('Máquina - Setor', 'valor')],

    'Tag/No de série da máquina': [('Máquina - Tag/No de Série', 'valor')],

    'Tag/Nº de série da máquina': [('Máquina - Tag/No de Série', 'valor')],

    'Tipo do equipamento': [('Máquina - Tipo do Equipamento', 'valor')],

    'Tipo de diagnose': [('Máquina - Tipo de Diagnose', 'valor')],

    'Tipo de serviço': [('Máquina - Tipo de Serviço', 'valor')],

    'Nome': [('Máquina - Nome', 'valor')],

    'Data de instalação': [('Máquina - Data de Instalação', 'valor')],

    'Número de saídas': [('Máquina - Número de Saídas', 'valor')],

    'Número de polos': [('Máquina - Número de Polos', 'valor')],

    'Rotação (RPM)': [('Máquina - Rotação (RPM)', 'valor')],

    'Potência': [('Máquina - Potência', 'valor'), ('Máquina - Potência Unidade', 'unidade')],

    'Frequência (Hz)': [('Máquina - Frequência (Hz)', 'valor')],

    'Tensão Estator (V)': [('Máquina - Tensão Estator (V)', 'valor')],

    'Tensão (V)': [('Máquina - Tensão Estator (V)', 'valor')],

    'Corrente Estator (A)': [('Máquina - Corrente Estator (A)', 'valor')],

    'Corrente (A)': [('Máquina - Corrente Estator (A)', 'valor')],

    'Tensão Excitação (Vcc)': [('Máquina - Tensão Excitação (Vcc)', 'valor')],

    'Corrente Excitação (Acc)': [('Máquina - Corrente Excitação (Acc)', 'valor')],

    'Tensão PMG (V)': [('Máquina - Tensão PMG (V)', 'valor')],

    'Corrente PMG (A)': [('Máquina - Corrente PMG (A)', 'valor')],

    'Fabricante': [('Máquina - Fabricante', 'valor')],

    'Tipo': [('Máquina - Tipo', 'valor')],

    'Modelo': [('Máquina - Modelo', 'valor')],

    'Número de série': [('Máquina - Número de Série', 'valor')],

    'Ligação [Y/∆]': [('Máquina - Ligação [Y/∆]', 'valor')],

    'Ligação [Y/Δ]': [('Máquina - Ligação [Y/∆]', 'valor')],

    'Carcaça': [('Máquina - Carcaça', 'valor')],

    'Fabricado em': [('Máquina - Fabricado em', 'valor')],

    'Grau de Proteção (IP)': [('Máquina - Grau de Proteção (IP)', 'valor')],

    'Rendimento (%)': [('Máquina - Rendimento (%)', 'valor')],

    'Fator de Serviço': [('Máquina - Fator de Serviço', 'valor')],

    'Fator de Potência': [('Máquina - Fator de Potência', 'valor'), ('Máquina - Fator de Potência Unidade', 'unidade')],

    'Regime': [('Máquina - Regime', 'valor')],

    'Classe Isol [A,B,F,H]': [('Máquina - Classe Isol [A,B,F,H]', 'valor')],

    '∆T (°C)': [('Máquina - ∆T (°C)', 'valor')],

    'ΔT (°C)': [('Máquina - ∆T (°C)', 'valor')],

}

_mapa_dados_maquina_daimer = {

    'Tipo de Serviço': 'Máquina - Tipo de Serviço',

    'Nome': 'Máquina - Nome',

    'Data de Instalação': 'Máquina - Data de Instalação',

    'Número de saídas': 'Máquina - Número de Saídas',

    'Número de polos': 'Máquina - Número de Polos',

    'Rotação (RPM)': 'Máquina - Rotação (RPM)',

    'Potência': 'Máquina - Potência',

    'Frequência (Hz)': 'Máquina - Frequência (Hz)',

    'Tensão Estator (V)': 'Máquina - Tensão Estator (V)',

    'Corrente Estator (A)': 'Máquina - Corrente Estator (A)',

    'Tensão Excitação (Vcc)': 'Máquina - Tensão Excitação (Vcc)',

    'Corrente Excitação (Acc)': 'Máquina - Corrente Excitação (Acc)',

    'Tensão PMG (V)': 'Máquina - Tensão PMG (V)',

    'Corrente PMG (A)': 'Máquina - Corrente PMG (A)',

    'Fabricante': 'Máquina - Fabricante',

    'Tipo': 'Máquina - Tipo',

    'Modelo': 'Máquina - Modelo',

    'Número de Série': 'Máquina - Número de Série',

    'Ligação [Y/∆]': 'Máquina - Ligação [Y/∆]',

    'Carcaça': 'Máquina - Carcaça',

    'Fabricado em': 'Máquina - Fabricado em',

    'Grau de Proteção (IP)': 'Máquina - Grau de Proteção (IP)',

    'Rendimento (%)': 'Máquina - Rendimento (%)',

    'Fator de Serviço': 'Máquina - Fator de Serviço',

    'Fator de Potência': 'Máquina - Fator de Potência',

    'Regime': 'Máquina - Regime',

    'Classe Isol [A,B,F,H]': 'Máquina - Classe Isol [A,B,F,H]',

    '∆T (°C)': 'Máquina - ∆T (°C)',

}

_aliases_colunas_ensaios = {

    'Î”I': 'ΔI',

    'Î”Tan Î´': 'ΔTan δ',

    'Tang Î´ (h)': 'Tang δ (h)',

    'Tan Î´': 'Tan δ',

    'GEI - Refer�ncia': 'GEI - Referência',

    'AvaliaÃ§Ã£o Global': 'Avaliação Global',

    'AvaliaÃ§Ã£o Global - Referência': 'Avaliação Global - Referência',

    'AvaliaÃ§Ã£o Global - Refer�ncia': 'Avaliação Global - Referência',

    'Grau de Deteriora��o (D10)': 'Grau de Deterioração (D10)',

    'D10 - Refer�ncia': 'D10 - Referência',

    'Grau de Contamina��o (D20)': 'Grau de Contaminação (D20)',

    'D20 - Refer�ncia': 'D20 - Referência',

}

os_processadas_execucao = set()

if DAIMER_WORKBOOK.exists():

    try:

        _df_existente = pd.read_excel(DAIMER_WORKBOOK)

        _df_existente = _df_existente.reindex(columns=_colunas_daimer)

        dados = _df_existente.values.tolist()

        print(f"[resume] Dados_Daimer.xlsx carregado: {len(dados)} registos existentes.")

    except Exception as _e:

        print(f"[resume] NÃ£o foi possÃ­vel carregar Dados_Daimer.xlsx: {_e}")

if ENSAIOS_WORKBOOK.exists():

    try:

        _df_ens_existente = pd.read_excel(ENSAIOS_WORKBOOK)

        _df_ens_existente = _df_ens_existente.rename(columns=_aliases_colunas_ensaios)

        dados_ensaios = cast(list[dict[str, Any]], _df_ens_existente.to_dict('records'))

        print(f"[resume] Dados_Ensaios.xlsx carregado: {len(dados_ensaios)} registos existentes.")

    except Exception as _e:

        print(f"[resume] NÃ£o foi possÃ­vel carregar Dados_Ensaios.xlsx: {_e}")



def normalizar_os(valor: Any) -> str:

    if valor is None:

        return ""

    try:

        if pd.isna(valor):

            return ""

    except TypeError:

        pass

    texto = re.sub(r"\s+", "", str(valor).strip())

    if texto.endswith(".0") and texto[:-2].isdigit():

        texto = texto[:-2]

    return texto.lstrip('0') or texto


def obter_os_alvo_execucao() -> set[str]:

    texto = os.environ.get("DAIMER_OS_ALVO", "")

    itens = re.split(r"[;,\s]+", texto)

    return {normalizar_os(item) for item in itens if normalizar_os(item)}



def normalizar_valor_comparacao(valor: Any) -> str:

    if valor is None:

        return ""

    try:

        if pd.isna(valor):

            return ""

    except TypeError:

        pass

    texto = re.sub(r"\s+", " ", str(valor).strip())

    if texto.lower() in {"", "nan", "none", "na", "n/a"}:

        return ""

    texto_numero = texto.replace(",", ".")

    if re.fullmatch(r"[-+]?\d+(\.\d+)?", texto_numero):

        numero = float(texto_numero)

        return f"{numero:.12g}"

    return texto.casefold()


def primeiro_elemento_visivel(elementos: list[Any]) -> Any | None:

    for elemento in elementos:

        try:

            if elemento.is_displayed():

                return elemento

        except StaleElementReferenceException:

            continue

    return None


def selecionar_os_no_datalist(browser: webdriver.Chrome, nr_os: str) -> None:

    input_xpath = "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/input"

    datalist_xpath = "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist"

    os_alvo = normalizar_os(nr_os)

    input_os = WebDriverWait(browser, 10).until(

        EC.element_to_be_clickable((By.XPATH, input_xpath))

    )

    browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_os)

    try:

        input_os.click()

    except ElementClickInterceptedException:

        browser.execute_script("arguments[0].focus();", input_os)

    input_os.send_keys(Keys.CONTROL, "a")

    input_os.send_keys(Keys.DELETE)

    input_os.send_keys(nr_os)

    WebDriverWait(browser, 10).until(

        EC.presence_of_element_located((By.XPATH, datalist_xpath))

    )

    def encontrar_item_exato(_: Any) -> Any | bool:

        try:

            container_atual = browser.find_element(By.XPATH, datalist_xpath)

            itens = container_atual.find_elements(By.XPATH, "./div/*")

            for item in itens:

                texto_item_atual = item.text.strip()

                primeiro_token = texto_item_atual.split()[0] if texto_item_atual.split() else texto_item_atual

                if normalizar_os(texto_item_atual) == os_alvo or normalizar_os(primeiro_token) == os_alvo:

                    return item

        except StaleElementReferenceException:

            return False

        return False

    item_exato = cast(Any, WebDriverWait(browser, 10).until(encontrar_item_exato))

    texto_item = item_exato.text.strip()

    browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", item_exato)

    browser.execute_script("arguments[0].click();", item_exato)

    time.sleep(1)

    valor_input = browser.find_element(By.XPATH, input_xpath).get_attribute("value") or texto_item

    if normalizar_os(valor_input) != os_alvo and normalizar_os(texto_item) != os_alvo:

        raise RuntimeError(f"OS selecionada no datalist nao confere: alvo={nr_os}, input={valor_input}, item={texto_item}")

    WebDriverWait(browser, 15).until(

        lambda b: bool(b.find_elements(By.XPATH, "//p-timeline//small") or b.find_elements(By.CSS_SELECTOR, ".assetDataPage"))

    )


def clicar_aba_e_obter_painel(browser: webdriver.Chrome, aba: Any, descricao: str, timeout: int = 10) -> Any:

    aba_id = aba.get_attribute("id") or ""

    painel_id = aba.get_attribute("aria-controls") or (f"{aba_id}-panel" if aba_id else "")

    browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", aba)

    browser.execute_script("arguments[0].click();", aba)

    def painel_visivel(_: Any) -> Any | bool:

        try:

            if painel_id:

                paineis = browser.find_elements(By.ID, painel_id)

                painel = primeiro_elemento_visivel(paineis)

                if painel is not None:

                    return painel

            painel_por_conteudo = browser.execute_script(

                """
                const visible = (element) => {
                    if (!element) return false;
                    const style = window.getComputedStyle(element);
                    if (style.visibility === 'hidden' || style.display === 'none') return false;
                    return !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
                };
                const botoes = Array.from(document.querySelectorAll('.btn-ge')).filter(visible);
                if (!botoes.length) return null;
                const botao = botoes[botoes.length - 1];
                return botao.closest('[role="tabpanel"], .tab-pane, .card, .ng-star-inserted, div') || botao.parentElement;
                """

            )

            if painel_por_conteudo is not None:

                return painel_por_conteudo

        except (NoSuchElementException, StaleElementReferenceException):

            return False

    try:

        return WebDriverWait(browser, timeout).until(painel_visivel)

    except TimeoutException as erro:

        detalhe = painel_id or "conteudo visivel da aba"

        raise TimeoutException(f"Painel da aba '{descricao}' nao ficou visivel: {detalhe}") from erro


def obter_corpo_modal_visivel(browser: webdriver.Chrome) -> Any | bool:

    seletores = [

        "ngb-modal-window .modal-body",

        "ngb-modal-window div.modal-content > div:nth-child(2)",

        "ngb-modal-window div[role='document'] div:nth-child(2)",

    ]

    for seletor in seletores:

        corpo = primeiro_elemento_visivel(browser.find_elements(By.CSS_SELECTOR, seletor))

        if corpo is not None:

            return corpo

    return False


def extrair_linhas_resultado_painel(painel: Any) -> list[tuple[str, str, str | None]]:

    linhas_resultado: list[tuple[str, str, str | None]] = []

    try:

        for tabela in painel.find_elements(By.CSS_SELECTOR, "table"):

            for row in tabela.find_elements(By.XPATH, ".//tr"):

                cols = row.find_elements(By.TAG_NAME, "td")

                if len(cols) < 2:

                    continue

                param = cols[0].text.strip()

                if not any(trecho in param for trecho in ("Grau de Envelhecimento", "GEI", "Avaliação Global", "Grau de Deterioração", "D10", "Grau de Contaminação", "D20")):

                    continue

                valor = cols[1].text.strip()

                ref = cols[2].text.strip() if len(cols) >= 3 else None

                linhas_resultado.append((param, valor, ref))

    except StaleElementReferenceException:

        return []

    return linhas_resultado


def extrair_linhas_resultado_visiveis(browser: webdriver.Chrome) -> list[tuple[str, str, str | None]]:

    linhas_resultado: list[tuple[str, str, str | None]] = []

    try:

        tabelas = browser.find_elements(By.CSS_SELECTOR, "table")

        for tabela in tabelas:

            try:

                if not tabela.is_displayed():

                    continue

            except StaleElementReferenceException:

                continue

            for row in tabela.find_elements(By.XPATH, ".//tr"):

                cols = row.find_elements(By.TAG_NAME, "td")

                if len(cols) < 2:

                    continue

                param = cols[0].text.strip()

                if not any(trecho in param for trecho in ("Grau de Envelhecimento", "GEI", "Avaliação Global", "Grau de Deterioração", "D10", "Grau de Contaminação", "D20")):

                    continue

                valor = cols[1].text.strip()

                ref = cols[2].text.strip() if len(cols) >= 3 else None

                linhas_resultado.append((param, valor, ref))

    except StaleElementReferenceException:

        return []

    return linhas_resultado


def assinatura_dados_ensaio(dados_ensaio: dict[str, Any]) -> tuple[str, ...]:

    colunas_assinatura = [

        'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H',

        'Grau de Envelhecimento GEI (Anos)', 'Avaliação Global',

        'Grau de Deterioração (D10)', 'Grau de Contaminação (D20)',

    ]

    return tuple(normalizar_valor_comparacao(dados_ensaio.get(coluna)) for coluna in colunas_assinatura)


def normalizar_rotulo_dados_maquina(rotulo: Any) -> str:

    texto = re.sub(r"\s+", " ", str(rotulo).replace("\xa0", " ")).strip()

    return texto.rstrip(':').casefold()


def normalizar_valor_dados_maquina(valor: Any) -> str | None:

    if valor is None:

        return None

    texto = re.sub(r"\s+", " ", str(valor).replace("\xa0", " ")).strip()

    if texto.lower() in {"", "nan", "none", "na", "n/a"}:

        return None

    return texto


def selecionar_aba_dados_maquina(browser: webdriver.Chrome) -> bool:

    candidatos = browser.find_elements(By.XPATH, "//*[@id='ngb-nav-23']")

    if not candidatos:

        for aba in browser.find_elements(By.XPATH, "//ul[@role='tablist']//a"):

            texto_aba = normalizar_rotulo_dados_maquina(aba.text)

            if "dados" in texto_aba and any(

                trecho in texto_aba

                for trecho in ("máquina", "maquina", "equipamento", "ativo", "placa")

            ):

                candidatos.append(aba)

                break

    if not candidatos:

        return False

    aba_dados_maquina = candidatos[0]

    browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", aba_dados_maquina)

    browser.execute_script("arguments[0].click();", aba_dados_maquina)

    time.sleep(1)

    return True


def extrair_dados_maquina(browser: webdriver.Chrome, nr_os: str) -> dict[str, Any]:

    dados_maquina: dict[str, Any] = {coluna: None for coluna in _colunas_dados_maquina}

    try:

        aba_encontrada = selecionar_aba_dados_maquina(browser)

        if not aba_encontrada:

            conteudo_visivel = browser.find_elements(By.CSS_SELECTOR, ".assetDataPage")

            if conteudo_visivel:

                print(f"  [maquina] Aba ngb-nav-23 nao localizada, usando dados da maquina ja visiveis para {nr_os}.")

            else:

                print(f"  [maquina] Aba ngb-nav-23 nao encontrada para {nr_os}. Campos de maquina ficam vazios.")

                return dados_maquina

        valores = browser.execute_script(

            """
            const xpath = "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]";
            const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
            const root = result.singleNodeValue || document.querySelector('.assetDataPage')?.closest('.card') || document;
            const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim().replace(/:$/, '');
            const selectedText = (select) => {
                if (!select) return '';
                const option = select.options[select.selectedIndex];
                return clean(option ? option.textContent : select.value);
            };
            const values = {};
            root.querySelectorAll('vitau-textinput, vitau-select, daimer-numberinput, vitau-datepicker').forEach((component) => {
                const label = clean(component.querySelector('span')?.textContent);
                if (!label) return;
                const input = component.querySelector('input');
                const select = component.querySelector('select');
                let value = '';
                let unit = '';
                if (component.tagName.toLowerCase() === 'daimer-numberinput') {
                    value = clean(input ? input.value : '');
                    unit = selectedText(select);
                } else if (select) {
                    value = selectedText(select);
                } else if (input) {
                    value = clean(input.value || input.getAttribute('value') || '');
                }
                values[label] = { valor: value, unidade: unit };
            });
            return values;
            """

        )

        valores_por_rotulo = {

            normalizar_rotulo_dados_maquina(rotulo): valor

            for rotulo, valor in dict(valores or {}).items()

        }

        for rotulo, destinos in _mapeamento_rotulos_dados_maquina.items():

            origem = valores_por_rotulo.get(normalizar_rotulo_dados_maquina(rotulo))

            if not origem:

                continue

            for coluna, chave in destinos:

                dados_maquina[coluna] = normalizar_valor_dados_maquina(origem.get(chave))

        preenchidos = sum(

            1 for valor in dados_maquina.values() if normalizar_valor_comparacao(valor)

        )

        print(f"  [maquina] {preenchidos} campos extraidos da aba ngb-nav-23 para {nr_os}.")

    except Exception as erro:

        print(f"  [maquina] Erro ao extrair dados da maquina para {nr_os}: {erro}")

    return dados_maquina



def linha_lista_para_dict(linha: Any, colunas: list[str]) -> dict[str, Any]:

    if isinstance(linha, dict):

        return {coluna: linha.get(coluna) for coluna in colunas}

    return {

        coluna: linha[indice] if indice < len(linha) else None

        for indice, coluna in enumerate(colunas)

    }



def registros_iguais(registro_atual: dict[str, Any], registro_novo: dict[str, Any], colunas: list[str]) -> bool:

    for coluna in colunas:

        if coluna == 'NR_OS':

            if normalizar_os(registro_atual.get(coluna)) != normalizar_os(registro_novo.get(coluna)):

                return False

            continue

        if normalizar_valor_comparacao(registro_atual.get(coluna)) != normalizar_valor_comparacao(registro_novo.get(coluna)):

            return False

    return True



def reconciliar_registro(

    registros: list[Any],

    registro_novo: dict[str, Any],

    colunas: list[str],

    nome_planilha: str,

    manter_como_lista: bool,

) -> str:

    os_nova = normalizar_os(registro_novo.get('NR_OS'))

    registros_mantidos = []

    registros_iguais_encontrados = 0

    registros_divergentes = 0



    for registro_atual in registros:

        registro_atual_dict = linha_lista_para_dict(registro_atual, colunas)

        if normalizar_os(registro_atual_dict.get('NR_OS')) != os_nova:

            registros_mantidos.append(registro_atual)

            continue

        if registros_iguais(registro_atual_dict, registro_novo, colunas):

            registros_iguais_encontrados += 1

        else:

            registros_divergentes += 1



    if registros_iguais_encontrados == 1 and registros_divergentes == 0:

        print(f"  [skip] {nome_planilha}: {os_nova} ja existe igual ao scrape.")

        return "igual"



    registro_final = [registro_novo.get(coluna) for coluna in colunas] if manter_como_lista else registro_novo

    registros[:] = registros_mantidos + [registro_final]



    if registros_iguais_encontrados or registros_divergentes:

        print(

            f"  [upsert] {nome_planilha}: {os_nova} substituida "

            f"({registros_iguais_encontrados} igual, {registros_divergentes} divergente)."

        )

        return "substituida"



    print(f"  [upsert] {nome_planilha}: {os_nova} adicionada.")

    return "adicionada"



def salvar_excels_incrementais(dados, dados_ensaios):

    """Guarda os dados acumulados nos ficheiros Excel sem fechar o browser."""

    colunas = _colunas_daimer

    if dados:

        df_inc = pd.DataFrame(dados, columns=colunas)

        df_inc['NR_OS'] = df_inc['NR_OS'].astype(str).str.lstrip('0')

        df_inc['Serviço de Campo'] = df_inc['Serviço de Campo'].replace({

            'Douglas Aparecido Lopes': 'Supervisor de Ensaios Elétricos',

            'Yswame Rodrigues da Cunha': 'Supervisor de Serviço de Campo'

        })

        df_inc.to_excel(DAIMER_WORKBOOK, index=False)

    colunas_ensaios = _colunas_ensaios

    if dados_ensaios:

        df_ens_inc = pd.DataFrame(dados_ensaios, columns=colunas_ensaios)

        df_ens_inc['NR_OS'] = df_ens_inc['NR_OS'].astype(str).str.lstrip('0')

        df_ens_inc.to_excel(ENSAIOS_WORKBOOK, index=False)

    print("  [save] Ficheiros Excel guardados.")





# Itere sobre os itens e insira um a um no campo de entrada

os_alvo_execucao = obter_os_alvo_execucao()

if os_alvo_execucao:

    itens_antes_filtro = len(all_items_list)

    all_items_list = [item for item in all_items_list if normalizar_os(item) in os_alvo_execucao]

    os_encontradas = {normalizar_os(item) for item in all_items_list}

    os_nao_encontradas = sorted(os_alvo_execucao - os_encontradas)

    print(

        f"[filtro] DAIMER_OS_ALVO ativo: {len(all_items_list)}/{itens_antes_filtro} OS serao processadas."

    )

    if os_nao_encontradas:

        print(f"[filtro] OS alvo nao encontradas no dropdown: {os_nao_encontradas}")

letra_atual = all_items_list[0][0].upper() if all_items_list else ''

ultima_assinatura_ensaio: tuple[str, ...] | None = None

repeticoes_assinatura_ensaio = 0

LIMITE_ASSINATURA_ENSAIO_REPETIDA = 5

interromper_execucao = False

for item_text in all_items_list:

    item_os_normalizada = normalizar_os(item_text)

    if item_os_normalizada in os_processadas_execucao:

        print(f"  [skip] {item_text} ja foi verificada nesta execucao, a saltar...")

        continue



    # Detectar mudanÃ§a de letra (Aâ†’B, Bâ†’C, etc.) e guardar Excel antes de continuar

    letra_os = item_text[0].upper() if item_text else ''

    if letra_os != letra_atual:

        print(f"  [save] MudanÃ§a de letra {letra_atual} â†’ {letra_os}. A guardar Excel...")

        salvar_excels_incrementais(dados, dados_ensaios)

        letra_atual = letra_os



    try:

        input_element = WebDriverWait(browser, 10).until(

            EC.element_to_be_clickable(

                (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/input"))

        )

    except Exception as e_tab:

        print(f"  [recovery] Erro ao localizar input ({e_tab}). A tentar recuperar...")

        try:

            browser = abrir_site_com_retry(browser, f"recuperacao de {item_text}")

            time.sleep(3)

            login_field2 = WebDriverWait(browser, 10).until(

                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='E-mail']"))

            )

            preencher_input_texto(login_field2, USERNAME)

            password_field2 = browser.find_element(By.XPATH, "//input[@placeholder='Senha']")

            preencher_input_texto(password_field2, PASSWORD)

            btn2 = WebDriverWait(browser, 10).until(

                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Enviar')]"))

            )

            browser.execute_script("arguments[0].click();", btn2)

            time.sleep(3)

            clicar_xpath_quando_presente(

                browser,

                "/html/body/app-root/div/div/sidepanel/aside[1]/div[3]/div[2]/div/a[3]/div/i",

            )

            time.sleep(2)

            clicar_xpath_quando_presente(

                browser,

                "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist",

            )

            input_element = WebDriverWait(browser, 10).until(

                EC.element_to_be_clickable(

                    (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/input"))

            )

            print(f"  [recovery] SessÃ£o recuperada. A continuar com {item_text}...")

        except Exception as e_recovery:

            print(f"  [recovery] Falha na recuperaÃ§Ã£o ({e_recovery}). Guardando dados e saindo.")

            salvar_excels_incrementais(dados, dados_ensaios)

            break



    for _tentativa in range(3):
        try:

            selecionar_os_no_datalist(browser, item_text)



            # Aguarde um curto perÃ­odo antes de inserir o prÃ³ximo item (opcional)

            time.sleep(3)



            # Raspagem de dados (adapte os locators para corresponder Ã  estrutura da pÃ¡gina)

            criado_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[1]/div[3]/small")

            preenchido_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[2]/div[3]/small")

            submetido_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[3]/div[3]/small")

            processado_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[4]/div[3]/small")

            revisado_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[5]/div[3]/small")

            disponibilizado_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[6]/div[3]/small")

            aprovado_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[2]/p-timeline/div/div[7]/div[3]/small")

            # Localize o elemento do cliente

            client_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[1]/div[1]/form[1]/vitau-textinput/input")

            # Remova o atributo "disabled" usando JavaScript

            browser.execute_script(

                "arguments[0].removeAttribute('disabled');", client_element)

            # Obtenha o valor do cliente do elemento

            client_text = (client_element.get_attribute("value") or "").strip()



            # Localize o elemento da planta

            plant_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[1]/div[1]/form[2]/vitau-textinput/input")

            # Remova o atributo "disabled" usando JavaScript

            browser.execute_script(

                "arguments[0].removeAttribute('disabled');", plant_element)

            # Obtenha o valor da planta do elemento

            plant_text = (plant_element.get_attribute("value") or "").strip()



            # Localize o elemento do setor

            sector_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[1]/div[1]/form[3]/vitau-textinput/input")

            # Remova o disabled

            browser.execute_script(

                "arguments[0].removeAttribute('disabled');", sector_element)

            # Obtenha o VALUE

            sector_text = (sector_element.get_attribute("value") or "").strip()

            # Localize o elemento da etiqueta da mÃ¡quina (machine tag)



            machine_tag_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[1]/div[1]/form[4]/vitau-textinput/input")

            # Remova o atributo "disabled" usando JavaScript

            browser.execute_script(

                "arguments[0].removeAttribute('disabled');", machine_tag_element)

            # Obtenha o valor da etiqueta da mÃ¡quina do elemento

            machine_tag_text = (machine_tag_element.get_attribute("value") or "").strip()



            # Localize o elemento do tipo de equipamento (equipment type)

            equipment_type_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[1]/div[2]/form/vitau-textinput/input")

            # Remova o atributo "disabled" usando JavaScript

            browser.execute_script(

                "arguments[0].removeAttribute('disabled');", equipment_type_element)

            # Obtenha o valor do tipo de equipamento do elemento

            equipment_type_text = (equipment_type_element.get_attribute("value") or "").strip()



            # Localize o elemento do tipo de diagnÃ³stico (diagnosis type)

            diagnosis_type_element = browser.find_element(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[1]/div[2]/vitau-select/select")

            # Remova o atributo "disabled" usando JavaScript

            browser.execute_script(

                "arguments[0].removeAttribute('disabled');", diagnosis_type_element)

            diagnosis_type_select = Select(diagnosis_type_element)

            selected_text = diagnosis_type_select.first_selected_option.text



            # Localize o(s) elemento(s) do responsÃ¡vel (pode haver 0, 1 ou vÃ¡rios)

            responsible_elements = browser.find_elements(

                By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[2]/div[1]/div[1]/ng2-smart-table/table/tbody/tr/td[2]/ng2-smart-table-cell/table-cell-view-mode/div/div")



            # Extraia o texto de cada elemento

            criado_text = criado_element.text

            preenchido_text = preenchido_element.text

            submetido_text = submetido_element.text

            processado_text = processado_element.text

            revisado_text = revisado_element.text

            disponibilizado_text = disponibilizado_element.text

            aprovado_text = aprovado_element.text

            client_text = client_text

            plant_text = plant_text

            sector_text = sector_text

            machine_tag_text = machine_tag_text

            equipment_type_text = equipment_type_text

            diagnosis_type_text = selected_text

            responsibles_text = ", ".join([e.text.strip() for e in responsible_elements if e.text.strip()]) or "NA"



            # Imprimir cada item

            print(f"NR_OS: {item_text}")

            print(f"Criado: {criado_text}")

            print(f"Preenchido: {preenchido_text}")

            print(f"Submetido: {submetido_text}")

            print(f"Processado: {processado_text}")

            print(f"Revisado: {revisado_text}")

            print(f"Disponibilizado: {disponibilizado_text}")

            print(f"Aprovado: {aprovado_text}")

            print(f"Cliente: {client_text}")

            print(f"Planta: {plant_text}")

            print(f"Setor: {sector_text}")

            print(f"Tag da Máquina: {machine_tag_text}")

            print(f"Tipo de Equipamento: {equipment_type_text}")

            print(f"Tipo de Diagnóstico: {diagnosis_type_text}")

            print(f"Responsáveis: {responsibles_text}")



            tabela_xpath = "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[2]/div[1]/div[3]/ng2-smart-table/table/tbody"

            elemento_td = extrair_textos_td_por_xpath(browser, tabela_xpath)

            print(elemento_td)



            # Verifique se "ANALISADOR MOVEL DE SISTEMAS ISOLANTES" estÃ¡ na lista

            if "ANALISADOR MOVEL DE SISTEMAS ISOLANTES" in elemento_td:

                Kit_Utilizado = "ANALISADOR MOVEL DE SISTEMAS ISOLANTES"

            elif "MEDIDOR DE PERDAS - MIDAS (LABORATORIO DE ENSAIOS)" in elemento_td:

                Kit_Utilizado = "MEDIDOR DE PERDAS - MIDAS (LABORATORIO DE ENSAIOS)"

            elif "MEDIDOR DE PERDAS - MIDAS" in elemento_td:

                # Encontre todos os Ã­ndices onde "MEDIDOR DE PERDAS - MIDAS" estÃ¡ presente

                indices_medidor_perdas = [i for i, valor in enumerate(

                    elemento_td) if valor == "MEDIDOR DE PERDAS - MIDAS"]



                # Verifique se existem pelo menos dois elementos apÃ³s "MEDIDOR DE PERDAS - MIDAS" no Ãºltimo Ã­ndice

                if indices_medidor_perdas and len(elemento_td) > indices_medidor_perdas[-1] + 2:

                    Kit_Utilizado = elemento_td[indices_medidor_perdas[-1] + 2]

                else:

                    Kit_Utilizado = "NA"

            else:

                Kit_Utilizado = "NA"



            print(f"O Kit Utilizado Ã©: {Kit_Utilizado}")

            print("-" * 50)

            time.sleep(2)



            # ---- ExtraÃ§Ã£o de dados de ensaios elÃ©tricos (aba ngb-nav-8) ----

            dados_ensaio = {

                'NR_OS': item_text,

                'Tipo de Equipamento': equipment_type_text,

                'IP': None, 'ΔI': None, 'Pi1/Vn': None, 'PD': None,

                'ΔTan δ': None, 'Tang δ (h)': None, 'Tan δ': None, 'H': None,

                'Grau de Envelhecimento GEI (Anos)': None, 'GEI - Referência': None,

                'Avaliação Global': None, 'Avaliação Global - Referência': None,

                'Grau de Deterioração (D10)': None, 'D10 - Referência': None,

                'Grau de Contaminação (D20)': None, 'D20 - Referência': None,

            }

            dados_maquina = extrair_dados_maquina(browser, item_text)

            dados_ensaio.update(dados_maquina)

            colunas_obrigatorias_ensaio = [

                'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H',

            ]

            ignorar_os_sem_aba_ensaio = False

            try:

                # Debug: listar todas as abas disponÃ­veis

                todas_abas = browser.find_elements(

                    By.XPATH,

                    "//ul[@role='tablist']//a"

                )

                print(f"  [abas] Abas encontradas para {item_text}: {[a.text.strip() for a in todas_abas]}")



                # A aba de avaliacao global e obrigatoria para processar a OS.

                tab_list = browser.find_elements(

                    By.XPATH,

                    "//ul[@role='tablist']//a[contains(normalize-space(.),'Avaliação Global') and contains(normalize-space(.),'Isolamento')]"

                )

                if not tab_list:

                    print(f"  [ensaio] Aba 'Avaliação Global dos Parâmetros de Isolamento' não existe para {item_text}, OS ignorada.")

                    ignorar_os_sem_aba_ensaio = True

                else:

                    nav8 = tab_list[0]

                    print(f"  [ensaio] Aba encontrada para {item_text}, clicando...")

                    browser.execute_script("arguments[0].scrollIntoView(true);", nav8)

                    time.sleep(0.5)

                    browser.execute_script("arguments[0].click();", nav8)

                    time.sleep(1)



                    # Abrir modal clicando no botÃ£o "Ver parÃ¢metros utilizados" (div.btn-ge)

                    em_button = WebDriverWait(browser, 10).until(


                        lambda _: primeiro_elemento_visivel(browser.find_elements(By.CSS_SELECTOR, ".btn-ge"))

                    )

                    browser.execute_script("arguments[0].click();", em_button)

                    time.sleep(2)



                    # Extrair parametro e valor do modal

                    modal_div = cast(Any, WebDriverWait(browser, 10).until(


                        lambda _: obter_corpo_modal_visivel(browser)

                    ))

                    parametros_alvo = {'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H'}

                    modal_rows = modal_div.find_elements(By.XPATH, './/tr')

                    for row in modal_rows:

                        cols = row.find_elements(By.TAG_NAME, 'td')

                        if len(cols) >= 2:

                            param = cols[0].text.strip()

                            valor = cols[1].text.strip()

                            if param in parametros_alvo:

                                if param == 'H' and valor == '-':

                                    valor = '0,01'

                                dados_ensaio[param] = valor

                                print(f"  [modal] {param} = {valor}")



                    # Fechar o modal com ESC (body.click() pode navegar para outro elemento)

                    webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()

                    time.sleep(1)



                    # Extrair tabela de resultados (Grau de Envelhecimento, AvaliaÃ§Ã£o Global, etc.)

                    try:


                        linhas_resultado = WebDriverWait(browser, 10).until(

                            lambda _: extrair_linhas_resultado_visiveis(browser) or False

                        )

                        for param, valor, ref in linhas_resultado:

                            print(f"  [tabela] {param} = {valor} | ref={ref}")

                            if 'Grau de Envelhecimento' in param or 'GEI' in param:

                                dados_ensaio['Grau de Envelhecimento GEI (Anos)'] = valor

                                dados_ensaio['GEI - Referência'] = ref

                            elif 'Avaliação Global' in param:

                                dados_ensaio['Avaliação Global'] = valor

                                dados_ensaio['Avaliação Global - Referência'] = ref

                            elif 'Grau de Deterioração' in param or 'D10' in param:

                                dados_ensaio['Grau de Deterioração (D10)'] = valor

                                dados_ensaio['D10 - Referência'] = ref

                            elif 'Grau de Contaminação' in param or 'D20' in param:

                                dados_ensaio['Grau de Contaminação (D20)'] = valor

                                dados_ensaio['D20 - Referência'] = ref

                    except TimeoutException:

                        print(f"  [ensaio] Tabela de resultados nÃ£o encontrada para {item_text}")



                    # Voltar para a aba IdentificaÃ§Ã£o para nÃ£o quebrar a extraÃ§Ã£o do prÃ³ximo OS

                    try:

                        aba_id = browser.find_elements(

                            By.XPATH, "//ul[@role='tablist']//a[contains(.,'Identificação')]"

                        )

                        if aba_id:

                            browser.execute_script("arguments[0].click();", aba_id[0])

                            time.sleep(0.5)

                    except Exception:

                        pass



            except Exception as e:

                print(f"  [ensaio] Erro para {item_text}: {str(e)}")



            if ignorar_os_sem_aba_ensaio:

                print(f"  [skip] {item_text} sem aba de Avaliação Global dos Parâmetros de Isolamento. Nada será gravado para essa OS.")

                break



            if not item_text.startswith('D'):

                ensaio_completo = all(

                    normalizar_valor_comparacao(dados_ensaio.get(coluna))

                    for coluna in colunas_obrigatorias_ensaio

                )

                if ensaio_completo:

                    assinatura_atual = assinatura_dados_ensaio(dados_ensaio)

                    if assinatura_atual == ultima_assinatura_ensaio:

                        repeticoes_assinatura_ensaio += 1

                    else:

                        ultima_assinatura_ensaio = assinatura_atual

                        repeticoes_assinatura_ensaio = 1

                    if repeticoes_assinatura_ensaio > LIMITE_ASSINATURA_ENSAIO_REPETIDA:

                        print(

                            f"  [guard] {item_text}: assinatura de ensaio repetida "

                            f"{repeticoes_assinatura_ensaio} vezes seguidas. Execucao interrompida para nao corromper o Excel."

                        )

                        salvar_excels_incrementais(dados, dados_ensaios)

                        interromper_execucao = True

                        break

                    reconciliar_registro(dados_ensaios, dados_ensaio, _colunas_ensaios, "Dados_Ensaios.xlsx", False)

                else:

                    print(f"  [skip] Dados_Ensaios.xlsx: {item_text} com campos obrigatórios de ensaio vazios. Nada será gravado.")



                # Certifique-se de que Kit_Utilizado tenha um valor

                if not 'Kit_Utilizado' in dir() or Kit_Utilizado is None:

                    Kit_Utilizado = "NA"

                dados_daimer = {

                    'NR_OS': item_text,

                    'Criado': criado_text,

                    'Preenchido': preenchido_text,

                    'Submetido': submetido_text,

                    'Processado': processado_text,

                    'Revisado': revisado_text,

                    'Disponibilizado': disponibilizado_text,

                    'Aprovado': aprovado_text,

                    'Cliente': client_text,

                    'Planta': plant_text,

                    'Setor': sector_text,

                    'Tag da Máquina(NS)': machine_tag_text,

                    'Tipo de Equipamento': equipment_type_text,

                    'Tipo de Diagnóstico': diagnosis_type_text,

                    'Serviço de Campo': responsibles_text,

                    'Kit_Utilizado': Kit_Utilizado,

                }

                dados_daimer.update({

                    coluna: dados_maquina.get(coluna_maquina)

                    for coluna, coluna_maquina in _mapa_dados_maquina_daimer.items()

                })

                reconciliar_registro(dados, dados_daimer, _colunas_daimer, "Dados_Daimer.xlsx", True)

                os_processadas_execucao.add(item_os_normalizada)



                # Guardar apÃ³s cada OS para nÃ£o perder dados em caso de crash

                salvar_excels_incrementais(dados, dados_ensaios)
            break  # sucesso
        except Exception as e_scrape:
            print(f"  [retry] Erro ao raspar {item_text} (tentativa {_tentativa + 1}/3): {e_scrape}")
            if _tentativa < 2:
                time.sleep(5)
                # Tentar recuperar sessao: re-login com credenciais do .env
                try:
                    browser = abrir_site_com_retry(browser, f"retry {_tentativa + 1} de {item_text}")
                    time.sleep(3)
                    login_field_r = WebDriverWait(browser, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='E-mail']"))
                    )
                    preencher_input_texto(login_field_r, USERNAME)
                    password_field_r = browser.find_element(By.XPATH, "//input[@placeholder='Senha']")
                    preencher_input_texto(password_field_r, PASSWORD)
                    btn_r = WebDriverWait(browser, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Enviar')]"))
                    )
                    browser.execute_script("arguments[0].click();", btn_r)
                    time.sleep(3)
                    clicar_xpath_quando_presente(
                        browser,
                        "/html/body/app-root/div/div/sidepanel/aside[1]/div[3]/div[2]/div/a[3]/div/i",
                    )
                    time.sleep(2)
                    clicar_xpath_quando_presente(
                        browser,
                        "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist",
                    )
                    input_element = WebDriverWait(browser, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/input"))
                    )
                    print(f"  [retry] Sessao recuperada com credenciais do .env. A repetir {item_text}...")
                except Exception as e_relogin:
                    print(f"  [retry] Falha no re-login ({e_relogin}). Guardando e a saltar {item_text}...")
                    salvar_excels_incrementais(dados, dados_ensaios)
                    break
            else:
                print(f"  [retry] Maximo de tentativas atingido para {item_text}. A saltar...")

    if interromper_execucao:

        break





# Seus dados e colunas

colunas = _colunas_daimer



df = pd.DataFrame(dados, columns=colunas)



# Remova leading zeros da coluna 'NR_OS'

df['NR_OS'] = df['NR_OS'].astype(str).str.lstrip('0')



# SubstituiÃ§Ã£o especÃ­fica na coluna 'ServiÃ§o de Campo'

df['Serviço de Campo'] = df['Serviço de Campo'].replace({

    'Douglas Aparecido Lopes': 'Supervisor de Ensaios Elétricos',

    'Yswame Rodrigues da Cunha': 'Supervisor de Serviço de Campo'

})





# Salvar o arquivo Excel

df.to_excel(DAIMER_WORKBOOK, index=False)



# Salvar o Excel de ensaios elÃ©tricos

colunas_ensaios = _colunas_ensaios

df_ensaios = pd.DataFrame(dados_ensaios, columns=colunas_ensaios)

df_ensaios['NR_OS'] = df_ensaios['NR_OS'].astype(str).str.lstrip('0')

df_ensaios.to_excel(ENSAIOS_WORKBOOK, index=False)



# Certifique-se de fechar o navegador no final

try:

    browser.quit()

except Exception:

    pass
