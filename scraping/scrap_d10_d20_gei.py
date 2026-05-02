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

from selenium.common.exceptions import NoSuchElementException, TimeoutException

import matplotlib.pyplot as plt

import os
from pathlib import Path

from typing import Any, cast

from openpyxl import Workbook

from openpyxl.styles import NamedStyle

from openpyxl.utils.dataframe import dataframe_to_rows

from dotenv import load_dotenv



# Carregar o .env do mesmo diretÃ³rio que o script

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAP_DIR = Path(SCRIPT_DIR)
DAIMER_WORKBOOK = SCRAP_DIR / 'Dados_Daimer.xlsx'
ENSAIOS_WORKBOOK = SCRAP_DIR / 'Dados_Ensaios.xlsx'

env_path = os.path.join(SCRIPT_DIR, '.env')

if not os.path.exists(env_path):

    raise FileNotFoundError(f"Arquivo .env nao encontrado em: {env_path}")

load_dotenv(dotenv_path=env_path, override=True)

print(f"[env] .env carregado: {env_path}")



USERNAME_ENV = os.getenv('DAIMER_EMAIL') or os.getenv('USERNAME')

PASSWORD_ENV = os.getenv('DAIMER_PASSWORD') or os.getenv('PASSWORD')

if not USERNAME_ENV or not PASSWORD_ENV:

    raise RuntimeError("Credenciais ausentes no .env. Configure DAIMER_EMAIL/USERNAME e DAIMER_PASSWORD/PASSWORD.")

USERNAME: str = USERNAME_ENV

PASSWORD: str = PASSWORD_ENV



# ConfiguraÃ§Ãµes do ChromeDriver

chrome_options = webdriver.ChromeOptions()

chrome_options.add_argument("--incognito")

chrome_options.add_argument("--window-size=1920,1080")



# Inicialize o webdriver Chromium (Chrome) usando o ChromeDriver

browser = webdriver.Chrome(options=chrome_options)

browser.maximize_window()

browser.execute_script("document.body.style.zoom='80%'")



# Abrir o site

browser.get('https://daimer.data.com.br/')



# Insira o login

login_field = browser.find_element(By.XPATH, "//input[@placeholder='E-mail']")

login_field.send_keys(USERNAME)



# Insira a sen

password_field = browser.find_element(

    By.XPATH, "//input[@placeholder='Senha']")

password_field.send_keys(PASSWORD)



# Encontre o elemento usando o XPath fornecido e clique via JS para evitar intercepÃ§Ã£o

button = WebDriverWait(browser, 10).until(

    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Enviar')]"))

)

browser.execute_script("arguments[0].click();", button)



# Aguarde um curto perÃ­odo para garantir que a pÃ¡gina esteja totalmente carregada

time.sleep(2)



try:

    # Localize o elemento <select> usando XPath e clique nele

    entrada_dados = WebDriverWait(browser, 10).until(

        EC.element_to_be_clickable(

            (By.XPATH, "/html/body/app-root/div/div/sidepanel/aside[1]/div[3]/div[2]/div/a[3]/div/i"))

    )

    entrada_dados.click()

except Exception as e:

    browser.save_screenshot("erro_menu.png")

    print(f"Erro ao encontrar menu. URL atual: {browser.current_url}")

    print(browser.page_source[:500])

    raise e



# Aguarde atÃ© que o dropdown seja clicÃ¡vel

dropdown_element = WebDriverWait(browser, 10).until(

    EC.element_to_be_clickable(

        (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist"))

)



# Clique no dropdown para abrir as opÃ§Ãµes

dropdown_element.click()



# Lista para armazenar todos os itens do dropdown

all_items_list = []



# Loop externo para iterar sobre as letras do alfabeto

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

_colunas_ensaios = [

    'NR_OS', 'Tipo de Equipamento', 'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H',

    'Grau de Envelhecimento GEI (Anos)', 'GEI - Referência',

    'Avaliação Global', 'Avaliação Global - Referência',

    'Grau de Deterioração (D10)', 'D10 - Referência',

    'Grau de Contaminação (D20)', 'D20 - Referência',

]

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

    colunas = ["NR_OS", "Criado", "Preenchido", "Submetido", "Processado", "Revisado",

               "Disponibilizado", "Aprovado", "Cliente", "Planta", "Setor",

               "Tag da Máquina(NS)", "Tipo de Equipamento", "Tipo de Diagnóstico",

               "Serviço de Campo", "Kit_Utilizado"]

    if dados:

        df_inc = pd.DataFrame(dados, columns=colunas)

        df_inc['NR_OS'] = df_inc['NR_OS'].astype(str).str.lstrip('0')

        df_inc['Serviço de Campo'] = df_inc['Serviço de Campo'].replace({

            'Douglas Aparecido Lopes': 'Supervisor de Ensaios Elétricos',

            'Yswame Rodrigues da Cunha': 'Supervisor de Serviço de Campo'

        })

        df_inc.to_excel(DAIMER_WORKBOOK, index=False)

    colunas_ensaios = [

        'NR_OS', 'Tipo de Equipamento', 'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H',

        'Grau de Envelhecimento GEI (Anos)', 'GEI - Referência',

        'Avaliação Global', 'Avaliação Global - Referência',

        'Grau de Deterioração (D10)', 'D10 - Referência',

        'Grau de Contaminação (D20)', 'D20 - Referência',

    ]

    if dados_ensaios:

        df_ens_inc = pd.DataFrame(dados_ensaios, columns=colunas_ensaios)

        df_ens_inc['NR_OS'] = df_ens_inc['NR_OS'].astype(str).str.lstrip('0')

        df_ens_inc.to_excel(ENSAIOS_WORKBOOK, index=False)

    print("  [save] Ficheiros Excel guardados.")





# Itere sobre os itens e insira um a um no campo de entrada

letra_atual = all_items_list[0][0].upper() if all_items_list else ''

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

            browser.get('https://daimer.data.com.br/')

            time.sleep(3)

            login_field2 = WebDriverWait(browser, 10).until(

                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='E-mail']"))

            )

            login_field2.send_keys(USERNAME)

            browser.find_element(By.XPATH, "//input[@placeholder='Senha']").send_keys(PASSWORD)

            btn2 = WebDriverWait(browser, 10).until(

                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Enviar')]"))

            )

            browser.execute_script("arguments[0].click();", btn2)

            time.sleep(3)

            WebDriverWait(browser, 10).until(

                EC.element_to_be_clickable(

                    (By.XPATH, "/html/body/app-root/div/div/sidepanel/aside[1]/div[3]/div[2]/div/a[3]/div/i"))

            ).click()

            time.sleep(2)

            WebDriverWait(browser, 10).until(

                EC.element_to_be_clickable(

                    (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[1]/div[1]/div/form/vitau-datalist"))

            ).click()

            input_element = WebDriverWait(browser, 10).until(

                EC.element_to_be_clickable(

                    (By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div/div/div/form/vitau-datalist/input"))

            )

            print(f"  [recovery] SessÃ£o recuperada. A continuar com {item_text}...")

        except Exception as e_recovery:

            print(f"  [recovery] Falha na recuperaÃ§Ã£o ({e_recovery}). Guardando dados e saindo.")

            salvar_excels_incrementais(dados, dados_ensaios)

            break



    input_element.clear()

    input_element.send_keys(item_text)

    input_element.send_keys(Keys.ENTER)



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



    # Localize a tabela usando o seletor XPath fornecido

    tabela = browser.find_element(

        By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[2]/div[1]/div[3]/ng2-smart-table/table/tbody")



    # Suponha que vocÃª jÃ¡ tenha obtido os elementos da tabela como mencionado anteriormente

    elementos_td = tabela.find_elements(By.TAG_NAME, "td")



    # Declare elemento_td como uma lista vazia

    elemento_td = []



    # Itere sobre os elementos e obtenha os textos

    for elemento in elementos_td:

        texto = elemento.text

        elemento_td.append(texto)



    # Fora do loop, imprima a lista completa

    print(elemento_td)



    # Reencontre a tabela apÃ³s alguma interaÃ§Ã£o que pode tornar os elementos obsoletos

    tabela = browser.find_element(

        By.XPATH, "/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[2]/div[1]/div[3]/ng2-smart-table/table/tbody")



    # Suponha que vocÃª jÃ¡ tenha obtido os elementos da tabela novamente apÃ³s a interaÃ§Ã£o

    elementos_td = tabela.find_elements(By.TAG_NAME, "td")



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

    dados_ensaio: dict[str, Any] = {

        'NR_OS': item_text,

        'Tipo de Equipamento': equipment_type_text,

        'IP': None, 'ΔI': None, 'Pi1/Vn': None, 'PD': None,

        'ΔTan δ': None, 'Tang δ (h)': None, 'Tan δ': None, 'H': None,

        'Grau de Envelhecimento GEI (Anos)': None, 'GEI - Referência': None,

        'Avaliação Global': None, 'Avaliação Global - Referência': None,

        'Grau de Deterioração (D10)': None, 'D10 - Referência': None,

        'Grau de Contaminação (D20)': None, 'D20 - Referência': None,

    }

    try:

        # Debug: listar todas as abas disponÃ­veis

        todas_abas = browser.find_elements(

            By.XPATH,

            "//ul[@role='tablist']//a"

        )

        print(f"  [abas] Abas encontradas para {item_text}: {[a.text.strip() for a in todas_abas]}")



        # Procura a aba pelo texto em qualquer nÃ­vel filho (div estÃ¡ entre ul e li)

        tab_list = browser.find_elements(

            By.XPATH,

            "//ul[@role='tablist']//a[contains(.,'Avaliação Global') and contains(.,'Isolamento')]"

        )

        if not tab_list:

            print(f"  [ensaio] Aba 'Avaliação Global dos Parâmetros de Isolamento' não existe para {item_text}, pulando...")

        else:

            nav8 = tab_list[0]

            print(f"  [ensaio] Aba encontrada para {item_text}, clicando...")

            browser.execute_script("arguments[0].scrollIntoView(true);", nav8)

            time.sleep(0.5)

            browser.execute_script("arguments[0].click();", nav8)

            time.sleep(1)



            # Abrir modal clicando no botÃ£o "Ver parÃ¢metros utilizados" (div.btn-ge)

            em_button = WebDriverWait(browser, 5).until(

                EC.element_to_be_clickable(

                    (By.XPATH, "//div[contains(@class,'btn-ge')]"))

            )

            browser.execute_script("arguments[0].click();", em_button)

            time.sleep(2)



            # Extrair parametro e valor do modal

            modal_div = WebDriverWait(browser, 5).until(

                EC.presence_of_element_located(

                    (By.XPATH, '/html/body/ngb-modal-window/div/div/div[2]/div'))

            )

            parametros_alvo = {'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H'}

            modal_rows = modal_div.find_elements(By.XPATH, './/tr')

            for row in modal_rows:

                cols = row.find_elements(By.TAG_NAME, 'td')

                if len(cols) >= 2:

                    param = cols[0].text.strip()

                    valor = cols[1].text.strip()

                    if param in parametros_alvo:

                        dados_ensaio[param] = valor

                        print(f"  [modal] {param} = {valor}")



            # Fechar o modal com ESC (body.click() pode navegar para outro elemento)

            webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()

            time.sleep(1)



            # Extrair tabela de resultados (Grau de Envelhecimento, AvaliaÃ§Ã£o Global, etc.)

            try:

                tabela_resultado = WebDriverWait(browser, 5).until(

                    EC.presence_of_element_located(

                        (By.XPATH, '/html/body/app-root/div/div/div/div[2]/div/div/inputs/div/div/div[2]/div[1]/div/div[2]/div/div[3]'))

                )

                ht_rows = tabela_resultado.find_elements(By.XPATH, './/tr')

                for row in ht_rows:

                    cols = row.find_elements(By.TAG_NAME, 'td')

                    if len(cols) >= 2:

                        param = cols[0].text.strip()

                        valor = cols[1].text.strip()

                        ref = cols[2].text.strip() if len(cols) >= 3 else None

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



    if not item_text.startswith('D'):

        reconciliar_registro(dados_ensaios, dados_ensaio, _colunas_ensaios, "Dados_Ensaios.xlsx", False)



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

        reconciliar_registro(dados, dados_daimer, _colunas_daimer, "Dados_Daimer.xlsx", True)

        os_processadas_execucao.add(item_os_normalizada)



        # Guardar apÃ³s cada OS para nÃ£o perder dados em caso de crash

        salvar_excels_incrementais(dados, dados_ensaios)





# Seus dados e colunas

colunas = ["NR_OS", "Criado", "Preenchido", "Submetido", "Processado", "Revisado", "Disponibilizado", "Aprovado", "Cliente",

           "Planta", "Setor", "Tag da Máquina(NS)", "Tipo de Equipamento", "Tipo de Diagnóstico", "Serviço de Campo", "Kit_Utilizado"]



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

colunas_ensaios = [

    'NR_OS', 'Tipo de Equipamento', 'IP', 'ΔI', 'Pi1/Vn', 'PD', 'ΔTan δ', 'Tang δ (h)', 'Tan δ', 'H',

    'Grau de Envelhecimento GEI (Anos)', 'GEI - Referência',

    'Avaliação Global', 'Avaliação Global - Referência',

    'Grau de Deterioração (D10)', 'D10 - Referência',

    'Grau de Contaminação (D20)', 'D20 - Referência',

]

df_ensaios = pd.DataFrame(dados_ensaios, columns=colunas_ensaios)

df_ensaios['NR_OS'] = df_ensaios['NR_OS'].astype(str).str.lstrip('0')

df_ensaios.to_excel(ENSAIOS_WORKBOOK, index=False)



# Certifique-se de fechar o navegador no final

browser.quit()